# 专属网关插件

`AgentkitGatewayClient` 支持 AgentKit 的 `CreateGatewayPlugin` 和
`CreateGatewayPluginBinding` OpenAPI，版本为 `2025-10-30`。
客户端复用 SDK 现有的凭据、区域、服务地址和请求签名配置。

## 安装 Identity 鉴权插件并绑定 MCP 服务

调用前，需要准备专属 MCP 网关及该网关下处于运行中的 MCP 服务。
还需在 Identity 中创建权限空间，并为调用方身份配置访问规则。

```python
import json

from agentkit.sdk.gateway import (
    AgentkitGatewayClient,
    CreateGatewayPluginBindingRequest,
    CreateGatewayPluginRequest,
)

# Credentials are resolved through the SDK's existing credential chain.
client = AgentkitGatewayClient(region="cn-beijing")

plugin = client.create_gateway_plugin(
    CreateGatewayPluginRequest(
        gateway_instance_id="<gateway-instance-id>",
        gateway_plugin_name="IdentityAuthorization",
        gateway_plugin_config="{}",
    )
)
if not plugin.gateway_plugin_id:
    raise RuntimeError("CreateGatewayPlugin returned no GatewayPluginId")

binding = client.create_gateway_plugin_binding(
    CreateGatewayPluginBindingRequest(
        gateway_plugin_id=plugin.gateway_plugin_id,
        target_id="<mcp-service-id>",
        gateway_plugin_binding_config=json.dumps(
            {
                "Namespace": "default",
                "TokenPosition": {
                    "Header": "x-ve-tip-token",
                    "Prefix": "",
                },
            }
        ),
        enable=True,
        comments="Identity authorization for this MCP service",
    )
)
print(binding.gateway_plugin_binding_id)
```

安装插件后，需要启用绑定规则，鉴权才会对目标 MCP 服务生效。
`Namespace` 填写 Identity 权限空间名称，与 OAuth 用户池 ID 无关。
示例从 `X-Ve-TIP-Token` 请求头读取 TIP Token，鉴权失败时拒绝请求。
MCP 服务原有的入站认证仍然生效。

## 请求字段

两个配置字段都必填，类型为**字符串**。配置对象需要先用 `json.dumps` 序列化，
再传给 SDK。客户端原样发送配置字符串，具体配置内容由对应插件处理。

| 请求模型 | 必填字段 | 可选字段 | 响应字段 |
| --- | --- | --- | --- |
| `CreateGatewayPluginRequest` | `gateway_instance_id`、`gateway_plugin_name`、`gateway_plugin_config` | 无 | `gateway_plugin_id` |
| `CreateGatewayPluginBindingRequest` | `gateway_plugin_id`、`target_id`、`gateway_plugin_binding_config` | `enable`、`comments` | `gateway_plugin_binding_id` |

模型也接受 `GatewayInstanceId`、`TargetId` 等 OpenAPI 字段名。
未设置的可选字段不会发送；显式设置的 `enable=False` 会保留。

这两个接口执行创建操作。插件或绑定已存在时，服务可能返回 `DuplicatedResource`，
SDK 会抛出包含该错误码的 `ApiError`。为同一插件添加其他绑定时，复用已有插件 ID。
客户端不会自动查询、更新或删除资源。

控制台配置方式和权限策略前提见[专属网关插件指南](https://docs.volcengine.com/docs/agentkit/dedicated-gateway-plugin-configuration-description)。
