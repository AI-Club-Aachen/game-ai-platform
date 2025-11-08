import json
import queue
import threading
import time
from typing import Any, Optional

import pytest

from gamelib.agent_base import AgentBase


class AgentIO:
    """
    Thread-safe I/O buffers for AgentBase during tests.
    """
    _SENTINEL = object()

    def __init__(self):
        self._in_q: "queue.Queue[Any]" = queue.Queue()
        self._out_q: "queue.Queue[str]" = queue.Queue()
        self._closed = False
        self._threads = []

    # ---- Input (stdin) helpers ----
    def write_input(self, data: Any):
        """
        Enqueue a single input line.
        Accepts str; if not str, JSON encodes the object.
        """
        if self._closed:
            raise RuntimeError("Input closed")
        line = data if isinstance(data, str) else json.dumps(data)
        self._in_q.put(line)

    def write_inputs(self, items: list[Any]):
        for item in items:
            self.write_input(item)

    def close_input(self):
        """
        Signal EOF to the agent loop.
        """
        self._closed = True
        self._in_q.put(self._SENTINEL)

    # ---- Output (stdout) helpers ----
    def read_output(self, timeout: Optional[float] = None) -> str:
        """
        Blocks until an output line is available or timeout.
        """
        return self._out_q.get(timeout=timeout)

    def try_read_output(self) -> Optional[str]:
        try:
            return self._out_q.get_nowait()
        except queue.Empty:
            return None

    def drain_outputs(self) -> list[str]:
        items = []
        while True:
            try:
                items.append(self._out_q.get_nowait())
            except queue.Empty:
                break
        return items

    # ---- Agent runner helper ----
    def start_agent(self, agent_cls: type, *args, daemon: bool = True, **kwargs) -> threading.Thread:
        """
        Start the given Agent class in a background thread.
        Returns the thread so tests can join if desired.
        """
        t = threading.Thread(target=agent_cls, args=args, kwargs=kwargs, daemon=daemon)
        t.start()
        self._threads.append(t)
        return t

    # ---- Internal used by patched methods ----
    def _get_input_blocking(self) -> str:
        item = self._in_q.get()
        if item is self._SENTINEL:
            raise EOFError("Test input closed")
        return item

    def _put_output(self, line: str):
        self._out_q.put(line)

    # ---- Cleanup ----
    def join_agents(self, timeout: Optional[float] = None):
        end = time.time() + timeout if timeout else None
        for t in list(self._threads):
            remaining = (end - time.time()) if end else None
            t.join(0 if remaining is None else max(0, remaining))


@pytest.fixture
def agent_io(monkeypatch):
    """
    Patches AgentBase._read_input/_write_output to use in-memory queues.
    Returns an AgentIO object with helpers:
      - write_input(data), write_inputs(list), close_input()
      - read_output(timeout), try_read_output(), drain_outputs()
      - start_agent(agent_cls, ...)
      - join_agents(timeout)
    """
    io = AgentIO()

    # Keep originals in case we fall back
    orig_read_input = AgentBase._read_input
    orig_write_output = AgentBase._write_output

    # Attach to class so patched methods can find it
    AgentBase._test_io = io

    def _patched_read_input(self):
        test_io = getattr(AgentBase, "_test_io", None)
        if test_io is None:
            return orig_read_input(self)
        return test_io._get_input_blocking()

    def _patched_write_output(self, output: str):
        test_io = getattr(AgentBase, "_test_io", None)
        if test_io is None:
            return orig_write_output(self, output)
        test_io._put_output(output)

    monkeypatch.setattr(AgentBase, "_read_input", _patched_read_input, raising=True)
    monkeypatch.setattr(AgentBase, "_write_output", _patched_write_output, raising=True)

    try:
        yield io
    finally:
        # Teardown
        AgentBase._test_io = None
        io.close_input()
        io.join_agents(timeout=2.0)
