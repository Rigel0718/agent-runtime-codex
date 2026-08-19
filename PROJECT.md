# Agent Harness

## Goal

Production-oriented AI Agent Harness를 구현한다.

OpenAI Agents SDK를 기반으로 Agent 실행을 감싸는 Harness 계층을 직접 구현하면서,
Agent runtime, lifecycle, tool control, persistence, HITL, context, tracing, evaluation의 핵심 구조를 단계적으로 학습하고 구현하는 것을 목표로 한다.

현재는 MVP를 우선하며, 필요한 기능을 하나씩 구현하고 검증한 뒤 확장한다.

## Stack

* Python
* FastAPI
* PostgreSQL
* OpenAI Agents SDK
* Pydantic v2
* SQLAlchemy

## Architecture

현재 시스템 구조와 layer responsibility는 `ARCHITECTURE.md`를 따른다.

Repository-wide Codex 작업 규칙은 `AGENTS.md`를 따른다.

Persistence의 상세 설계와 현재 구현 범위는 `PERSISTENCE.md`를 따른다.

## Decisions

### 2026-08

* OpenAI Agents SDK의 `Agent`를 그대로 사용한다.
* 별도의 custom Agent class를 만들지 않는다.
* Harness의 runtime 및 execution control layer를 직접 구현한다.
* OpenAI SDK `Runner`의 내부 Agent execution을 재구현하지 않는다.
* `AgentRuntime`은 SDK execution과 Harness lifecycle을 연결하는 orchestration layer로 둔다.
* `ToolGateway`는 SDK tool call과 실제 tool execution 사이의 Harness-controlled boundary로 둔다.
* Pydantic을 domain model로 사용한다.
* Domain model과 persistence model을 분리한다.
* DB persistence는 SQLAlchemy를 통해 구현한다.
* Persistence는 `AgentRun`의 저장과 복원을 담당하며 lifecycle rule을 소유하지 않는다.
* Persistence가 `AgentRun.status`를 결정하거나 lifecycle transition을 수행하지 않는다.
* Persistence MVP에서는 `AgentRun`만 persistence 대상으로 한다.
* Persistence MVP에서는 generic repository, Unit of Work 등의 선행 abstraction을 만들지 않는다.
* MVP를 단계적으로 구현하며, 아직 필요하지 않은 abstraction은 미리 만들지 않는다.
* `AgentRun`의 lifecycle status 변경은 state machine을 통해 수행한다.
* `AgentRuntime`에서도 `AgentRun.status`를 직접 변경하지 않고 `AgentLifecycle`을 통해 상태를 변경한다.
* step의 도메인 기준이 정해질 때까지 `AgentRun`은 현재 step을 추적하지 않는다.

## Current Stage

Persistence 초기 구현 완료.

현재 구현 완료 범위:

```text
AgentRun
→ State Machine
→ AgentLifecycle
→ AgentRuntime
→ ToolGateway
→ Persistence
```

다음 구현 대상:

```text
AgentRuntime
    ↕
Persistence
```

`AgentRuntime`과 Persistence의 실제 orchestration integration은 Persistence 구현이 검증된 뒤
별도 작업으로 진행한다.

HITL, Context, Tracing, Evaluation은 현재 scope에 포함하지 않는다.

## Progress

* [x] AgentRun
* [x] State Machine
* [x] AgentLifecycle
* [x] AgentRuntime
* [x] Tool Gateway
* [x] Persistence
* [ ] Runtime-Persistence integration ← next
* [ ] HITL
* [ ] Context
* [ ] Tracing
* [ ] Evaluation

## Persistence Implementation Order

1. Persistence responsibility와 boundary 확정
2. SQLAlchemy persistence model 구현
3. database/session infrastructure 구현
4. `AgentRun` 저장 구현
5. `AgentRun` 복원 구현
6. domain ↔ persistence mapping 검증
7. repository tests
8. 구현 결과 검토
9. Runtime-Persistence integration 설계

Persistence 초기 단계에서 1~7까지 구현을 완료했다.

## Development Approach

각 component를 다음 순서로 진행한다:

1. responsibility와 boundary 결정
2. 최소 구현
3. 테스트
4. 구현 결과 검토
5. `ARCHITECTURE.md` 업데이트
6. `PROJECT.md` 진행 상태 업데이트
7. 다음 component 진행

현재 scope 밖의 component는 필요해질 때까지 구현하지 않는다.
