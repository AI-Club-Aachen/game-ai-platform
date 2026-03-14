import importlib
import logging
from typing import Any

from lib.backend_api import BackendAPI
from lib.agent_communication import AgentProcess, AgentCommunicationError

logger = logging.getLogger(__name__)

async def _get_agent_image_tags(agent_ids: list[str], api: BackendAPI) -> list[str]:
    image_tags = []
    for agent_id in agent_ids:
        try:
            submission = await api.get_submission(agent_id)
        except Exception as e:
            raise AgentCommunicationError(f"Could not retrieve agent metadata for {agent_id}: {e}")
            
        build_jobs = submission.get("build_jobs", [])
        tag = None
        for job in build_jobs:
            if job.get("status") == "completed" and job.get("image_tag"):
                tag = job["image_tag"]
                break
                
        if not tag:
            raise AgentCommunicationError(f"No valid Docker image tag found for agent {agent_id}")
            
        image_tags.append(tag)
    return image_tags

async def run_match(match_id: str, config: dict[str, Any], agent_ids: list[str], api: BackendAPI) -> dict[str, Any]:
    """
    Execute a real match loop using standard I/O communication with dockerized agents.
    """
    try:
        match_data = await api.get_match(match_id)
        game_type = match_data["game_type"]

        # Dynamically import game engine and state based on game_type
        try:
            Engine = importlib.import_module(f"gamelib.{game_type}.engine").Engine
            State = importlib.import_module(f"gamelib.{game_type}.gamestate").GameState
            Move = importlib.import_module(f"gamelib.{game_type}.move").Move
        except ImportError as e:
            return {"status": "error", "reason": f"Game type {game_type} not supported: {e}"}

        # Determine agent image tags
        try:
            image_tags = await _get_agent_image_tags(agent_ids, api)
        except AgentCommunicationError as e:
            return {"status": "error", "reason": str(e)}

        agents = []
        for i, tag in enumerate(image_tags):
            agents.append(AgentProcess(tag, player_id=i))

        # Check whether the given image exists for all playing agents
        for agent in agents:
            try:
                agent.verify_image()
            except AgentCommunicationError as e:
                return {"status": "error", "reason": str(e)}

        # Initialize the given game using gamelib
        engine = Engine()
        state = State.initial()

        # Start and initialize each agent
        for agent in agents:
            try:
                await agent.start()
                await agent.send_init()
            except AgentCommunicationError as e:
                for a in agents:
                    await a.cleanup()
                return {"status": "error", "reason": f"Agent {agent.player_id} failed to start/init: {e}"}

        scores = {agent_id: 0 for agent_id in agent_ids}
        winner_id = -1
        reason = ""

        # Send states and get moves from agents
        try:
            while not engine.is_game_over(state):
                current_player = state.turn
                cur_agent = agents[current_player]

                try:
                    await cur_agent.send_state(state.to_json())
                    move_json = await cur_agent.get_move()
                    move = Move.from_json(move_json)
                except Exception as e:
                    reason = f"Player {current_player} failed to communicate or generated invalid output: {e}"
                    winner_id = 1 - current_player
                    break

                if not engine.validate_move(state, move):
                    reason = f"Player {current_player} made an invalid move."
                    winner_id = 1 - current_player
                    break

                state = engine.apply_move(state, move)
        finally:
            # Clean up all agent subprocesses
            for agent in agents:
                await agent.cleanup()

        game_status = engine.get_status(state)
        
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

        # Construct exact expected structure if requested
        return {
            "winner": winner_result,
            "scores": scores,
            "reason": reason,
        }

    except Exception as e:
        logger.exception(f"Unexpected exception during execute match {match_id}: {e}")
        return {"status": "error", "reason": str(e)}