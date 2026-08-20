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

Persistence의 상세 설계와 구현 범위는 `PERSISTENCE.md`를 따른다.

HITL의 상세 설계와 구현 범위는 `src/agent_harness/hitl/HITL.md`를 따른다.

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
* `AgentRun`의 lifecycle status 변경은 state machine을 통해 수행한다.
* MVP를 단계적으로 구현하며, 아직 필요하지 않은 abstraction은 미리 만들지 않는다.
* step의 도메인 기준이 정해질 때까지 `AgentRun`은 현재 step을 추적하지 않는다.

## Current Stage

HITL v0 구현을 완료했다.

현재 구현 완료 범위:

```text
AgentRun
→ State Machine
→ AgentLifecycle
→ AgentRuntime
→ ToolGateway
→ Persistence
→ HITL
```

SDK approval interruption에서 `WAITING_APPROVAL`과 `RunState`를 저장하고,
approve/reject 결정 후 동일한 SDK 실행을 재개하는 흐름을 완료했다.

다음 단계는 Context이다.

## Progress

* [x] AgentRun
* [x] State Machine
* [x] AgentLifecycle
* [x] AgentRuntime
* [x] Tool Gateway
* [x] Persistence
* [x] Runtime-Persistence integration
* [x] HITL
* [ ] Context ← next
* [ ] Tracing
* [ ] Evaluation

## Development Approach

각 component를 다음 순서로 진행한다:

1. responsibility와 boundary 결정
2. 최소 구현
3. 테스트
4. 구현 결과 검토
5. 필요한 문서 업데이트
6. 다음 component 진행

현재 scope 밖의 component는 필요해질 때까지 구현하지 않는다.
