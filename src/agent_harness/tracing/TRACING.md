# Tracing

## Purpose

Tracing은 하나의 `AgentRun` 동안 Harness boundary에서 발생하는
의미 있는 execution event를 구조화하여 기록한다.

Tracing은 Agent execution을 관찰하며,
OpenAI Agents SDK의 execution mechanism을 제어하거나 재구현하지 않는다.

## Responsibilities

Tracing은 다음을 담당한다.

* 하나의 실행에서 발생한 trace event를 표현한다.
* event를 `run_id`를 기준으로 동일한 실행과 연결한다.
* `AgentRuntime`에서 발생하는 주요 execution event를 기록한다.
* `ToolGateway`를 통과하는 tool execution event를 기록한다.

## Trace Event

Trace event는 실행 중 발생한 하나의 의미 있는 사건을 나타낸다.

MVP에서는 현재 필요한 최소 정보만 포함한다.

```text
TraceEvent

- run_id
- event_type
- timestamp
```

필드는 실제 tracing 요구사항 없이 미리 확장하지 않는다.

## Runtime Tracing

`AgentRuntime`은 runtime-owned execution event가 발생하는 시점을 결정한다.

현재 기록 대상은 다음과 같다.

```text
RUN_STARTED
RUN_COMPLETED
RUN_FAILED
```

Tracing은 해당 event를 기록할 뿐 lifecycle transition을 수행하거나
`AgentRun`의 상태를 변경하지 않는다.

## Tool Tracing

`ToolGateway`는 gateway를 통과하는 tool execution event가 발생하는 시점을 결정한다.

현재 기록 대상은 다음과 같다.

```text
TOOL_STARTED
TOOL_COMPLETED
TOOL_FAILED
```

개별 Tool은 Harness tracing을 직접 관리하지 않는다.

## Boundaries

Tracing은 execution의 observer이며 execution correctness를 소유하지 않는다.

## Current Scope

Tracing v0의 완료 범위는 다음과 같다.

* 최소 `TraceEvent` model 정의
* trace event를 기록하는 최소 recorder 구현
* `AgentRuntime`의 run execution event 기록
* `ToolGateway`의 tool execution event 기록
* 동일한 `run_id`를 통한 event 연결
* tracing integration에 대한 테스트

Durable trace storage, trace query API, distributed tracing,
OpenTelemetry integration, metrics, dashboard, cost tracking,
HITL tracing, Evaluation은 현재 scope 밖이다.

필요성이 실제로 생길 때 별도의 responsibility와 boundary를 결정한 뒤 확장한다.
