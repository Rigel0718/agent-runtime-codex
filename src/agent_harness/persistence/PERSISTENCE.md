# Persistence

## Purpose

Persistence는 `AgentRun`을 durable storage에 저장하고 다시 복원하는 계층이다.

현재 MVP에서는 `AgentRun`만 persistence 대상으로 한다.

Persistence는 domain state를 저장할 뿐, lifecycle transition이나 Agent execution을 결정하지 않는다.

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

* lifecycle transition 또는 `AgentRun.status` 결정
* Agent execution orchestration
* runtime lifecycle transition의 발생 시점 결정
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

```python
class AgentRunRepository:
    async def save(self, run: AgentRun) -> None:
        ...

    async def get(self, run_id: UUID) -> AgentRun | None:
        ...
```

`save()`는 새 `AgentRun`을 저장하고 동일한 `run_id`가 존재하면 현재 state로 갱신한다.

`get()`은 저장된 record를 domain `AgentRun`으로 복원하며, 존재하지 않으면 `None`을 반환한다.

현재 규모에서는 mapping을 repository 내부 private function으로 두며 별도의 Mapper abstraction은 만들지 않는다.

## Current Status

초기 Persistence 구현과 Runtime-Persistence integration은 완료되었다.

구현 완료 범위:

* SQLAlchemy database/session setup
* `AgentRunModel`
* `AgentRun` ↔ `AgentRunModel` mapping
* `AgentRunRepository.save()` / `get()`
* 관련 repository tests
* Runtime의 `RUNNING`, `COMPLETED`, `FAILED` transition 직후 저장
* success, SDK failure, initial persistence failure integration tests

## Runtime-Persistence Integration

`AgentRuntime`은 Persistence 자체를 확장하지 않고 기존 repository와 연결된다.

```text
AgentRuntime
    ↓
AgentLifecycle transition
    ↓
AgentRun
    ↓
AgentRunRepository.save()
```

현재 integration 대상:

```text
start()    → RUNNING   → save
complete() → COMPLETED → save
fail()     → FAILED    → save
```

책임은 다음과 같이 유지한다.

* `AgentLifecycle`은 state transition을 결정한다.
* Persistence는 변경된 `AgentRun`을 저장한다.
* `AgentRuntime`은 execution 흐름에서 transition과 save의 시점을 orchestration한다.

Runtime-Persistence integration만을 위해 Runtime이 `AgentRun` 생성 책임을 새로 소유하지 않는다.

`CREATED` 상태의 최초 저장 시점과 상위 application orchestration은 현재 단계에서 결정하지 않는다.

## Integration Result

구현 범위:

* `AgentRuntime`과 `AgentRunRepository` 연결
* `RUNNING`, `COMPLETED`, `FAILED` transition 후 저장
* 기존 SDK `RunResult` 반환과 execution exception re-raise 유지
* success / failure orchestration tests
* persistence exception을 숨기지 않고 caller에게 전달

현재 범위 밖:

* Generic Repository / Unit of Work
* retry policy / transaction orchestration
* Event Sourcing / Audit Log / Cache
* HITL / Context / Trace / Eval persistence

Persistence 실패에 대한 recovery infrastructure는 필요가 생길 때 별도 설계한다.
