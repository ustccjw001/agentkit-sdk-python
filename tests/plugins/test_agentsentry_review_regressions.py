from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest
from google.genai import types
from agentkit.plugins.llm_shield import LLMShieldPlugin


@pytest.fixture
def plugin(monkeypatch):
    for key, value in {
        "URL": "http://sentry/OpenTOP/V3/Lumen/Moderate",
        "ACCOUNT_ID": "account",
        "INSTANCE_ID": "instance",
        "AK": "ak",
        "SK": "sk",
    }.items():
        monkeypatch.setenv("AGENTSENTRY_" + key, value)
    p = LLMShieldPlugin.from_env()
    p._sentry_v3.moderate = Mock(return_value=None)
    return p


@pytest.mark.asyncio
async def test_text_entry_defaults_and_final_reply_scope(plugin):
    await plugin.moderate_text("input", role="user")
    assert plugin._sentry_v3.moderate.call_args.kwargs["hook_name"] == "before_dispatch"
    await plugin.moderate_text("final", role="assistant")
    assert plugin._sentry_v3.moderate.call_count == 1


@pytest.mark.asyncio
async def test_native_adk_tool_uses_visible_plan(plugin):
    context = NS(agent_states={}, session=NS(id="s"), invocation_id="r")
    callback = NS(_invocation_context=context)
    response = NS(
        partial=False,
        content=types.Content(
            role="model",
            parts=[
                types.Part(text="SECRET", thought=True),
                types.Part(text="visible"),
                types.Part(
                    function_call=types.FunctionCall(name="record", args={"n": 1})
                ),
            ],
        ),
    )
    await plugin.after_model_callback(callback_context=callback, llm_response=response)
    result = await plugin.before_tool_callback(
        tool=NS(name="record"), tool_args={"n": 1}, tool_context=callback
    )
    assert result is None
    assert plugin._sentry_v3.moderate.call_args.args[0] == "visible"
    result = await plugin.before_tool_callback(
        tool=NS(name="record"), tool_args={"n": 1}, tool_context=callback
    )
    assert result["reason"] == "missing_visible_execution_plan"


def test_disable_private_independently(plugin, monkeypatch):
    monkeypatch.setenv("AGENTSENTRY_ENABLED", "false")
    monkeypatch.delenv("AGENTSENTRY_SK")
    assert LLMShieldPlugin.from_env() is None


@pytest.mark.asyncio
async def test_nontext_input_has_distinct_diagnostic(plugin):
    from agentkit.plugins.agentsentry_v3 import AgentSentryV3, UNSUPPORTED_INPUT

    plugin._sentry_v3.moderate = AgentSentryV3.moderate.__get__(plugin._sentry_v3)
    ctx = NS(
        agent_states={},
        session=NS(id="s"),
        invocation_id="r",
        user_content=types.Content(
            role="user",
            parts=[
                types.Part(inline_data=types.Blob(data=b"image", mime_type="image/png"))
            ],
        ),
    )
    response = await plugin.before_run_callback(invocation_context=ctx)
    assert response.parts[0].text == UNSUPPORTED_INPUT


@pytest.mark.asyncio
async def test_next_model_request_discards_old_native_plans(plugin):
    ctx = NS(agent_states={})
    response = NS(
        partial=False,
        content=types.Content(
            role="model",
            parts=[
                types.Part(text="old plan"),
                types.Part(function_call=types.FunctionCall(name="record", args={})),
            ],
        ),
    )
    await plugin.after_model_callback(callback_context=ctx, llm_response=response)
    await plugin.before_model_callback(callback_context=ctx, llm_request=NS())
    result = await plugin.before_tool_callback(
        tool=NS(name="record"), tool_args={}, tool_context=ctx
    )
    assert result["reason"] == "missing_visible_execution_plan"
    plugin._sentry_v3.moderate.assert_not_called()


def test_v3_rejects_legacy_environment_entry(plugin, monkeypatch):
    monkeypatch.delenv("AGENTSENTRY_URL")
    monkeypatch.setenv("TOOL_LLM_SHIELD_URL", "http://sentry/OpenTOP/V3/Lumen/Moderate")
    with pytest.raises(ValueError, match="AGENTSENTRY_URL"):
        LLMShieldPlugin.from_env()


def test_public_text_extraction_is_unchanged():
    from agentkit.plugins.llm_shield import _content_text

    content = types.Content(parts=[types.Part(text="existing text", thought=True)])
    assert _content_text(content) == "existing text"
    assert _content_text(content, visible_only=True) == ""
