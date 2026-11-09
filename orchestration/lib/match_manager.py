import importlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lib import agent_manager
from lib.agent_communication import AgentCommunicationError, AgentProcess, AgentTimeLimitError
from lib.backend_api import BackendAPI
from lib.human_player import HUMAN_PLAYER_ID, HumanPlayer, HumanResignedError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

DEFAULT_TURN_TIME_LIMIT: float = 10.0  # seconds
DEFAULT_HUMAN_TURN_TIME_LIMIT: float = 60.0  # seconds

# Resource-exhaustion caps; configurable via env.
MAX_HISTORY_STATES: int = int(os.getenv("MATCH_MAX_HISTORY_STATES", "5000"))
MATCH_WALL_CLOCK_SECONDS: float = float(os.getenv("MATCH_WALL_CLOCK_SECONDS", "600"))


@dataclass(frozen=True)
class MatchConfig:
    """Normalized match configuration used by the runner."""

    turn_time_limit: float = DEFAULT_TURN_TIME_LIMIT
    human_turn_time_limit: float = DEFAULT_HUMAN_TURN_TIME_LIMIT
    max_duration_seconds: float | None = None


def _parse_match_config(raw_config: dict[str, Any]) -> MatchConfig:
    """
    Normalize a raw match config dictionary into typed values.

    Invalid turn_time_limit values fall back to the default.
    Ensures a minimum of 0.1s.
    """
    raw = raw_config.get("turn_time_limit", DEFAULT_TURN_TIME_LIMIT)

    turn_time_limit = DEFAULT_TURN_TIME_LIMIT
    # If explicitly passed as None (null in JSON), use default
    if raw is not None:
        try:
            turn_time_limit = max(0.1, float(raw))
        except (TypeError, ValueError):
            logger.warning(f"Invalid turn_time_limit {raw!r}, using default {DEFAULT_TURN_TIME_LIMIT}s")

    human_turn_time_limit = _positive_float(raw_config.get("human_turn_time_limit")) or DEFAULT_HUMAN_TURN_TIME_LIMIT
    max_duration_seconds = _positive_float(raw_config.get("max_duration_seconds"))

    return MatchConfig(
        turn_time_limit=turn_time_limit,
        human_turn_time_limit=human_turn_time_limit,
        max_duration_seconds=max_duration_seconds,
    )


def _positive_float(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


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
# Turn helpers
# ---------------------------------------------------------------------------

@dataclass
class TurnOutcome:
    """Result of one player's turn: a move, or the reason the match ends here."""

    move: Any = None
    move_repr: str = ""
    elapsed: float = 0.0
    reason: str = ""
    winner_id: int = -1


async def _play_agent_turn(
    *,
    api: BackendAPI,
    match_id: str,
    agent: AgentProcess,
    state: Any,
    move_cls: Any,
    turn_count: int,
    turn_time_limit: float,
) -> TurnOutcome:
    """Send the state to a dockerized agent and read back its move."""
    current_player = agent.player_id
    # Resume the active agent; keep all others paused
    agent.resume()
    try:
        state_json = state.to_json()
        logger.debug(f"[{match_id}] Turn {turn_count}: sending state to player {current_player}")
        await agent.send_state(state_json)
        # Allow some overhead here in time out but expect exact time limit in returned cpu_time
        raw_move_json, _ = await agent.get_move(timeout=turn_time_limit + 1.5)
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

        if cpu_time > turn_time_limit:
            raise AgentTimeLimitError(
                f"Player {current_player} exceeded the per-turn time limit of "
                f"{turn_time_limit}s. (cpu_time: {cpu_time}s)"
            )

        # Extract the move sub-object if present, otherwise treat the whole response as the move.
        move_data = parsed_output.get("move", parsed_output)
        if not isinstance(move_data, dict):
            raise AgentCommunicationError(
                f"Player {current_player} move field has unexpected type "
                f"{type(move_data).__name__!r}; expected an object."
            )
        move = move_cls.model_validate(move_data, strict=True)

        move_repr = json.dumps(move_data, separators=(",", ":"))
        return TurnOutcome(move=move, move_repr=move_repr, elapsed=cpu_time)
    except AgentTimeLimitError as e:
        winner_id = 1 - current_player
        logger.warning(f"[{match_id}] Turn {turn_count}: {e}")
        await _log(
            api, match_id, "running",
            f"[TURN {turn_count}] Player {current_player} exceeded time limit "
            f"({turn_time_limit}s). Player {winner_id} wins",
        )
        return TurnOutcome(reason="Time limit exceeded", winner_id=winner_id)
    except Exception as e:
        reason = f"Player {current_player} failed to communicate or generated invalid output"
        winner_id = 1 - current_player
        logger.warning(f"[{match_id}] Turn {turn_count}: {reason}" + f": {e}")
        await _log(
            api, match_id, "running",
            f"[TURN {turn_count}] Player {current_player} communication error. "
            f"Player {winner_id} wins",
        )
        return TurnOutcome(reason=reason, winner_id=winner_id)
    finally:
        # Pause the active agent now that its turn is done (or failed)
        agent.pause()


async def _play_human_turn(
    *,
    api: BackendAPI,
    match_id: str,
    human: HumanPlayer,
    engine: Any,
    state: Any,
    move_cls: Any,
    turn_count: int,
    move_time_limit: float,
    match_deadline: float,
) -> TurnOutcome:
    """Wait for the human's move. Illegal moves are logged and ignored, not forfeited."""
    current_player = human.player_id
    winner_id = 1 - current_player
    wall_remaining = max(0.0, match_deadline - time.monotonic())
    timeout = min(move_time_limit, wall_remaining)

    # Report before starting our clock, so the UI countdown can only run short, never long.
    try:
        await api.update_match(match_id, status="running", human_turn_seconds=timeout)
    except Exception as e:
        logger.warning("[%s] Failed to report human move deadline: %s", match_id, e)
    started = time.monotonic()

    async def heartbeat() -> None:
        try:
            await api.update_match(match_id, status="running")
        except Exception as e:
            logger.debug("[%s] Heartbeat failed: %s", match_id, e)

    while True:
        try:
            move_data = await human.get_input(
                timeout=max(0.0, timeout - (time.monotonic() - started)),
                heartbeat=heartbeat,
            )
        except HumanResignedError:
            await _log(
                api, match_id, "running",
                f"[TURN {turn_count}] Player {current_player} (human) resigned. Player {winner_id} wins",
            )
            return TurnOutcome(reason="Resigned", winner_id=winner_id)
        except AgentTimeLimitError:
            if wall_remaining < move_time_limit:
                reason = "Match wall-clock limit exceeded"
                await _log(api, match_id, "running", f"[ABORT] {reason}")
                # winner_id stays -1: the engine status decides the outcome.
                return TurnOutcome(reason=reason, winner_id=-1)
            await _log(
                api, match_id, "running",
                f"[TURN {turn_count}] Player {current_player} (human) exceeded time limit "
                f"({move_time_limit:g}s). Player {winner_id} wins",
            )
            return TurnOutcome(reason="Time limit exceeded", winner_id=winner_id)

        move_repr = json.dumps(move_data, separators=(",", ":"))
        try:
            move = move_cls.model_validate(move_data, strict=True)
            legal = engine.validate_move(state, move)
        except Exception:
            legal = False
        if not legal:
            await _log(
                api, match_id, "running",
                f"[TURN {turn_count}] Player {current_player} (human) illegal move ignored: {move_repr}",
            )
            continue
        return TurnOutcome(move=move, move_repr=move_repr, elapsed=time.monotonic() - started)


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

async def run_match(
    match_id: str,
    config: dict[str, Any],
    agent_ids: list[str],
    image_tags: list[str],
    api: BackendAPI
) -> dict[str, Any]:
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
        turn_limit_str = f"{parsed_config.turn_time_limit}s"
        logger.debug(f"[{match_id}] Per-turn time limit: {parsed_config.turn_time_limit}s")

        # Dynamically import game engine and state based on game_type
        try:
            Engine = importlib.import_module(f"gamelib.{game_type}.engine").Engine
            State = importlib.import_module(f"gamelib.{game_type}.gamestate").GameState
            Move = importlib.import_module(f"gamelib.{game_type}.move").Move
            logger.debug(f"[{match_id}] Imported Engine={Engine.__name__}, State={State.__name__}, Move={Move.__name__}")  # noqa: E501
        except ImportError as e:
            logger.error(f"[{match_id}] Failed to import game modules for type {game_type!r}: {e}")
            return {"status": "error", "reason": f"Game type {game_type} not supported: {e}"}

        # Human-vs-agent: the human takes one seat. From here on, index by seat.
        human_index = match_data.get("human_player_index")
        player_ids: list[str] = list(agent_ids)
        player_images: list[str] = list(image_tags)
        if human_index is not None:
            human_index = int(human_index)
            if not (0 <= human_index <= len(agent_ids)):
                return {"status": "error", "reason": f"Invalid human_player_index {human_index}"}
            player_ids.insert(human_index, HUMAN_PLAYER_ID)
            player_images.insert(human_index, "")

        agents: list[AgentProcess | HumanPlayer] = []
        started_at: list[datetime | None] = []
        for i, tag in enumerate(player_images):
            if i == human_index:
                logger.debug(f"[{match_id}] Player {i} is the human player")
                agents.append(HumanPlayer(match_id, player_id=i))
            else:
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
        state_init_data = match_data.get("config", {}).get("state_init_data", {})
        state = State.initial(state_init_data)
        logger.debug(f"[{match_id}] Game engine and initial state created")
        await _log(
            api, match_id, "running",
            f"[INIT] Game={game_type} | Players={len(player_ids)} | TurnTimeLimit={turn_limit_str}"
            + (
                f" | HumanPlayer={human_index} | HumanMoveLimit={parsed_config.human_turn_time_limit:g}s"
                if human_index is not None
                else ""
            ),
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
                started = (
                    "human player connected"
                    if isinstance(agent, HumanPlayer)
                    else f"started (image={player_images[agent.player_id]!r})"
                )
                await _log(api, match_id, "running", f"[INIT] Player {agent.player_id} {started}")
            except AgentCommunicationError as e:
                logger.error(f"[{match_id}] Agent player {agent.player_id} failed to start/init: {e}")
                await _log(
                    api, match_id, "running",
                    f"[ERROR] Player {agent.player_id} failed to start",
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
                    agent_ids=player_ids,
                    image_tags=player_images,
                    agents=agents,
                    started_at=started_at,
                    status="error",
                    include_stats=False,
                    logs_by_container_id=logs_by_container_id,
                )
                return {"status": "error", "reason": f"Agent {agent.player_id} failed to start/init"}

        # All agents start in a paused state; they are resumed only when it is
        # their turn so they cannot compute ahead of time.
        for agent in agents:
            agent.pause()

        await _report_all_container_snapshots(
            api=api,
            match_id=match_id,
            agent_ids=player_ids,
            image_tags=player_images,
            agents=agents,
            started_at=started_at,
            status="running",
            include_stats=False,
        )

        scores = {player_id: 0 for player_id in player_ids}
        winner_id = -1
        reason = ""
        turn_count = 0
        wall_clock_seconds = MATCH_WALL_CLOCK_SECONDS
        if human_index is not None and parsed_config.max_duration_seconds:
            wall_clock_seconds = parsed_config.max_duration_seconds
        match_deadline = time.monotonic() + wall_clock_seconds
        history_truncated = False

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
                # Stop match at wall-clock limit; winner_id stays -1 so the engine
                # status below decides the outcome.
                if time.monotonic() > match_deadline:
                    reason = "Match wall-clock limit exceeded"
                    logger.warning(f"[{match_id}] {reason} after {turn_count} turn(s)")
                    await _log(api, match_id, "running", f"[ABORT] {reason}")
                    break

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

                if isinstance(cur_agent, HumanPlayer):
                    outcome = await _play_human_turn(
                        api=api,
                        match_id=match_id,
                        human=cur_agent,
                        engine=engine,
                        state=state,
                        move_cls=Move,
                        turn_count=turn_count,
                        move_time_limit=parsed_config.human_turn_time_limit,
                        match_deadline=match_deadline,
                    )
                else:
                    outcome = await _play_agent_turn(
                        api=api,
                        match_id=match_id,
                        agent=cur_agent,
                        state=state,
                        move_cls=Move,
                        turn_count=turn_count,
                        turn_time_limit=parsed_config.turn_time_limit,
                    )
                if outcome.move is None:
                    reason, winner_id = outcome.reason, outcome.winner_id
                    break
                move, move_repr, cpu_time = outcome.move, outcome.move_repr, outcome.elapsed

                if not engine.validate_move(state, move):
                    reason = f"Player {current_player} made an invalid move."
                    logger.warning(f"[{match_id}] Turn {turn_count}: {reason} move={move_repr!r}")
                    winner_id = 1 - current_player
                    await _log(
                        api, match_id, "running",
                        f"[TURN {turn_count}] Player {current_player} invalid move: {move_repr}. "
                        f"Player {winner_id} wins",
                    )
                    break

                state = engine.apply_move(state, move)
                logger.debug(f"[{match_id}] Turn {turn_count}: move applied, updating backend state")
                try:
                    state_json_str = state.to_json()
                    state_dict = json.loads(state_json_str)
                    # Cap stored history.
                    if len(history) < MAX_HISTORY_STATES:
                        history.append(state_dict)
                    elif not history_truncated:
                        history_truncated = True
                        logger.warning(
                            f"[{match_id}] history reached cap of {MAX_HISTORY_STATES} states; "
                            "no longer storing per-turn snapshots"
                        )
                    move_log = f"[TURN {turn_count}] Player {current_player} move: {move_repr} (cpu={cpu_time:.3f}s)"
                    await api.update_match(match_id, status="running", game_state=state_dict, logs=move_log)
                    await _report_all_container_snapshots(
                        api=api,
                        match_id=match_id,
                        agent_ids=player_ids,
                        image_tags=player_images,
                        agents=agents,
                        started_at=started_at,
                        status="running",
                        include_stats=True,
                    )
                    logger.debug(f"[{match_id}] Turn {turn_count}: backend state updated")
                    if isinstance(cur_agent, HumanPlayer):
                        await cur_agent.discard_pending()
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
                agent_ids=player_ids,
                image_tags=player_images,
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
            scores[player_ids[winner_id]] = 1
            winner_result = player_ids[winner_id]
        else:
            winner_result = "draw"

        # Log final result
        if winner_result == "draw":
            result_summary = f"Draw after {turn_count} turn(s). Reason: {reason}"
        else:
            who = "human" if winner_result == HUMAN_PLAYER_ID else f"agent {winner_result}"
            result_summary = (
                f"Player {winner_id} ({who}) wins after {turn_count} turn(s). "
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
