# Agent Harness Architecture

## Current Architecture

Current scope:

```text
AgentRun
    ↑
State Machine
    ↑
AgentLifecycle
    ↑
AgentRuntime

OpenAI Agents SDK
    ↓
Tool Gateway
    ↓
Tools
```

## AgentRun

`AgentRun` represents one harness execution.

It stores run state and request data and does not orchestrate execution.

## State Machine

The state machine owns valid `AgentRun` status transitions.

All status changes must go through the state machine.

Terminal states:

* COMPLETED
* FAILED
* CANCELLED

Terminal states cannot transition further.

## AgentLifecycle

`AgentLifecycle` exposes semantic lifecycle operations such as:

* start
* complete
* fail
* cancel
* request approval
* resume

It delegates all status transitions to the state machine.

It must not execute:

* OpenAI SDK Agents
* tools
* persistence
* tracing
* context management

## AgentRuntime

`AgentRuntime` orchestrates actual Agent execution.

It connects OpenAI Agents SDK execution with the harness lifecycle.

It is responsible for:

* starting the lifecycle before execution
* executing the SDK Agent
* completing or failing the lifecycle according to the execution result

It must not:

* directly mutate `AgentRun` status
* reimplement the OpenAI Agents SDK execution loop
* implement future infrastructure such as persistence, HITL, context, tracing, or evaluation

## Tool Gateway

`ToolGateway` provides the harness-controlled execution boundary for tools used by SDK Agents.

It is responsible for resolving registered tools and delegating tool execution.

It must not:

* orchestrate SDK Agent execution
* mutate `AgentRun` lifecycle state
* implement individual tool business logic
* reimplement the OpenAI Agents SDK tool-calling loop
* implement future infrastructure such as persistence, HITL, tracing, context, or evaluation

## Layer Responsibilities

AgentRun
→ stores run state and request data

State Machine
→ owns transition rules

AgentLifecycle
→ exposes semantic lifecycle operations

AgentRuntime
→ orchestrates actual execution

Tool Gateway
→ controls the boundary between SDK tool calls and tool execution

OpenAI Agents SDK
→ executes Agent-level behavior

## Current Scope

Implement through `ToolGateway`.

Do not implement later infrastructure unless explicitly requested.

## Evolution

Update this document when a new architectural responsibility is actually implemented or explicitly decided.
