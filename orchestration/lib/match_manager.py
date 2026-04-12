import importlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lib import agent_manager
from lib.agent_communication import AgentCommunicationError, AgentProcess, AgentTimeLimitError
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


def _uptime_seconds(started_at: datetime | None) -> float:
    if started_at is None:
        return 0.0
    return max(0.0, (datetime.now(UTC) - started_at).total_seconds())


def _collect_container_logs(agents: list[AgentProcess], match_id: str) -> dict[str, str]:
    logs_by_container_id: dict[str, str] = {}
    for agent in agents:
        container_id = agent.container_id
        if not container_id:
            continue

        logs = ""
        try:
            logs = agent_manager.get_container_logs(container_id, tail=5000)
        except Exception as e:
            logger.debug("[%s] Failed collecting docker logs for %s: %s", match_id, container_id, e)

        stderr_tail = (agent.stderr_tail or "").strip()
        if stderr_tail:
            logs = f"{logs}\n{stderr_tail}".strip() if logs else stderr_tail

        if logs:
            logs_by_container_id[container_id] = logs

    return logs_by_container_id


async def _report_all_container_snapshots(
    *,
    api: BackendAPI,
    match_id: str,
    agent_ids: list[str],
    image_tags: list[str],
    agents: list[AgentProcess],
    started_at: list[datetime | None],
    status: str,
    include_stats: bool,
    logs_by_container_id: dict[str, str] | None = None,
) -> None:
    def _status_from_runtime(runtime_status: str | None, fallback: str) -> str:
        if runtime_status in {"running", "paused", "restarting", "created"}:
            return "running"
        if runtime_status in {"exited", "dead", "removing"}:
            return "stopped"
        return fallback

    for i, agent in enumerate(agents):
        container_id = agent.container_id
        if not container_id:
            continue

        payload: dict[str, Any] = {
            "container_id": container_id,
            "match_id": match_id,
            "agent_id": agent_ids[i],
            "agent_name": agent_ids[i],
            "name": container_id[:12],
            "status": status,
            "image": image_tags[i],
            "uptime_seconds": _uptime_seconds(started_at[i]),
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
        }

        if logs_by_container_id is not None and container_id in logs_by_container_id:
            payload["logs"] = logs_by_container_id.get(container_id)

        try:
            container = agent.client.containers.get(container_id)
            payload["name"] = container.name or payload["name"]

            # Only let runtime state drive status while the match is active.
            # For terminal snapshots (e.g., stopped/error), keep explicit status.
            if status == "running":
                payload["status"] = _status_from_runtime(container.status, status)
        except Exception:
            pass

        if include_stats:
            try:
                stats = agent_manager.get_container_stats(container_id)
                memory_usage = float(stats.get("memory_usage") or 0.0)
                payload["cpu_percent"] = float(stats.get("cpu_percent") or 0.0)
                payload["memory_mb"] = memory_usage / (1024.0 * 1024.0)
            except Exception as e:
                logger.debug("[%s] Failed reading stats for container %s: %s", match_id, container_id, e)

        try:
            await api.report_container_stats(payload)
        except Exception as e:
            logger.warning("[%s] Failed reporting container snapshot for %s: %s", match_id, container_id, e)


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

async def _log(api: BackendAPI, match_id: str, status: str, msg: str) -> None:
    """Push a single log line to the backend without raising on failure."""
    try:
        await api.update_match(match_id, status=status, logs=msg)
    except Exception as exc:
        logger.warning("[%s] Failed to push log to backend: %s", match_id, exc)


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
        turn_limit_str = (
            f"{parsed_config.turn_time_limit}s" if parsed_config.turn_time_limit is not None else "none"
        )
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
        started_at: list[datetime | None] = []
        for i, tag in enumerate(image_tags):
            logger.debug(f"[{match_id}] Creating AgentProcess for player {i} with image {tag!r}")
            agents.append(AgentProcess(tag, player_id=i))
            started_at.append(None)

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
        await _log(
            api, match_id, "running",
            f"[INIT] Game={game_type} | Players={len(agent_ids)} | TurnTimeLimit={turn_limit_str}",
        )

        # Start and initialize each agent
        for agent in agents:
            logger.debug(f"[{match_id}] Starting agent process for player {agent.player_id}")
            try:
                await agent.start()
                logger.debug(f"[{match_id}] Agent process started for player {agent.player_id}, sending init")
                await agent.send_init()
                started_at[agent.player_id] = datetime.now(UTC)
                logger.debug(f"[{match_id}] Agent player {agent.player_id} init sent successfully")
                await _log(
                    api, match_id, "running",
                    f"[INIT] Player {agent.player_id} started (image={image_tags[agent.player_id]!r})",
                )
            except AgentCommunicationError as e:
                logger.error(f"[{match_id}] Agent player {agent.player_id} failed to start/init: {e}")
                await _log(
                    api, match_id, "running",
                    f"[ERROR] Player {agent.player_id} failed to start: {e}",
                )

                logs_by_container_id = _collect_container_logs(agents, match_id)
                for a in agents:
                    await a.cleanup()
                # Append any stderr emitted during cleanup/termination.
                logs_by_container_id = {
                    **logs_by_container_id,
                    **_collect_container_logs(agents, match_id),
                }

                await _report_all_container_snapshots(
                    api=api,
                    match_id=match_id,
                    agent_ids=agent_ids,
                    image_tags=image_tags,
                    agents=agents,
                    started_at=started_at,
                    status="error",
                    include_stats=False,
                    logs_by_container_id=logs_by_container_id,
                )
                return {"status": "error", "reason": f"Agent {agent.player_id} failed to start/init: {e}"}

        # All agents start in a paused state; they are resumed only when it is
        # their turn so they cannot compute ahead of time.
        for agent in agents:
            agent.pause()

        await _report_all_container_snapshots(
            api=api,
            match_id=match_id,
            agent_ids=agent_ids,
            image_tags=image_tags,
            agents=agents,
            started_at=started_at,
            status="running",
            include_stats=False,
        )

        scores = {agent_id: 0 for agent_id in agent_ids}
        winner_id = -1
        reason = ""
        turn_count = 0

        # Initialize history with initial state and push it to the backend
        state_dict = json.loads(state.to_json())
        history = [state_dict]
        await api.update_match(
            match_id,
            status="running",
            game_state=state_dict,
            logs="[INIT] Initial game state set",
        )

        # Send states and get moves from agents
        try:
            while not engine.is_game_over(state):
                current_player = state.turn
                if current_player < 0 or current_player >= len(agents):
                    return {
                        "status": "error",
                        "reason": (
                            f"Engine requested player index {current_player}, "
                            f"but only {len(agents)} agent(s) were provided"
                        ),
                    }
                cur_agent = agents[current_player]
                turn_count += 1
                logger.debug(f"[{match_id}] Turn {turn_count}: player {current_player}'s move")

                # Resume the active agent; keep all others paused
                cur_agent.resume()

                try:
                    state_json = state.to_json()
                    logger.debug(f"[{match_id}] Turn {turn_count}: sending state to player {current_player}")
                    await cur_agent.send_state(state_json)
                    # Allow some overhead here in time out but expect exact time limit in returned cpu_time
                    raw_move_json = await cur_agent.get_move(timeout=parsed_config.turn_time_limit + 1.5)
                    logger.debug(f"[{match_id}] Turn {turn_count}: received move from player {current_player}: {raw_move_json!r}")  # noqa: E501

                    # --- Safe JSON parsing ---------------------------------------
                    try:
                        parsed_output = json.loads(raw_move_json)
                    except json.JSONDecodeError as e:
                        raise AgentCommunicationError(
                            f"Player {current_player} returned invalid JSON: {e}"
                        )

                    # parsed_output must be a mapping; reject any other type
                    # (e.g. a bare list or string) to prevent type confusion.
                    if not isinstance(parsed_output, dict):
                        raise AgentCommunicationError(
                            f"Player {current_player} returned unexpected JSON type "
                            f"{type(parsed_output).__name__!r}; expected an object."
                        )

                    # cpu_time must be a real number; coerce defensively.
                    raw_cpu_time = parsed_output.get("cpu_time", 0.0)
                    try:
                        cpu_time = float(raw_cpu_time)
                    except (TypeError, ValueError):
                        logger.warning(
                            f"[{match_id}] Turn {turn_count}: "
                            f"player {current_player} sent non-numeric cpu_time "
                            f"{raw_cpu_time!r}; defaulting to 0.0"
                        )
                        cpu_time = 0.0

                    if cpu_time > parsed_config.turn_time_limit:
                        raise AgentTimeLimitError(
                            f"Player {current_player} exceeded the per-turn time limit of "
                            f"{parsed_config.turn_time_limit}s. (cpu_time: {cpu_time}s)"
                        )

                    # Extract the move sub-object if present, otherwise treat the whole response as the move.
                    move_data = parsed_output.get("move", parsed_output)
                    if not isinstance(move_data, dict):
                        raise AgentCommunicationError(
                            f"Player {current_player} move field has unexpected type "
                            f"{type(move_data).__name__!r}; expected an object."
                        )
                    move = Move.model_validate(move_data, strict=True)

                    move_repr = json.dumps(move_data, separators=(",", ":"))
                except AgentTimeLimitError as e:
                    reason = "Time limit exceeded"
                    logger.warning(f"[{match_id}] Turn {turn_count}: {e}")
                    winner_id = 1 - current_player
                    await _log(
                        api, match_id, "running",
                        f"[TURN {turn_count}] Player {current_player} exceeded time limit "
                        f"({parsed_config.turn_time_limit}s) — Player {winner_id} wins",
                    )
                    break
                except Exception as e:
                    reason = f"Player {current_player} failed to communicate or generated invalid output: {e}"
                    logger.warning(f"[{match_id}] Turn {turn_count}: {reason}")
                    winner_id = 1 - current_player
                    await _log(
                        api, match_id, "running",
                        f"[TURN {turn_count}] Player {current_player} communication error: {e} "
                        f"— Player {winner_id} wins",
                    )
                    break
                finally:
                    # Pause the active agent now that its turn is done (or failed)
                    cur_agent.pause()

                if not engine.validate_move(state, move):
                    reason = f"Player {current_player} made an invalid move."
                    logger.warning(f"[{match_id}] Turn {turn_count}: {reason} move={move_repr!r}")
                    winner_id = 1 - current_player
                    await _log(
                        api, match_id, "running",
                        f"[TURN {turn_count}] Player {current_player} invalid move: {move_repr} "
                        f"— Player {winner_id} wins",
                    )
                    break

                state = engine.apply_move(state, move)
                logger.debug(f"[{match_id}] Turn {turn_count}: move applied, updating backend state")
                try:
                    state_json_str = state.to_json()
                    state_dict = json.loads(state_json_str)
                    history.append(state_dict)
                    move_log = f"[TURN {turn_count}] Player {current_player} move: {move_repr} (cpu={cpu_time:.3f}s)"
                    await api.update_match(match_id, status="running", game_state=state_dict, logs=move_log)
                    await _report_all_container_snapshots(
                        api=api,
                        match_id=match_id,
                        agent_ids=agent_ids,
                        image_tags=image_tags,
                        agents=agents,
                        started_at=started_at,
                        status="running",
                        include_stats=True,
                    )
                    logger.debug(f"[{match_id}] Turn {turn_count}: backend state updated")
                except Exception as e:
                    logger.error(f"[{match_id}] Turn {turn_count}: failed to update match game_state: {e}")
        finally:
            # Clean up all agent subprocesses (cleanup() calls resume() first
            # so paused containers receive the termination signal)
            logger.debug(f"[{match_id}] Cleaning up {len(agents)} agent process(es)")

            logs_by_container_id = _collect_container_logs(agents, match_id)

            for agent in agents:
                await agent.cleanup()

            logs_by_container_id = {
                **logs_by_container_id,
                **_collect_container_logs(agents, match_id),
            }

            await _report_all_container_snapshots(
                api=api,
                match_id=match_id,
                agent_ids=agent_ids,
                image_tags=image_tags,
                agents=agents,
                started_at=started_at,
                status="stopped",
                include_stats=False,
                logs_by_container_id=logs_by_container_id,
            )
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

        # Log final result
        if winner_result == "draw":
            result_summary = f"Draw after {turn_count} turn(s). Reason: {reason}"
        else:
            result_summary = (
                f"Player {winner_id} (agent {winner_result}) wins after {turn_count} turn(s). "
                f"Reason: {reason}"
            )
        await _log(api, match_id, "running", f"[RESULT] {result_summary}")
        logger.debug(f"[{match_id}] Match result: winner={winner_result!r} reason={reason!r} turns={turn_count}")

        result = {
            "winner": winner_result,
            "scores": scores,
            "reason": reason,
            "history": history,
        }
        return result

    except Exception as e:
        logger.exception(f"Unexpected exception during execute match {match_id}: {e}")
        return {"status": "error", "reason": str(e)}
