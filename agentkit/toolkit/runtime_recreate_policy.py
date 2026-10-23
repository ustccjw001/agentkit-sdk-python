# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Runtime deletion/recreation safety policy helpers."""

from __future__ import annotations

import sys
from typing import Callable, Literal, Optional

from agentkit.toolkit.reporter import Reporter

RuntimeRecreatePolicy = Literal["prompt", "always", "never"]


def parse_runtime_recreate_policy(value: Optional[str]) -> RuntimeRecreatePolicy:
    """Parse the CLI value for ``--recreate-runtime``."""
    if value is None or value.strip() == "":
        return "prompt"
    normalized = value.strip().lower()
    if normalized == "yes":
        return "always"
    if normalized == "no":
        return "never"
    raise ValueError("--recreate-runtime must be yes or no.")


def normalize_runtime_recreate_policy(
    value: Optional[str],
) -> RuntimeRecreatePolicy:
    """Normalize SDK/internal policy values early in the execution chain."""
    if value is None or value.strip() == "":
        return "prompt"
    normalized = value.strip().lower()
    if normalized in {"prompt", "always", "never"}:
        return normalized  # type: ignore[return-value]
    if normalized == "yes":
        return "always"
    if normalized == "no":
        return "never"
    raise ValueError(
        "runtime_recreate_policy must be prompt, always, or never "
        "(yes/no are accepted as aliases)."
    )


def runtime_gateway_replacement_reason() -> str:
    return (
        "requires replacement because gateway settings can only be "
        "applied when a Runtime is created"
    )


def runtime_recreate_prompt_message(
    runtime_id: str,
    reason: str,
) -> str:
    return (
        f"Runtime {runtime_id} {reason}. Delete and recreate it? This will change "
        "the Runtime id and may affect egress IP, observability data, and version "
        "history."
    )


def runtime_recreate_preserved_message(
    runtime_id: str,
    reason: str,
) -> str:
    return (
        f"Runtime {runtime_id} {reason}; delete/recreate was not confirmed, so the "
        "existing Runtime was preserved."
    )


def should_recreate_runtime(
    policy: RuntimeRecreatePolicy,
    *,
    runtime_id: str,
    reason: str,
    reporter: Reporter,
    is_interactive: Optional[Callable[[], bool]] = None,
) -> bool:
    """Return whether deleting/recreating a runtime is allowed."""
    if policy == "always":
        return True
    if policy == "never":
        return False
    if policy != "prompt":
        raise ValueError(f"Invalid Runtime recreate policy: {policy!r}")

    check_interactive = is_interactive or sys.stdin.isatty
    if not check_interactive():
        return False

    try:
        return bool(
            reporter.confirm(
                runtime_recreate_prompt_message(runtime_id, reason),
                default=False,
            )
        )
    except (KeyboardInterrupt, EOFError):
        return False


__all__ = [
    "RuntimeRecreatePolicy",
    "runtime_gateway_replacement_reason",
    "normalize_runtime_recreate_policy",
    "parse_runtime_recreate_policy",
    "runtime_recreate_prompt_message",
    "runtime_recreate_preserved_message",
    "should_recreate_runtime",
]
