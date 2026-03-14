import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import docker
import yaml

logger = logging.getLogger(__name__)

class AgentCommunicationError(Exception):
    pass

def load_secure_defaults() -> dict[str, Any]:
    settings_path = Path(__file__).parent.parent / "secure_default_settings.yaml"
    if not settings_path.exists():
        logger.warning("secure_default_settings.yaml not found")
        return {}
    with open(settings_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def build_docker_run_args() -> list[str]:
    settings = load_secure_defaults()
    args = []
    
    if "cap_drop" in settings:
        for cap in settings["cap_drop"]:
            args.extend(["--cap-drop", cap])
    if "security_opt" in settings:
        for opt in settings["security_opt"]:
            args.extend(["--security-opt", opt])
    if settings.get("read_only"):
        args.append("--read-only")
    if "tmpfs" in settings:
        for path, opts in settings["tmpfs"].items():
            args.extend(["--tmpfs", f"{path}:{opts}"])
    if "pids_limit" in settings:
        args.extend(["--pids-limit", str(settings["pids_limit"])])
    if "ulimits" in settings:
        for ulim in settings["ulimits"]:
            args.extend(["--ulimit", f"{ulim['name']}={ulim['soft']}:{ulim['hard']}"])
    if "mem_limit" in settings:
        args.extend(["--memory", settings["mem_limit"]])
    if "nano_cpus" in settings:
        args.extend(["--cpus", str(settings["nano_cpus"] / 1_000_000_000)])
    if "network_mode" in settings:
        args.extend(["--network", settings["network_mode"]])
    
    return args

class AgentProcess:
    def __init__(self, image_tag: str, player_id: int):
        self.image_tag = image_tag
        self.player_id = player_id
        self.process: asyncio.subprocess.Process | None = None
        self.client = docker.from_env()

    def verify_image(self) -> None:
        """Must check whether the given image exists."""
        try:
            self.client.images.get(self.image_tag)
        except docker.errors.ImageNotFound:
            raise AgentCommunicationError(f"Image {self.image_tag} not found.")
        except docker.errors.APIError as e:
            raise AgentCommunicationError(f"Docker API error verifying image {self.image_tag}: {e}")

    async def start(self) -> None:
        cmd_args = ["run", "-i", "--rm"]
        cmd_args.extend(build_docker_run_args())
        
        # Environment to indicate to agent it is running in online mode
        cmd_args.extend(["-e", "AGENT_ONLINE=1"])
        
        cmd_args.append(self.image_tag)

        try:
            self.process = await asyncio.create_subprocess_exec(
                "docker", *cmd_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception as e:
            raise AgentCommunicationError(f"Failed to start container process: {e}")

    async def send_init(self) -> None:
        init_data = {"player_id": self.player_id}
        await self._send_json(init_data)

    async def send_state(self, state_json: str) -> None:
        if not self.process or not self.process.stdin:
            raise AgentCommunicationError("Process not started or stdin not available.")
        try:
            self.process.stdin.write((state_json + "\n").encode("utf-8"))
            await self.process.stdin.drain()
        except BaseException as e:
            raise AgentCommunicationError(f"Failed to send state: {e}")

    async def get_move(self) -> str:
        if not self.process or not self.process.stdout:
            raise AgentCommunicationError("Process not started or stdout not available.")
        
        try:
            # We enforce a timeout for each move
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout=30.0)
            if not line:
                raise AgentCommunicationError("Agent process disconnected unexpectedly.")
            return line.decode("utf-8").strip()
        except asyncio.TimeoutError:
            raise AgentCommunicationError("Timeout waiting for agent move.")
        except BaseException as e:
            raise AgentCommunicationError(f"Error reading move: {e}")

    async def _send_json(self, data: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise AgentCommunicationError("Process not started.")
        data_str = json.dumps(data) + "\n"
        try:
            self.process.stdin.write(data_str.encode("utf-8"))
            await self.process.stdin.drain()
        except BaseException as e:
            raise AgentCommunicationError(f"Failed to send json payload: {e}")

    async def cleanup(self) -> None:
        if self.process:
            if self.process.returncode is None:
                try:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
                except ProcessLookupError:
                    pass

            if self.process.stderr:
                try:
                    err = await self.process.stderr.read()
                    if err:
                        logger.debug(f"Agent stdout/err remainder: {err.decode('utf-8', errors='replace')}")
                except Exception:
                    pass