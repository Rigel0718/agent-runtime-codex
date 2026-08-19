# Persistence

## Purpose

Persistence는 `AgentRun`을 durable storage에 저장하고 다시 복원하는 계층이다.

현재 MVP에서는 `AgentRun`만 persistence 대상으로 한다.

Persistence는 domain state를 저장할 뿐,
lifecycle transition이나 Agent execution을 결정하지 않는다.

```text
AgentRun
    ↕
AgentRunRepository
    ↕
AgentRunModel
    ↕
Database
```

## Responsibilities

Persistence는 다음을 담당한다.

* `AgentRun` 저장
* `run_id`를 통한 `AgentRun` 조회
* domain `AgentRun`과 SQLAlchemy persistence model 간 mapping
* SQLAlchemy를 통한 database access

Persistence는 다음을 담당하지 않는다.

* lifecycle transition
* `AgentRun.status` 결정
* Agent execution orchestration
* Tool execution
* HITL, Context, Tracing, Evaluation

상태 변화는 기존과 동일하게 다음 흐름을 따른다.

```text
AgentLifecycle
    ↓
State Machine
    ↓
AgentRun
```

Persistence는 상태 변화가 완료된 `AgentRun`을 저장한다.

## Structure

권장 최소 구조:

```text
persistence/
├── database.py
├── models.py
└── repository.py
```

### database.py

SQLAlchemy engine 및 session 생성에 필요한 최소 infrastructure를 담당한다.

### models.py

`AgentRun`의 database representation인 `AgentRunModel`을 정의한다.

Domain `AgentRun`은 SQLAlchemy에 의존하지 않는다.

### repository.py

`AgentRun`의 persistence operation을 제공한다.

초기 public API:

```python
class AgentRunRepository:
    async def save(self, run: AgentRun) -> None:
        ...

    async def get(self, run_id: UUID) -> AgentRun | None:
        ...
```

`save()`는 새 `AgentRun`을 저장하고,
동일한 `run_id`가 존재하면 현재 state로 갱신한다.

`get()`은 저장된 record를 domain `AgentRun`으로 복원하며,
존재하지 않으면 `None`을 반환한다.

현재 규모에서는 mapping을 repository 내부 private function으로 둘 수 있다.

별도의 Mapper abstraction은 만들지 않는다.

## Initial Scope

현재 단계에서 구현한다.

* SQLAlchemy database/session setup
* `AgentRunModel`
* `AgentRun` ↔ `AgentRunModel` mapping
* `AgentRunRepository.save()`
* `AgentRunRepository.get()`
* 관련 tests

현재 단계에서는 구현하지 않는다.

* Runtime-Persistence integration
* Generic Repository
* Unit of Work
* Event Sourcing
* Audit Log
* Cache
* HITL / Context / Trace / Eval persistence

Runtime과 Persistence의 연결은 Persistence 자체가 구현되고 검증된 뒤 별도 단계에서 설계한다.

## Completion Criteria

다음 조건을 만족하면 초기 Persistence 구현을 완료한 것으로 본다.

* 새 `AgentRun`을 저장할 수 있다.
* 저장된 `AgentRun`을 `run_id`로 조회할 수 있다.
* 동일한 `run_id`의 `AgentRun`을 다시 저장하면 현재 state가 반영된다.
* 존재하지 않는 `run_id` 조회 시 `None`을 반환한다.
* 모든 현재 `AgentRun` field가 정상적으로 round-trip 된다.
* Domain `AgentRun`이 SQLAlchemy에 의존하지 않는다.
* 관련 tests가 통과한다.
