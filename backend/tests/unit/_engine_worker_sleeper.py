"""A job-child target for worker tests: imported by name in a spawned process."""

from __future__ import annotations

import time


def sleep_child(*_args: object) -> None:
    time.sleep(120)
