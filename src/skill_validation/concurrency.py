"""Concurrency lock management for the improvement loop.

This module provides file-based concurrency control to prevent multiple
instances of the improvement loop from working on the same issue simultaneously.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


@dataclass
class LockState:
    """Represents the current state of the improvement loop lock."""

    in_progress: int | None  # Issue number currently being worked on
    last_check: datetime
    completed_tasks: list[dict[str, Any]]
    locked_at: datetime | None = None
    locked_by: str | None = None  # Process ID or identifier

    @property
    def is_locked(self) -> bool:
        """Check if there's an active lock."""
        return self.in_progress is not None

    def is_stale(self, stale_threshold_hours: int = 2) -> bool:
        """Check if the current lock is stale (older than threshold)."""
        if not self.is_locked or self.locked_at is None:
            return False
        return datetime.now() - self.locked_at > timedelta(hours=stale_threshold_hours)


class ConcurrencyLock:
    """File-based concurrency lock for the improvement loop.

    This uses a YAML state file to coordinate between multiple processes
    or cron job invocations, ensuring only one instance works on an issue
    at a time.
    """

    DEFAULT_STATE_FILE = ".improvement-loop-state.yaml"
    STALE_THRESHOLD_HOURS = 2

    def __init__(self, state_file: Path | str | None = None):
        self.state_path = Path(state_file) if state_file else Path(self.DEFAULT_STATE_FILE)
        self._lock_acquired = False

    def _load_state(self) -> LockState:
        """Load the current state from the YAML file."""
        if not self.state_path.exists():
            return LockState(
                in_progress=None,
                last_check=datetime.now(),
                completed_tasks=[],
                locked_at=None,
                locked_by=None,
            )

        try:
            with open(self.state_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            # If file is corrupted, reset state
            return LockState(
                in_progress=None,
                last_check=datetime.now(),
                completed_tasks=[],
                locked_at=None,
                locked_by=None,
            )

        # Parse datetime fields
        def parse_datetime(value: str | datetime | None) -> datetime | None:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return None

        return LockState(
            in_progress=data.get("in_progress"),
            last_check=parse_datetime(data.get("last_check")) or datetime.now(),
            completed_tasks=data.get("completed_tasks", []),
            locked_at=parse_datetime(data.get("locked_at")),
            locked_by=data.get("locked_by"),
        )

    def _save_state(self, state: LockState) -> None:
        """Save the state to the YAML file atomically."""
        # Write to a temp file first, then rename for atomicity
        temp_file = self.state_path.with_suffix(".tmp")

        data = {
            "in_progress": state.in_progress,
            "last_check": state.last_check.isoformat(),
            "completed_tasks": state.completed_tasks,
        }

        if state.locked_at:
            data["locked_at"] = state.locked_at.isoformat()
        if state.locked_by:
            data["locked_by"] = state.locked_by

        with open(temp_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        # Atomic rename
        temp_file.replace(self.state_path)

    def acquire(self, issue_number: int) -> bool:
        """Try to acquire the lock for working on an issue.

        Args:
            issue_number: The issue number to lock

        Returns:
            True if lock was acquired, False if already locked by another process
        """
        state = self._load_state()

        # Check if already locked
        if state.is_locked:
            # If stale, we can steal the lock
            if state.is_stale(self.STALE_THRESHOLD_HOURS):
                # Clear the stale lock
                state.in_progress = None
                state.locked_at = None
                state.locked_by = None
            else:
                # Lock is held and not stale
                return False

        # Acquire the lock
        state.in_progress = issue_number
        state.locked_at = datetime.now()
        state.locked_by = f"{os.getpid()}@{os.uname().nodename}"
        state.last_check = datetime.now()

        self._save_state(state)
        self._lock_acquired = True
        return True

    def release(self, completed: bool = True) -> None:
        """Release the lock.

        Args:
            completed: If True, marks the issue as completed in the task list
        """
        if not self._lock_acquired:
            return

        state = self._load_state()

        if completed and state.in_progress is not None:
            # Add to completed tasks
            state.completed_tasks.append(
                {
                    "issue": state.in_progress,
                    "title": f"Issue #{state.in_progress}",
                    "completed_at": datetime.now().isoformat(),
                }
            )

        # Clear the lock
        state.in_progress = None
        state.locked_at = None
        state.locked_by = None
        state.last_check = datetime.now()

        self._save_state(state)
        self._lock_acquired = False

    def get_state(self) -> LockState:
        """Get the current lock state without modifying it."""
        return self._load_state()

    def clear_stale_lock(self) -> bool:
        """Clear a stale lock if one exists.

        Returns:
            True if a stale lock was cleared, False otherwise
        """
        state = self._load_state()

        if state.is_locked and state.is_stale(self.STALE_THRESHOLD_HOURS):
            state.in_progress = None
            state.locked_at = None
            state.locked_by = None
            state.last_check = datetime.now()
            self._save_state(state)
            return True

        return False

    def __enter__(self):
        """Context manager entry - does NOT auto-acquire, use acquire() first."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - releases lock if held."""
        if self._lock_acquired:
            # If we had an exception, don't mark as completed
            self.release(completed=(exc_type is None))
        return False


def check_and_acquire(issue_number: int, state_file: Path | str | None = None) -> tuple[bool, str]:
    """Convenience function to check state and acquire lock for an issue.

    Args:
        issue_number: The issue number to work on
        state_file: Path to the state file (optional)

    Returns:
        Tuple of (success, message)
    """
    lock = ConcurrencyLock(state_file)
    state = lock.get_state()

    # Check if something is already in progress
    if state.is_locked:
        if state.is_stale(lock.STALE_THRESHOLD_HOURS):
            lock.clear_stale_lock()
            # Try to acquire after clearing
            if lock.acquire(issue_number):
                return True, f"Cleared stale lock and acquired for issue #{issue_number}"
            return False, "Failed to acquire lock after clearing stale lock"
        else:
            return (
                False,
                f"Issue #{state.in_progress} is already in progress (locked at {state.locked_at})",
            )

    # Try to acquire
    if lock.acquire(issue_number):
        return True, f"Acquired lock for issue #{issue_number}"
    return False, "Failed to acquire lock"
