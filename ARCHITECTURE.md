# ARCHITECTURE.md

## Goal

Build a production-oriented Agent Harness around the OpenAI Agents SDK.

The project is developed incrementally as an MVP.

Do not design future components before they are required.

## Current Architecture

Current scope:

AgentRun
    ↑
State Machine
    ↑
AgentLifecycle

`AgentRuntime` will be introduced after the lifecycle layer is complete.

## AgentRun

`AgentRun` represents one harness execution.

It stores run state and does not orchestrate execution.

## State Machine

The state machine owns valid `AgentRun` status transitions.

All status changes must go through the state machine.

Terminal states:

- COMPLETED
- FAILED
- CANCELLED

Terminal states cannot transition further.

## AgentLifecycle

`AgentLifecycle` exposes semantic lifecycle operations such as:

- start
- complete
- fail
- cancel
- request approval
- resume

It delegates all status transitions to the state machine.

It must not execute:

- OpenAI SDK Agents
- tools
- persistence
- tracing
- context management

## Layer Responsibilities

AgentRun
→ stores run state

State Machine
→ owns transition rules

AgentLifecycle
→ exposes semantic lifecycle operations

Future AgentRuntime
→ orchestrates actual execution

## Current Scope

Implement through `AgentLifecycle`.

Do not implement `AgentRuntime` or later infrastructure unless explicitly requested.

## Evolution

Update this document when a new architectural responsibility is actually implemented or explicitly decided.