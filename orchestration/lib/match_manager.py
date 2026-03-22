import importlib
import json
import logging
from typing import Any

from lib.agent_communication import AgentCommunicationError, AgentProcess
from lib.backend_api import BackendAPI

logger = logging.getLogger(__name__)

async def _get_agent_image_tags(agent_ids: list[str], api: BackendAPI) -> list[str]:
    image_tags = []
    for agent_id in agent_ids:
        logger.debug(f"Fetching submission metadata for agent {agent_id!r}")
        try:
            submission = await api.get_submission(agent_id)
        except Exception as e:
            raise AgentCommunicationError(f"Could not retrieve agent metadata for {agent_id}: {e}")

        build_jobs = submission.get("build_jobs", [])
        logger.debug(f"Agent {agent_id!r} has {len(build_jobs)} build job(s)")
        tag = None
        for job in build_jobs:
            if job.get("status") == "completed" and job.get("image_tag"):
                tag = job["image_tag"]
                logger.debug(f"Resolved image tag for agent {agent_id!r}: {tag!r}")
                break

        if not tag:
            raise AgentCommunicationError(f"No valid Docker image tag found for agent {agent_id}")

        image_tags.append(tag)
    return image_tags

async def run_match(match_id: str, config: dict[str, Any], agent_ids: list[str], api: BackendAPI) -> dict[str, Any]:
    """
    Execute a real match loop using standard I/O communication with dockerized agents.
    """
    logger.debug(f"run_match called | match_id={match_id!r} agent_ids={agent_ids} config={config}")
    try:
        match_data = await api.get_match(match_id)
        game_type = match_data["game_type"]
        logger.debug(f"[{match_id}] Game type resolved: {game_type!r}")

        # Dynamically import game engine and state based on game_type
        try:
            Engine = importlib.import_module(f"gamelib.{game_type}.engine").Engine
            State = importlib.import_module(f"gamelib.{game_type}.gamestate").GameState
            Move = importlib.import_module(f"gamelib.{game_type}.move").Move
            logger.debug(f"[{match_id}] Imported Engine={Engine.__name__}, State={State.__name__}, Move={Move.__name__}")  # noqa: E501
        except ImportError as e:
            logger.error(f"[{match_id}] Failed to import game modules for type {game_type!r}: {e}")
            return {"status": "error", "reason": f"Game type {game_type} not supported: {e}"}

        # Determine agent image tags
        logger.debug(f"[{match_id}] Resolving image tags for {len(agent_ids)} agent(s): {agent_ids}")
        try:
            image_tags = await _get_agent_image_tags(agent_ids, api)
            logger.debug(f"[{match_id}] Image tags resolved: {image_tags}")
        except AgentCommunicationError as e:
            logger.error(f"[{match_id}] Image tag resolution failed: {e}")
            return {"status": "error", "reason": str(e)}

        agents = []
        for i, tag in enumerate(image_tags):
            logger.debug(f"[{match_id}] Creating AgentProcess for player {i} with image {tag!r}")
            agents.append(AgentProcess(tag, player_id=i))

        # Check whether the given image exists for all playing agents
        for agent in agents:
            logger.debug(f"[{match_id}] Verifying image for player {agent.player_id}")
            try:
                agent.verify_image()
            except AgentCommunicationError as e:
                logger.error(f"[{match_id}] Image verification failed for player {agent.player_id}: {e}")
                return {"status": "error", "reason": str(e)}

        # Initialize the given game using gamelib
        engine = Engine()
        state = State.initial()
        logger.debug(f"[{match_id}] Game engine and initial state created")

        # Start and initialize each agent
        for agent in agents:
            logger.debug(f"[{match_id}] Starting agent process for player {agent.player_id}")
            try:
                await agent.start()
                logger.debug(f"[{match_id}] Agent process started for player {agent.player_id}, sending init")
                await agent.send_init()
                logger.debug(f"[{match_id}] Agent player {agent.player_id} init sent successfully")
            except AgentCommunicationError as e:
                logger.error(f"[{match_id}] Agent player {agent.player_id} failed to start/init: {e}")
                for a in agents:
                    await a.cleanup()
                return {"status": "error", "reason": f"Agent {agent.player_id} failed to start/init: {e}"}

        scores = {agent_id: 0 for agent_id in agent_ids}
        winner_id = -1
        reason = ""
        turn_count = 0

        # Send states and get moves from agents
        try:
            while not engine.is_game_over(state):
                current_player = state.turn
                cur_agent = agents[current_player]
                turn_count += 1
                logger.debug(f"[{match_id}] Turn {turn_count}: player {current_player}'s move")

                try:
                    state_json = state.to_json()
                    logger.debug(f"[{match_id}] Turn {turn_count}: sending state to player {current_player}")
                    await cur_agent.send_state(state_json)
                    move_json = await cur_agent.get_move()
                    logger.debug(f"[{match_id}] Turn {turn_count}: received move from player {current_player}: {move_json!r}")  # noqa: E501
                    move = Move.from_json(move_json)
                except Exception as e:
                    reason = f"Player {current_player} failed to communicate or generated invalid output: {e}"
                    logger.warning(f"[{match_id}] Turn {turn_count}: {reason}")
                    winner_id = 1 - current_player
                    break

                if not engine.validate_move(state, move):
                    reason = f"Player {current_player} made an invalid move."
                    logger.warning(f"[{match_id}] Turn {turn_count}: {reason} move={move_json!r}")
                    winner_id = 1 - current_player
                    break

                state = engine.apply_move(state, move)
                logger.debug(f"[{match_id}] Turn {turn_count}: move applied, updating backend state")
                try:
                    state_json_str = state.to_json()
                    state_dict = json.loads(state_json_str)
                    await api.update_match(match_id, status="running", game_state=state_dict)
                    logger.debug(f"[{match_id}] Turn {turn_count}: backend state updated")
                except Exception as e:
                    logger.error(f"[{match_id}] Turn {turn_count}: failed to update match game_state: {e}")
        finally:
            # Clean up all agent subprocesses
            logger.debug(f"[{match_id}] Cleaning up {len(agents)} agent process(es)")
            for agent in agents:
                await agent.cleanup()
            logger.debug(f"[{match_id}] Agent cleanup done (total turns played: {turn_count})")

        game_status = engine.get_status(state)
        logger.debug(f"[{match_id}] Game over | engine.get_status={game_status} winner_id={winner_id}")

        if winner_id == -1:
            if game_status >= 0:
                winner_id = game_status
                reason = "Turn limit reached" if getattr(state, "status", None) == "limit" else "Game finished"
            else:
                reason = "Draw"

        if winner_id >= 0:
            scores[agent_ids[winner_id]] = 1
            winner_result = agent_ids[winner_id]
        else:
            winner_result = "draw"

        result = {
            "winner": winner_result,
            "scores": scores,
            "reason": reason,
        }
        logger.debug(f"[{match_id}] Match result: {result}")
        return result

    except Exception as e:
        logger.exception(f"Unexpected exception during execute match {match_id}: {e}")
        return {"status": "error", "reason": str(e)}
