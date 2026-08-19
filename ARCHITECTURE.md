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
    │
    └── Persistence

OpenAI Agents SDK
    ↓
Tool Gateway
    ↓
Tools

AgentRun
    ↕
Persistence
    ↕
Database
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

It connects OpenAI Agents SDK execution with the harness lifecycle and Persistence.

It is responsible for:

* starting the lifecycle before execution
* executing the SDK Agent
* completing or failing the lifecycle according to the execution result
* persisting `AgentRun` after runtime-owned lifecycle transitions

It must not:

* directly mutate `AgentRun` status
* reimplement the OpenAI Agents SDK execution loop
* implement database or SQLAlchemy details
* decide persistence mapping rules
* take ownership of `AgentRun` creation for persistence integration
* implement future infrastructure such as HITL, context, tracing, or evaluation

Runtime orchestrates persistence timing, while Lifecycle owns transitions and Persistence owns storage.

## Tool Gateway

`ToolGateway` provides the harness-controlled execution boundary for tools used by SDK Agents.

It owns a minimal in-memory registry of SDK `FunctionTool` instances, resolves tools by name,
and delegates execution to the registered tool.

For SDK integration, it creates an SDK-compatible `FunctionTool` adapter that preserves the
registered tool's definition while routing `on_invoke_tool` through the gateway. The SDK
`Runner` continues to own the Agent and tool-calling execution loops.

It must not:

* orchestrate SDK Agent execution
* mutate `AgentRun` lifecycle state
* implement individual tool business logic
* reimplement the OpenAI Agents SDK tool-calling loop
* implement persistence, HITL, tracing, context, or evaluation

## Persistence

Persistence provides durable storage and restoration of `AgentRun`.

The domain `AgentRun` remains independent from SQLAlchemy and database concerns.

Persistence is responsible for:

* storing the current `AgentRun`
* restoring an `AgentRun` by `run_id`
* mapping between the domain model and persistence model
* performing database access through SQLAlchemy

Persistence must not:

* decide or perform lifecycle transitions
* mutate `AgentRun` status according to business rules
* orchestrate Agent execution
* decide when runtime lifecycle transitions occur
* execute tools
* implement HITL, context, tracing, or evaluation
* introduce generic persistence abstractions without a current requirement

Detailed Persistence design is defined in `PERSISTENCE.md`.

## Layer Responsibilities

```text
AgentRun
→ stores run state and request data

State Machine
→ owns transition rules

AgentLifecycle
→ exposes semantic lifecycle operations

AgentRuntime
→ orchestrates execution and persistence timing for runtime-owned transitions

Tool Gateway
→ controls the boundary between SDK tool calls and tool execution

Persistence
→ stores and restores AgentRun without owning domain rules

OpenAI Agents SDK
→ executes Agent-level behavior
```

## Current Scope

Implemented through Runtime-Persistence integration.

The runtime persists runtime-owned `RUNNING`, `COMPLETED`, and `FAILED` states.

Retry policy, Unit of Work, transaction orchestration, and later infrastructure are outside the current scope.

## Evolution

Update this document when a new architectural responsibility is actually implemented or explicitly decided.
