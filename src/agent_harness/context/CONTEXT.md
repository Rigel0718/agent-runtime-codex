# Context

## Purpose

Context는 하나의 Agent 실행 동안 Agent와 Tool이 참조할 수 있는
Harness-owned contextual data를 제공한다.

Context는 OpenAI Agents SDK의 context 전달 메커니즘을 사용하며,
별도의 Agent execution mechanism을 구현하지 않는다.

## Responsibilities

Context는 다음을 담당한다.

* 현재 Agent 실행에 필요한 contextual data를 표현한다.
* `AgentRuntime`을 통해 SDK execution에 전달된다.
* 동일한 실행 안에서 Agent와 Tool이 context를 참조할 수 있도록 한다.

MVP에서는 하나의 `AgentRun` 범위에서 사용하는 context만 다룬다.

## AgentContext

`AgentContext`는 Harness에서 사용하는 최소 context model이다.

현재 필요한 실행 식별 정보만 포함한다.

```text
AgentContext

- run_id
- user_id
```

필드가 실제 요구사항 없이 미리 확장되어서는 안 된다.

## Runtime Integration

`AgentRuntime`은 전달받은 `AgentContext`를 해석하거나 수정하지 않는다.

Runtime의 책임은 Context를 OpenAI Agents SDK execution에 전달하는 것뿐이다.

```text
AgentContext
    ↓
AgentRuntime
    ↓
OpenAI Agents SDK
    ↓
Agent / Tools
```

Context가 없는 기존 Agent 실행도 계속 가능해야 한다.

## Boundaries

Context must not:

* execute or orchestrate Agents
* perform lifecycle transitions
* mutate `AgentRun`
* load or save persistence data
* execute or route tools
* approve or reject HITL interruptions
* manage conversation history
* implement long-term memory
* build or modify prompts
* introduce context provider, resolver, store, or manager abstractions without a current requirement

Persistence와 Context의 책임은 분리한다.

```text
Persistence
→ 데이터를 저장하고 복원한다.

Context
→ 현재 실행에서 사용할 contextual data를 전달한다.
```

Context가 persistence를 직접 호출하지 않는다.

## Current Scope

Context v0의 완료 범위는 다음과 같다.

* 최소 `AgentContext` model 정의
* `AgentRuntime`에서 optional Context 수용
* SDK execution으로 동일 Context 전달
* Tool에서 Context 접근 가능
* Context가 없는 기존 실행 유지

Conversation memory, session management, user profile loading,
cross-run memory, retrieval, context persistence는 현재 scope 밖이다.

필요성이 실제로 생길 때 별도의 responsibility와 boundary를 결정한 뒤 확장한다.
