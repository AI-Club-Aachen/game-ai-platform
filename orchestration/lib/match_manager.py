import importlib
import json
import logging
from dataclasses import dataclass
from typing import Any

from lib.agent_communication import AgentCommunicationError, AgentTimeLimitError, AgentProcess
from lib.backend_api import BackendAPI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

DEFAULT_TURN_TIME_LIMIT: float = 10.0  # seconds


@dataclass(frozen=True)
class MatchConfig:
    """Normalized match configuration used by the runner."""

    turn_time_limit: float | None = DEFAULT_TURN_TIME_LIMIT


def _parse_match_config(raw_config: dict[str, Any]) -> MatchConfig:
    """
    Normalize a raw match config dictionary into typed values.

    Invalid ``turn_time_limit`` values fall back to the default; non-positive
    values disable timeout enforcement.
    """
    raw = raw_config.get("turn_time_limit", DEFAULT_TURN_TIME_LIMIT)
    if raw is None:
        return MatchConfig(turn_time_limit=None)

    try:
        turn_time_limit = float(raw)
    except (TypeError, ValueError):
        logger.warning(f"Invalid turn_time_limit {raw!r}, using default {DEFAULT_TURN_TIME_LIMIT}s")
        return MatchConfig(turn_time_limit=DEFAULT_TURN_TIME_LIMIT)

    return MatchConfig(turn_time_limit=turn_time_limit if turn_time_limit > 0 else None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_agent_image_tags(agent_ids: list[str], api: BackendAPI) -> list[str]:
    image_tags = []
    for agent_id in agent_ids:
        logger.debug(f"Fetching agent metadata for agent {agent_id!r}")
        try:
            agent = await api.get_agent(agent_id)
        except Exception as e:
            raise AgentCommunicationError(f"Could not retrieve agent metadata for {agent_id}: {e}")

        submission_id = agent.get("active_submission_id")
        if not submission_id:
            raise AgentCommunicationError(f"Agent {agent_id} does not have an active submission")

        try:
            submission = await api.get_submission(submission_id)
        except Exception as e:
            raise AgentCommunicationError(f"Could not retrieve submission metadata for agent {agent_id}: {e}")

        build_jobs = submission.get("build_jobs", [])
        logger.debug(f"Agent {agent_id!r} submission {submission_id!r} has {len(build_jobs)} build job(s)")
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


# ---------------------------------------------------------------------------
# Main match entrypoint
# ---------------------------------------------------------------------------

async def run_match(match_id: str, config: dict[str, Any], agent_ids: list[str], api: BackendAPI) -> dict[str, Any]:
    """
    Execute a real match loop using standard I/O communication with dockerized agents.
    """
    logger.debug(f"run_match called | match_id={match_id!r} agent_ids={agent_ids} config={config}")
    try:
        match_data = await api.get_match(match_id)
        game_type = match_data["game_type"]
        logger.debug(f"[{match_id}] Game type resolved: {game_type!r}")

        # ---- Parse typed config ----------------------------------------
        parsed_config = _parse_match_config(config)
        if parsed_config.turn_time_limit is not None:
            logger.debug(f"[{match_id}] Per-turn time limit: {parsed_config.turn_time_limit}s")
        else:
            logger.debug(f"[{match_id}] No per-turn time limit enforced")

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

        # All agents start in a paused state; they are resumed only when it is
        # their turn so they cannot compute ahead of time.
        for agent in agents:
            agent.pause()

        scores = {agent_id: 0 for agent_id in agent_ids}
        winner_id = -1
        reason = ""
        turn_count = 0

        # Initialize history with initial state
        state_dict = json.loads(state.to_json())
        history = [state_dict]

        # Send states and get moves from agents
        try:
            while not engine.is_game_over(state):
                current_player = state.turn
                cur_agent = agents[current_player]
                turn_count += 1
                logger.debug(f"[{match_id}] Turn {turn_count}: player {current_player}'s move")

                # Resume the active agent; keep all others paused
                cur_agent.resume()

                try:
                    state_json = state.to_json()
                    logger.debug(f"[{match_id}] Turn {turn_count}: sending state to player {current_player}")
                    await cur_agent.send_state(state_json)
                    move_json = await cur_agent.get_move(timeout=parsed_config.turn_time_limit)
                    logger.debug(f"[{match_id}] Turn {turn_count}: received move from player {current_player}: {move_json!r}")  # noqa: E501
                    move = Move.from_json(move_json)
                except AgentTimeLimitError as e:
                    reason = f"Time limit exceeded"
                    logger.warning(f"[{match_id}] Turn {turn_count}: {e}")
                    winner_id = 1 - current_player
                    break
                except Exception as e:
                    reason = f"Player {current_player} failed to communicate or generated invalid output: {e}"
                    logger.warning(f"[{match_id}] Turn {turn_count}: {reason}")
                    winner_id = 1 - current_player
                    break
                finally:
                    # Pause the active agent now that its turn is done (or failed)
                    cur_agent.pause()

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
                    history.append(state_dict)
                    await api.update_match(match_id, status="running", game_state=state_dict)
                    logger.debug(f"[{match_id}] Turn {turn_count}: backend state updated")
                except Exception as e:
                    logger.error(f"[{match_id}] Turn {turn_count}: failed to update match game_state: {e}")
        finally:
            # Clean up all agent subprocesses (cleanup() calls resume() first
            # so paused containers receive the termination signal)
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
            "history": history,
        }
        logger.debug(f"[{match_id}] Match result: {result}")
        return result

    except Exception as e:
        logger.exception(f"Unexpected exception during execute match {match_id}: {e}")
        return {"status": "error", "reason": str(e)}
