"""Hold an exclusive nonblocking file lock on Windows and POSIX.

Inputs: open writable lock-file handle. Outputs: acquired lock or BlockingIOError.
Identity: at most one cooperating process holds the lock until release/close.
Tier: 1. Run: project .venv/bin/python -m pytest tests/test_file_lock.py.
"""
import errno
import os


def acquire_exclusive(handle):
    if os.name == 'nt':
        import msvcrt

        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write('\0')
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise BlockingIOError('Another process holds this lock') from exc
            raise
    else:
        import fcntl

        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)


def release(handle):
    if os.name == 'nt':
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle, fcntl.LOCK_UN)
