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

from __future__ import annotations

from typing import ClassVar

from agentkit.client import BaseAgentkitClient

from .types import (
    CreateGatewayPluginBindingRequest,
    CreateGatewayPluginBindingResponse,
    CreateGatewayPluginRequest,
    CreateGatewayPluginResponse,
)


class AgentkitGatewayClient(BaseAgentkitClient):
    """Manage plugins on dedicated AgentKit gateways and bind them to MCP services."""

    API_ACTIONS: ClassVar[dict[str, str]] = {
        "CreateGatewayPlugin": "CreateGatewayPlugin",
        "CreateGatewayPluginBinding": "CreateGatewayPluginBinding",
    }

    def __init__(
        self,
        access_key: str = "",
        secret_key: str = "",
        region: str = "",
        session_token: str = "",
    ) -> None:
        super().__init__(
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            session_token=session_token,
            service_name="gateway",
        )

    def create_gateway_plugin(
        self, request: CreateGatewayPluginRequest
    ) -> CreateGatewayPluginResponse:
        """Install a plugin; create a binding separately to apply it to requests."""
        return self._invoke_api(
            api_action="CreateGatewayPlugin",
            request=request,
            response_type=CreateGatewayPluginResponse,
        )

    def create_gateway_plugin_binding(
        self, request: CreateGatewayPluginBindingRequest
    ) -> CreateGatewayPluginBindingResponse:
        """Bind an installed gateway plugin to a target MCP service."""
        return self._invoke_api(
            api_action="CreateGatewayPluginBinding",
            request=request,
            response_type=CreateGatewayPluginBindingResponse,
        )
