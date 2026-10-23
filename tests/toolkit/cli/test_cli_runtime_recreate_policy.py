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

from typer.testing import CliRunner

from agentkit.toolkit.cli.cli import app
from agentkit.toolkit.models import DeployResult, LifecycleResult


runner = CliRunner()


def test_deploy_recreate_runtime_yes_passes_policy(monkeypatch):
    calls = []

    class _DeployExecutor:
        def __init__(self, reporter=None):
            self.reporter = reporter

        def execute(self, **kwargs):
            calls.append(kwargs)
            return DeployResult(success=True)

    import agentkit.toolkit.executors as executors

    monkeypatch.setattr(executors, "DeployExecutor", _DeployExecutor)

    result = runner.invoke(app, ["deploy", "--recreate-runtime", "yes"])

    assert result.exit_code == 0
    assert calls[0]["runtime_recreate_policy"] == "always"


def test_deploy_recreate_runtime_invalid_exits_two():
    result = runner.invoke(app, ["deploy", "--recreate-runtime", "maybe"])

    assert result.exit_code == 2
    assert "--recreate-runtime must be yes or no" in result.output


def test_launch_recreate_runtime_no_passes_policy(monkeypatch):
    calls = []

    class _LifecycleExecutor:
        def __init__(self, reporter=None):
            self.reporter = reporter

        def launch(self, **kwargs):
            calls.append(kwargs)
            return LifecycleResult(success=True, operation="launch")

    import agentkit.toolkit.executors as executors

    monkeypatch.setattr(executors, "LifecycleExecutor", _LifecycleExecutor)

    result = runner.invoke(app, ["launch", "--recreate-runtime", "no"])

    assert result.exit_code == 0
    assert calls[0]["runtime_recreate_policy"] == "never"


def test_launch_recreate_runtime_invalid_exits_two():
    result = runner.invoke(app, ["launch", "--recreate-runtime", "maybe"])

    assert result.exit_code == 2
    assert "--recreate-runtime must be yes or no" in result.output


def test_harness_deploy_recreate_runtime_yes_passes_policy(monkeypatch):
    calls = []

    def _deploy_harness(**kwargs):
        calls.append(kwargs)
        return LifecycleResult(
            success=True,
            operation="launch",
            deploy_result=DeployResult(success=True, endpoint_url="https://example"),
        )

    import agentkit.toolkit.sdk as sdk

    monkeypatch.setattr(sdk, "deploy_harness", _deploy_harness)

    result = runner.invoke(
        app,
        ["deploy", "--harness", "demo", "--recreate-runtime", "yes"],
    )

    assert result.exit_code == 0
    assert calls[0]["runtime_recreate_policy"] == "always"


def test_harness_deploy_recreate_runtime_invalid_exits_two():
    result = runner.invoke(
        app,
        ["deploy", "--harness", "demo", "--recreate-runtime", "maybe"],
    )

    assert result.exit_code == 2
    assert "--recreate-runtime must be yes or no" in result.output
