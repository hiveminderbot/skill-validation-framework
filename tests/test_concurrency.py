"""Tests for concurrency lock mechanism."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from skill_validation.concurrency import ConcurrencyLock, LockState, check_and_acquire


class TestConcurrencyLock:
    """Test suite for the concurrency lock mechanism."""

    def test_initial_state(self):
        """Test that a new lock has the correct initial state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"
            lock = ConcurrencyLock(state_file)
            state = lock.get_state()

            assert state.in_progress is None
            assert not state.is_locked
            assert not state.is_stale()

    def test_acquire_lock(self):
        """Test acquiring a lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"
            lock = ConcurrencyLock(state_file)

            assert lock.acquire(1)
            state = lock.get_state()
            assert state.in_progress == 1
            assert state.is_locked
            assert state.locked_at is not None
            assert state.locked_by is not None

    def test_acquire_already_locked(self):
        """Test that acquiring a held lock fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"
            lock1 = ConcurrencyLock(state_file)
            lock2 = ConcurrencyLock(state_file)

            assert lock1.acquire(1)
            assert not lock2.acquire(2)  # Should fail, already locked

    def test_release_lock(self):
        """Test releasing a lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"
            lock = ConcurrencyLock(state_file)

            lock.acquire(1)
            lock.release(completed=True)

            state = lock.get_state()
            assert state.in_progress is None
            assert not state.is_locked
            assert len(state.completed_tasks) == 1

    def test_stale_lock_detection(self):
        """Test that stale locks are detected correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"
            lock = ConcurrencyLock(state_file)

            # Create a stale lock manually
            state = lock.get_state()
            state.in_progress = 1
            state.locked_at = datetime.now() - timedelta(hours=3)
            state.locked_by = "test"
            lock._save_state(state)

            # Check it's detected as stale
            state = lock.get_state()
            assert state.is_stale

            # Clear it
            assert lock.clear_stale_lock()
            state = lock.get_state()
            assert not state.is_locked

    def test_context_manager(self):
        """Test the context manager protocol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"
            lock = ConcurrencyLock(state_file)

            lock.acquire(1)
            with lock:
                pass  # Lock should be released on exit

            state = lock.get_state()
            assert not state.is_locked


class TestCheckAndAcquire:
    """Test the check_and_acquire convenience function."""

    def test_successful_acquire(self):
        """Test successful lock acquisition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"
            success, message = check_and_acquire(1, state_file)

            assert success
            assert "Acquired" in message

    def test_already_locked(self):
        """Test that check_and_acquire fails when already locked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # First acquisition
            lock = ConcurrencyLock(state_file)
            lock.acquire(1)

            # Second should fail
            success, message = check_and_acquire(2, state_file)
            assert not success
            assert "already in progress" in message
