# HITL

## Purpose

HITL(Human-in-the-Loop)은 Agent 실행 중 사람의 승인이 필요한 경우 실행을 중단하고,
approve 또는 reject 결정 이후 동일한 실행을 재개할 수 있도록 한다.

OpenAI Agents SDK의 interruption 및 `RunState` 기능을 활용하며,
SDK의 approval execution loop를 재구현하지 않는다.

## Execution Flow

```text
RUNNING
   ↓
SDK interruption
   ↓
WAITING_APPROVAL
   ↓
approve / reject
   ↓
RUNNING
   ↓
SDK execution resume
```

Tool call이 reject되더라도 Agent 실행 자체가 취소되는 것은 아니다.

approve와 reject 모두 pending approval에 대한 결정이며,
결정 적용 후 Agent 실행을 재개한다.

## Responsibilities

HITL은 다음을 담당한다.

* SDK가 반환한 pending approval을 다룬다.
* 외부에서 전달된 approve 또는 reject 결정을 SDK `RunState`에 적용한다.
* 중단된 SDK execution을 재개할 수 있는 상태를 유지한다.

HITL은 다음을 담당하지 않는다.

* `AgentRun` status를 직접 변경하지 않는다.
* lifecycle transition rule을 정의하지 않는다.
* SDK Agent execution을 직접 orchestrate하지 않는다.
* tool을 직접 실행하지 않는다.
* database 또는 SQLAlchemy 세부사항을 구현하지 않는다.
* approval UI, API, authorization policy를 구현하지 않는다.

## Layer Integration

### AgentLifecycle

상태 변경은 기존 lifecycle operation을 사용한다.

```text
request_approval()
RUNNING → WAITING_APPROVAL

resume()
WAITING_APPROVAL → RUNNING
```

HITL은 상태를 직접 변경하지 않는다.

### AgentRuntime

Runtime은 HITL execution flow를 orchestrate한다.

Runtime은:

* SDK interruption을 감지한다.
* interruption 발생 시 `request_approval()`을 호출한다.
* resume 시 `resume()`을 호출한다.
* SDK `RunState`를 사용하여 실행을 재개한다.
* lifecycle transition 이후 필요한 persistence timing을 결정한다.

### Persistence

Persistence는 HITL 재개에 필요한 durable state를 저장하고 복원한다.

`AgentRun`과 SDK execution state는 서로 다른 책임을 가진다.

```text
AgentRun
→ Harness lifecycle state

RunState
→ SDK execution resume state
```

SDK `RunState`를 `AgentRun` domain model에 포함하지 않는다.

두 상태는 `run_id`를 기준으로 연결한다.

## Current Scope

HITL v0의 목표는 다음 흐름을 지원하는 것이다.

```text
Agent 실행
→ approval interruption
→ WAITING_APPROVAL 저장
→ RunState 저장
→ approve / reject
→ RunState 복원
→ RUNNING
→ Agent 실행 재개
```

현재 scope에는 다음을 포함하지 않는다.

* approval timeout
* approval notification
* approver role 또는 permission
* multi-user approval
* generic policy engine
* generic checkpoint framework
* FastAPI approval endpoint 또는 UI
* tracing
* evaluation
* context management

현재 단계에서는 Agent가 approval을 기다리며 중단되고,
사람의 결정 이후 동일한 실행을 정상적으로 재개할 수 있는 최소 흐름만 구현한다.
