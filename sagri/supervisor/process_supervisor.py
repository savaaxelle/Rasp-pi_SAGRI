import time
from pathlib import Path

from sagri.supervisor.managed_process import ManagedProcess

TICK_SECONDS = 1
STARTUP_STAGGER_SECONDS = 1


class ProcessSupervisor:
    """
    Starts a set of program files as subprocesses and keeps them alive.

    Restart policy is data (the program_specs mapping), so which
    programs exist and whether they auto-restart can change without
    touching this class.
    """

    def __init__(self, project_directory: Path, program_specs: dict):
        self._processes = [
            ManagedProcess(
                name=name,
                filepath=project_directory / name,
                project_directory=project_directory,
                auto_restart=auto_restart,
            )
            for name, auto_restart in program_specs.items()
        ]

    def start_all(self) -> None:
        for process in self._processes:
            process.start()
            time.sleep(STARTUP_STAGGER_SECONDS)

    def monitor_forever(self) -> None:
        print()
        print("=" * 50)
        print("SMART LAUNCHER ACTIVE")
        print("=" * 50)
        print()
        print("The launcher is monitoring all programs.")
        print("Important programs will restart automatically if they stop.")
        print("Press Ctrl+C to stop all programs.")
        print()

        try:
            while True:
                now = time.time()

                for process in self._processes:
                    process.poll_and_maybe_restart(now)

                time.sleep(TICK_SECONDS)
        except KeyboardInterrupt:
            print()
            print("=" * 50)
            print("[STOP] Stopping all programs...")
            print("=" * 50)

            self.stop_all()

    def stop_all(self) -> None:
        for process in self._processes:
            process.terminate()

        for process in self._processes:
            process.wait_until_stopped()

        print()
        print("[OK] All programs have been stopped.")
