"""Tests for rate limit budget tracker."""

from __future__ import annotations

import time

from mcp_coda.client import RATE_LIMITS, RateLimitBudget


class TestRateLimitBudget:
    def test_initial_state(self) -> None:
        budget = RateLimitBudget()
        remaining = budget.remaining()
        assert remaining["read"]["remaining"] == RATE_LIMITS["read"]["limit"]
        assert remaining["write"]["remaining"] == RATE_LIMITS["write"]["limit"]
        assert remaining["read"]["used"] == 0
        assert remaining["write"]["used"] == 0

    def test_record_read(self) -> None:
        budget = RateLimitBudget()
        budget.record("GET")
        remaining = budget.remaining()
        assert remaining["read"]["used"] == 1
        assert remaining["read"]["remaining"] == RATE_LIMITS["read"]["limit"] - 1
        assert remaining["write"]["used"] == 0

    def test_record_write(self) -> None:
        budget = RateLimitBudget()
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            budget.record(method)
        remaining = budget.remaining()
        assert remaining["write"]["used"] == 4
        assert remaining["read"]["used"] == 0

    def test_window_expiry(self) -> None:
        budget = RateLimitBudget()
        # Record a call in the past
        past_time = time.monotonic() - 10  # Older than 6s window
        budget._read_calls.append(past_time)
        remaining = budget.remaining()
        # Expired call should be pruned
        assert remaining["read"]["used"] == 0
        assert remaining["read"]["remaining"] == RATE_LIMITS["read"]["limit"]

    def test_budget_at_limit(self) -> None:
        budget = RateLimitBudget()
        for _ in range(RATE_LIMITS["write"]["limit"]):
            budget.record("POST")
        remaining = budget.remaining()
        assert remaining["write"]["remaining"] == 0
        assert remaining["write"]["used"] == RATE_LIMITS["write"]["limit"]

    def test_case_insensitive_method(self) -> None:
        budget = RateLimitBudget()
        budget.record("post")
        remaining = budget.remaining()
        assert remaining["write"]["used"] == 1
