"""Cross-platform single-instance process lock for the bot."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

if os.name == "nt":
    import ctypes

    _ERROR_ALREADY_EXISTS = 183
else:
    import fcntl


class SingleInstanceLock:
    """Prevent accidental startup of multiple bot processes."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._handle = None
        self._file_handle = None
        self._path = Path(tempfile.gettempdir()) / f"{name}.lock"

    def acquire(self) -> bool:
        """Try to acquire the lock without blocking."""

        if os.name == "nt":
            return self._acquire_windows()
        return self._acquire_posix()

    def release(self) -> None:
        """Release the lock if it is currently held."""

        if os.name == "nt":
            self._release_windows()
            return
        self._release_posix()

    def _acquire_windows(self) -> bool:
        """Use a named mutex on Windows."""

        mutex_name = f"Local\\{self._name}"
        handle = ctypes.windll.kernel32.CreateMutexW(None, True, mutex_name)
        if not handle:
            return False

        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == _ERROR_ALREADY_EXISTS:
            ctypes.windll.kernel32.CloseHandle(handle)
            return False

        self._handle = handle
        return True

    def _release_windows(self) -> None:
        """Release Windows named mutex."""

        if self._handle is None:
            return

        try:
            ctypes.windll.kernel32.ReleaseMutex(self._handle)
        except OSError:
            pass
        finally:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None

    def _acquire_posix(self) -> bool:
        """Use flock on POSIX systems."""

        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False

        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        self._file_handle = handle
        return True

    def _release_posix(self) -> None:
        """Release POSIX file lock."""

        if self._file_handle is None:
            return

        try:
            fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            self._file_handle.close()
            self._file_handle = None
