from dataclasses import dataclass
from typing import Optional


@dataclass
class RetryState:
    file_path: str
    page_number: Optional[int] = None
    attempts: int = 0
    max_attempts: int = 1
    last_status: str = ""
    last_error: str = ""

    @property
    def can_retry(self):
        return self.attempts < self.max_attempts


class RetryManager:
    def __init__(
        self,
        enabled=True,
        max_attempts=1,
    ):
        self.enabled = bool(
            enabled
        )

        self.max_attempts = max(
            0,
            int(max_attempts),
        )

        self.states = {}

    def make_key(
        self,
        file_path,
        page_number=None,
    ):
        return (
            str(file_path),
            page_number,
        )

    def get_state(
        self,
        file_path,
        page_number=None,
    ):
        key = self.make_key(
            file_path,
            page_number,
        )

        if key not in self.states:
            self.states[key] = RetryState(
                file_path=str(
                    file_path
                ),
                page_number=page_number,
                max_attempts=(
                    self.max_attempts
                ),
            )

        return self.states[key]

    def should_retry(
        self,
        file_path,
        page_number=None,
        status="",
        error="",
    ):
        """
        Возвращает True, если файл или страница
        должны быть обработаны повторно.
        """
        if not self.enabled:
            return False

        state = self.get_state(
            file_path,
            page_number,
        )

        state.last_status = status
        state.last_error = error

        if status in {
            "ok",
            "found",
        }:
            return False

        return state.can_retry

    def register_attempt(
        self,
        file_path,
        page_number=None,
        status="",
        error="",
    ):
        state = self.get_state(
            file_path,
            page_number,
        )

        state.attempts += 1
        state.last_status = status
        state.last_error = error

        return state

    def reset(
        self,
        file_path=None,
        page_number=None,
    ):
        if file_path is None:
            self.states.clear()
            return

        key = self.make_key(
            file_path,
            page_number,
        )

        self.states.pop(
            key,
            None,
        )

    def attempts(
        self,
        file_path,
        page_number=None,
    ):
        state = self.get_state(
            file_path,
            page_number,
        )

        return state.attempts

    def remaining_attempts(
        self,
        file_path,
        page_number=None,
    ):
        state = self.get_state(
            file_path,
            page_number,
        )

        return max(
            0,
            state.max_attempts
            - state.attempts,
        )