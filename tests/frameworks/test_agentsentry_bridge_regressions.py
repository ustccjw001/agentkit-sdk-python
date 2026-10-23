import asyncio
from types import SimpleNamespace as NS
import pytest
from agentkit.frameworks import _agentsentry as guards


def test_text_ignores_reasoning():
    assert (
        guards._text(
            [
                {"type": "reasoning", "text": "SECRET"},
                {"type": "text", "text": "visible"},
            ]
        )
        == "visible"
    )


@pytest.mark.asyncio
async def test_guard_does_not_leak_across_yield_or_cross_task_close(monkeypatch):
    guard = NS(blocked=None)
    monkeypatch.setattr(guards, "_make_guard", lambda *_: guard)
    closed = []

    async def stream(self, ctx):
        try:
            assert guards._active_guard.get() is guard
            yield "event"
        finally:
            closed.append(True)

    ctx = NS(plugin_manager=NS(plugins=[NS(_sentry_v3=True)]))
    stream = guards.protect_migrated_tools(stream)(NS(name="agent"), ctx)
    assert await anext(stream) == "event"
    assert guards._active_guard.get() is None
    await asyncio.create_task(stream.aclose())
    assert closed == [True]


@pytest.mark.asyncio
async def test_checkpoint_restores_only_pending_calls(monkeypatch):
    pytest.importorskip("langchain_core")
    from langchain_core.messages import AIMessage, ToolMessage

    seen = []
    guard = guards._make_guard(
        NS(_sentry_v3=NS(moderate=lambda *a, **kw: seen.append((a, kw)))),
        NS(session=NS(id="s"), invocation_id="r"),
    )
    calls = [
        {"name": "record", "args": {"n": n}, "id": str(n), "type": "tool_call"}
        for n in (1, 2)
    ]

    async def state(config):
        return NS(
            values={
                "messages": [
                    AIMessage(content="visible plan", tool_calls=calls),
                    ToolMessage(content="done", tool_call_id="1"),
                ]
            }
        )

    token = guards._active_guard.set(guard)
    try:
        await guards.restore_pending_tools(NS(aget_state=state), {})
    finally:
        guards._active_guard.reset(token)
    guard.on_tool_start({"name": "record"}, '{"n":2}')
    assert seen[0][1]["tool_calls"][0]["ID"] == "2"
    with pytest.raises(guards.AgentSentryBlocked):
        guard.on_tool_start({"name": "record"}, '{"n":1}')


@pytest.mark.asyncio
async def test_real_graph_approval_resume_executes_reviewed_tool(monkeypatch):
    pytest.importorskip("langgraph")
    from langgraph.graph import StateGraph, MessagesState, START, END
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import interrupt
    from langgraph.prebuilt import ToolNode
    from langchain_core.messages import AIMessage
    from langchain_core.tools import tool
    from google.adk.apps import App
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from agentkit.frameworks import LangGraphAgentkitBridge
    from agentkit.plugins import LLMShieldPlugin

    for key, value in {
        "URL": "http://sentry/OpenTOP/V3/Lumen/Moderate",
        "ACCOUNT_ID": "account",
        "INSTANCE_ID": "instance",
        "AK": "ak",
        "SK": "sk",
    }.items():
        monkeypatch.setenv("AGENTSENTRY_" + key, value)
    executed = []

    @tool
    def record(action: str) -> str:
        """Record an approved action."""
        executed.append(action)
        return "done"

    def plan(state):
        return {
            "messages": [
                AIMessage(
                    content="Record the approved note",
                    tool_calls=[
                        {
                            "name": "record",
                            "args": {"action": "note"},
                            "id": "call1",
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        }

    def approve(state):
        interrupt("approve?")
        return {}

    graph = StateGraph(MessagesState)
    graph.add_node("plan", plan)
    graph.add_node("approve", approve)
    graph.add_node("tools", ToolNode([record]))
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "approve")
    graph.add_edge("approve", "tools")
    graph.add_edge("tools", END)
    compiled = graph.compile(checkpointer=InMemorySaver())
    bridge = LangGraphAgentkitBridge(compiled, name="test")
    plugin = LLMShieldPlugin.from_env()
    seen = []
    plugin._sentry_v3.moderate = lambda text, **kw: seen.append((text, kw))
    sessions = InMemorySessionService()
    await sessions.create_session(app_name="test", user_id="u", session_id="s")
    runner = Runner(
        app=App(name="test", root_agent=bridge, plugins=[plugin]),
        session_service=sessions,
    )

    async def run(text):
        return [
            e
            async for e in runner.run_async(
                user_id="u",
                session_id="s",
                new_message=types.Content(role="user", parts=[types.Part(text=text)]),
            )
        ]

    first = await run("record a note")
    assert any(e.error_code == "LANGGRAPH_INTERRUPT" for e in first)
    assert executed == []
    await run("approved")
    assert executed == ["note"]
    assert any(
        text == "Record the approved note" and kw["hook_name"] == "before_tool_call"
        for text, kw in seen
    )


@pytest.mark.asyncio
async def test_cancellation_closes_stream_without_guard_leak(monkeypatch):
    guard = NS(blocked=None)
    monkeypatch.setattr(guards, "_make_guard", lambda *_: guard)
    entered = asyncio.Event()
    closed = asyncio.Event()

    async def stream(self, ctx):
        try:
            entered.set()
            await asyncio.Event().wait()
            yield None
        finally:
            closed.set()

    ctx = NS(plugin_manager=NS(plugins=[NS(_sentry_v3=True)]))
    gen = guards.protect_migrated_tools(stream)(NS(name="agent"), ctx)
    task = asyncio.create_task(anext(gen))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()
    assert guards._active_guard.get() is None
