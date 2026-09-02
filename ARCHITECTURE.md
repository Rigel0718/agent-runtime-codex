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
    ├── Persistence
    ├── Context
    └── Tracing

OpenAI Agents SDK
    ↓
Tool Gateway
    ├── Tools
    └── Tracing

AgentRun
    ↕
Persistence
    ↕
Database

HITL
    ↕
SDK RunState
    ↕
Persistence

Context
    ↓
AgentRuntime
    ↓
OpenAI Agents SDK
    ↓
Agent / Tools
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
* detecting SDK approval interruptions and resuming persisted SDK `RunState`

It must not:

* directly mutate `AgentRun` status
* reimplement the OpenAI Agents SDK execution loop
* implement database or SQLAlchemy details
* decide persistence mapping rules
* take ownership of `AgentRun` creation for persistence integration
* implement database-backed tracing storage, metrics, or evaluation

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
* implement persistence, HITL, context management, or evaluation

## Persistence

Persistence provides durable storage and restoration of `AgentRun`.

The domain `AgentRun` remains independent from SQLAlchemy and database concerns.

Persistence is responsible for:

* storing the current `AgentRun`
* restoring an `AgentRun` by `run_id`
* mapping between the domain model and persistence model
* performing database access through SQLAlchemy
* storing and restoring SDK `RunState` separately from `AgentRun`, keyed by `run_id`

Persistence must not:

* decide or perform lifecycle transitions
* mutate `AgentRun` status according to business rules
* orchestrate Agent execution
* decide when runtime lifecycle transitions occur
* execute tools
* apply approval decisions or orchestrate HITL execution
* introduce generic persistence abstractions without a current requirement

Detailed Persistence design is defined in `PERSISTENCE.md`.

## Context

Context provides Harness-owned contextual data for one Agent execution.

`AgentContext` contains the current `run_id` and `user_id`. `AgentRuntime` passes an
optional context unchanged to the OpenAI Agents SDK so Agents and Tools can access it.

Context does not own persistence, lifecycle transitions, execution orchestration,
conversation history, or long-term memory.

## Tracing

Tracing observes meaningful execution events at Harness-owned boundaries.

`AgentRuntime` records run start, completion, and failure events. `ToolGateway` records
tool start, completion, and failure events. A minimal in-memory recorder stores events,
and every event is connected to its execution by `run_id`.

Tracing does not own lifecycle transitions, execution correctness, durable storage,
OpenTelemetry integration, metrics, or evaluation.

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

Context
→ carries run-scoped contextual data to SDK Agents and Tools

Tracing
→ records run and tool execution events at Harness boundaries

OpenAI Agents SDK
→ executes Agent-level behavior

HITL
→ applies approve/reject decisions to pending SDK interruptions

SDK RunState
→ stores the SDK execution state required to resume an interrupted run
```

## Current Scope

Implemented through Tracing v0.

The runtime persists runtime-owned lifecycle transitions and SDK `RunState` at approval
interruptions, then restores it to resume after an approve or reject decision.

The runtime optionally passes `AgentContext` to SDK execution without interpreting or
persisting it. Runtime and tool execution events are recorded in memory and correlated
through the same `run_id`.

Retry policy, Unit of Work, transaction orchestration, and later infrastructure are outside the current scope.

## Evolution

Update this document when a new architectural responsibility is actually implemented or explicitly decided.
