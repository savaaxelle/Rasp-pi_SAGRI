import subprocess
import sys
from pathlib import Path

DEFAULT_RESTART_DELAY = 5


class ManagedProcess:
    """
    Wraps one subprocess: starting it, polling whether it's still alive,
    and restarting it on the configured policy.
    """

    def __init__(
        self,
        name: str,
        filepath: Path,
        project_directory: Path,
        auto_restart: bool,
        restart_delay: float = DEFAULT_RESTART_DELAY,
    ):
        self._name = name
        self._filepath = filepath
        self._project_directory = project_directory
        self._auto_restart = auto_restart
        self._restart_delay = restart_delay

        self._process = None
        self._reported = False
        self._last_restart = 0.0

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        if not self._filepath.exists():
            print(f"[ERROR] File not found: {self._filepath}")
            self._process = None
            return

        print(f"[START] Starting {self._name}")

        try:
            self._process = subprocess.Popen(
                # sys.executable, not a literal "python3": guarantees
                # every subprocess uses the same interpreter (and venv,
                # if any) as run_raspi_all.py itself.
                [sys.executable, str(self._filepath)],
                cwd=str(self._project_directory),
            )
        except Exception as error:
            print(f"[ERROR] Failed to start {self._name}")
            print(f"        {error}")
            self._process = None

        self._reported = False

    def poll_and_maybe_restart(self, now: float) -> None:
        """Check process state, log transitions, and restart if configured."""

        if self._process is None:
            self._maybe_restart(now, retry=True)
            return

        return_code = self._process.poll()

        # Still running.
        if return_code is None:
            self._reported = False
            return

        if not self._reported:
            if return_code == 0:
                print(f"[INFO] {self._name} finished normally (code 0)")
            else:
                print(f"[WARNING] {self._name} stopped (code {return_code})")
            self._reported = True

        self._maybe_restart(now, retry=False)

    def _maybe_restart(self, now: float, retry: bool) -> None:
        if not self._auto_restart:
            return

        if now - self._last_restart < self._restart_delay:
            return

        if retry:
            print(f"[RETRY] Attempting to start {self._name} again...")
        else:
            print(f"[RESTART] Restarting {self._name}...")

        self.start()
        self._last_restart = now

    def terminate(self) -> None:
        if self._process is None:
            return

        if self._process.poll() is None:
            print(f"[STOP] {self._name}")
            self._process.terminate()

    def wait_until_stopped(self, timeout: float = DEFAULT_RESTART_DELAY) -> None:
        if self._process is None:
            return

        if self._process.poll() is None:
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                print(f"[FORCE STOP] {self._name}")
                self._process.kill()
