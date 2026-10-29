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

import json

import pytest
from pydantic import ValidationError

from agentkit.platform.context import default_cloud_provider
from agentkit.sdk.gateway import (
    AgentkitGatewayClient,
    CreateGatewayPluginBindingRequest,
    CreateGatewayPluginBindingResponse,
    CreateGatewayPluginRequest,
    CreateGatewayPluginResponse,
)
from agentkit.toolkit.errors import ApiError


@pytest.fixture
def client():
    with default_cloud_provider("volcengine"):
        return AgentkitGatewayClient(
            access_key="AK_LOCAL_TEST_ONLY",
            secret_key="SK_LOCAL_TEST_ONLY",
            region="cn-beijing",
            session_token="TOKEN_LOCAL_TEST_ONLY",
        )


def test_create_plugin_sends_agentkit_request_and_parses_id(client, monkeypatch):
    def fake_json(api, params, body):
        assert api == "CreateGatewayPlugin"
        assert params == {}
        assert json.loads(body) == {
            "GatewayInstanceId": "g-test",
            "GatewayPluginName": "IdentityAuthorization",
            "GatewayPluginConfig": "{}",
        }
        return json.dumps({"Result": {"GatewayPluginId": "gpl-test"}})

    monkeypatch.setattr(client, "json", fake_json)
    assert client.service == "agentkit"
    assert client.session_token == "TOKEN_LOCAL_TEST_ONLY"
    for action, info in client.api_info.items():
        assert info.method == "POST"
        assert info.path == "/"
        assert info.query == {"Action": action, "Version": "2025-10-30"}

    response = client.create_gateway_plugin(
        CreateGatewayPluginRequest(
            gateway_instance_id="g-test",
            gateway_plugin_name="IdentityAuthorization",
            gateway_plugin_config="{}",
        )
    )
    assert isinstance(response, CreateGatewayPluginResponse)
    assert response.gateway_plugin_id == "gpl-test"


@pytest.mark.parametrize("enable", [None, False, True])
def test_create_binding_preserves_config_and_optional_values(
    client, monkeypatch, enable
):
    config = json.dumps(
        {
            "Namespace": "default",
            "TokenPosition": {"Header": "x-ve-tip-token", "Prefix": ""},
        }
    )
    expected = {
        "GatewayPluginId": "gpl-test",
        "TargetId": "m-test",
        "GatewayPluginBindingConfig": config,
    }
    if enable is not None:
        expected.update(Enable=enable, Comments="")

    def fake_json(api, params, body):
        assert api == "CreateGatewayPluginBinding"
        assert params == {}
        assert json.loads(body) == expected
        return json.dumps({"Result": {"GatewayPluginBindingId": "gpb-test"}})

    monkeypatch.setattr(client, "json", fake_json)
    response = client.create_gateway_plugin_binding(
        CreateGatewayPluginBindingRequest(
            GatewayPluginId="gpl-test",
            TargetId="m-test",
            GatewayPluginBindingConfig=config,
            Enable=enable,
            Comments="" if enable is not None else None,
        )
    )
    assert isinstance(response, CreateGatewayPluginBindingResponse)
    assert response.gateway_plugin_binding_id == "gpb-test"


@pytest.mark.parametrize(
    "model,values,config_field",
    [
        (
            CreateGatewayPluginRequest,
            {
                "gateway_instance_id": "g-test",
                "gateway_plugin_name": "IdentityAuthorization",
            },
            "gateway_plugin_config",
        ),
        (
            CreateGatewayPluginBindingRequest,
            {"gateway_plugin_id": "gpl-test", "target_id": "m-test"},
            "gateway_plugin_binding_config",
        ),
    ],
)
def test_config_is_required_and_must_be_a_string(model, values, config_field):
    with pytest.raises(ValidationError):
        model(**values)
    with pytest.raises(ValidationError):
        model(**values, **{config_field: {"Namespace": "default"}})


def test_duplicate_binding_error_is_preserved(client, monkeypatch):
    calls = []

    def fake_json(api, params, body):
        calls.append(api)
        return json.dumps(
            {
                "ResponseMetadata": {
                    "Error": {
                        "Code": "DuplicatedResource",
                        "Message": "The specified resource already exists.",
                    }
                }
            }
        )

    monkeypatch.setattr(client, "json", fake_json)
    with pytest.raises(ApiError) as error:
        client.create_gateway_plugin_binding(
            CreateGatewayPluginBindingRequest(
                gateway_plugin_id="gpl-test",
                target_id="m-test",
                gateway_plugin_binding_config="{}",
            )
        )
    assert error.value.error_code == "DuplicatedResource"
    assert calls == ["CreateGatewayPluginBinding"]
