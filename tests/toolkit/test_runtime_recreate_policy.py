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

import pytest

from agentkit.toolkit.runtime_recreate_policy import (
    normalize_runtime_recreate_policy,
    parse_runtime_recreate_policy,
    runtime_gateway_replacement_reason,
    runtime_recreate_preserved_message,
    runtime_recreate_prompt_message,
    should_recreate_runtime,
)


class _Reporter:
    def __init__(self, answer=True, exc=None):
        self.answer = answer
        self.exc = exc
        self.calls = []

    def confirm(self, message, default=False):
        self.calls.append((message, default))
        if self.exc:
            raise self.exc
        return self.answer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "prompt"),
        ("", "prompt"),
        ("  ", "prompt"),
        ("yes", "always"),
        ("YES", "always"),
        (" no ", "never"),
    ],
)
def test_parse_runtime_recreate_policy(raw, expected):
    assert parse_runtime_recreate_policy(raw) == expected


def test_parse_runtime_recreate_policy_rejects_invalid_value():
    with pytest.raises(ValueError, match="--recreate-runtime must be yes or no"):
        parse_runtime_recreate_policy("maybe")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "prompt"),
        ("", "prompt"),
        ("prompt", "prompt"),
        ("always", "always"),
        ("never", "never"),
        ("yes", "always"),
        ("no", "never"),
    ],
)
def test_normalize_runtime_recreate_policy(raw, expected):
    assert normalize_runtime_recreate_policy(raw) == expected


def test_normalize_runtime_recreate_policy_rejects_invalid_value():
    with pytest.raises(ValueError, match="runtime_recreate_policy must be"):
        normalize_runtime_recreate_policy("maybe")


def test_runtime_recreate_policy_always_and_never_do_not_prompt():
    reporter = _Reporter()

    assert (
        should_recreate_runtime(
            "always", runtime_id="rt-1", reason="needs replacement", reporter=reporter
        )
        is True
    )
    assert (
        should_recreate_runtime(
            "never", runtime_id="rt-1", reason="needs replacement", reporter=reporter
        )
        is False
    )
    assert reporter.calls == []


def test_runtime_recreate_policy_prompt_returns_false_for_non_tty():
    reporter = _Reporter()

    assert (
        should_recreate_runtime(
            "prompt",
            runtime_id="rt-1",
            reason="needs replacement",
            reporter=reporter,
            is_interactive=lambda: False,
        )
        is False
    )
    assert reporter.calls == []


def test_runtime_recreate_policy_prompt_uses_default_no():
    reporter = _Reporter(answer=True)

    assert (
        should_recreate_runtime(
            "prompt",
            runtime_id="rt-1",
            reason="needs replacement",
            reporter=reporter,
            is_interactive=lambda: True,
        )
        is True
    )
    assert reporter.calls == [
        (
            runtime_recreate_prompt_message("rt-1", "needs replacement"),
            False,
        )
    ]


@pytest.mark.parametrize("exc", [KeyboardInterrupt(), EOFError()])
def test_runtime_recreate_policy_prompt_cancellation_returns_false(exc):
    reporter = _Reporter(exc=exc)

    assert (
        should_recreate_runtime(
            "prompt",
            runtime_id="rt-1",
            reason="needs replacement",
            reporter=reporter,
            is_interactive=lambda: True,
        )
        is False
    )


def test_runtime_recreate_preserved_message_warns_existing_runtime_preserved():
    message = runtime_recreate_preserved_message("rt-1", "needs replacement")

    assert "Runtime rt-1 needs replacement" in message
    assert "existing Runtime was preserved" in message


def test_runtime_gateway_replacement_reason_is_user_friendly():
    reason = runtime_gateway_replacement_reason()

    assert "gateway settings" in reason
    assert "when a Runtime is created" in reason
    assert "gateway_mode" not in reason
    assert "gateway_instance_id" not in reason


def test_agentkit_client_deploy_normalizes_runtime_recreate_policy(monkeypatch):
    from agentkit.toolkit.sdk.client import AgentKitClient
    import agentkit.toolkit.sdk.client as client_mod

    calls = []

    def _fake_deploy(**kwargs):
        calls.append(kwargs)
        return "ok"

    monkeypatch.setattr(client_mod, "_deploy", _fake_deploy)

    client = AgentKitClient(config_dict={"common": {"agent_name": "demo"}})
    assert client.deploy(runtime_recreate_policy="yes") == "ok"

    assert calls[0]["runtime_recreate_policy"] == "always"


def test_agentkit_client_deploy_rejects_invalid_runtime_recreate_policy(monkeypatch):
    from agentkit.toolkit.sdk.client import AgentKitClient
    import agentkit.toolkit.sdk.client as client_mod

    def _fake_deploy(**kwargs):
        raise AssertionError("deploy should not be called")

    monkeypatch.setattr(client_mod, "_deploy", _fake_deploy)

    client = AgentKitClient(config_dict={"common": {"agent_name": "demo"}})
    with pytest.raises(ValueError, match="runtime_recreate_policy must be"):
        client.deploy(runtime_recreate_policy="maybe")
