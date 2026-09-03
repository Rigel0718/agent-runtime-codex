# V0 E2E Validation

## Purpose

Agent Harness v0의 각 component가 실제 하나의 execution flow에서
기존 responsibility와 boundary를 유지하며 함께 동작하는지 검증한다.

이 검증은 새로운 architecture나 abstraction을 추가하기 위한 작업이 아니다.

검증 과정에서 문제가 발견되면 현재 v0 scope 안에서 필요한 최소 변경만 수행한다.

## Validation Rules

각 항목은 실제 검증이 완료되면 `[o]`로 표시한다.

```text
[ ] not validated
[o] validated
```

검증 중 예상과 다른 동작, 환경 의존성, failure condition, SDK behavior 등
추가로 기록할 필요가 있는 변수가 발견되면 해당 항목의 `Notes`에 기록한다.

예:

```text
Notes:
- Tool failure 발생 시 SDK가 exception을 wrapping함.
- SQLite에서는 통과하지만 PostgreSQL에서는 추가 검증 필요.
```

검증을 위해 미래 component나 불필요한 abstraction을 추가하지 않는다.

---

## 1. Normal Run E2E

Status: `[o]`

하나의 `AgentRun`이 정상적으로 시작되어 Agent와 Tool을 실행하고
최종적으로 `COMPLETED` 상태까지 도달하는지 검증한다.

Expected flow:

```text
AgentRun CREATED
    ↓
AgentRuntime
    ↓
RUNNING
    ↓
OpenAI Agents SDK
    ↓
ToolGateway
    ↓
Tool
    ↓
Agent Result
    ↓
COMPLETED
```

Verify:

* lifecycle이 `CREATED → RUNNING → COMPLETED`로 전환된다.
* SDK Agent execution이 `AgentRuntime`을 통해 실행된다.
* Tool 호출이 `ToolGateway`를 통과한다.
* 정상 실행 결과가 반환된다.

Notes:

```text
- `tests/test_e2e.py::test_normal_run_connects_context_tool_trace_and_persistence`에서 검증했다.
- 외부 모델/API 호출은 사용하지 않고 `Runner.run`을 결정론적으로 대체했으며,
  Runtime에서 SDK Agent와 SDK-compatible gateway tool로 이어지는 경계는 그대로 통과했다.
```

---

## 2. Context / Tool / Trace / Persistence

Status: `[o]`

Normal Run 안에서 Context, ToolGateway, Tracing, Persistence가
각자의 responsibility에 따라 함께 동작하는지 검증한다.

Verify:

### Context

* `AgentContext`가 Runtime을 통해 SDK execution에 전달된다.
* Agent와 Tool이 동일한 run-scoped context를 참조한다.
* Runtime이 Context의 내용을 해석하거나 관리하지 않는다.

### Tool

* SDK tool call이 `ToolGateway`를 통과한다.
* 개별 Tool이 Harness execution orchestration을 소유하지 않는다.

### Tracing

다음 event가 동일한 `run_id`로 연결되는지 확인한다.

```text
RUN_STARTED
TOOL_STARTED
TOOL_COMPLETED
RUN_COMPLETED
```

Tracing은 lifecycle 또는 execution 결과를 변경하지 않는다.

### Persistence

* Runtime-owned lifecycle transition 이후 `AgentRun`이 저장된다.
* 최종 저장 상태가 `COMPLETED`인지 확인한다.
* Persistence가 lifecycle transition을 직접 수행하지 않는다.

Notes:

```text
- Runtime에 전달한 동일한 AgentContext 객체를 Tool이 참조했다.
- 실제 SQLite repository에서 RUNNING과 COMPLETED 저장 시점을 기록하고 최종 상태를 조회했다.
- RUN_STARTED → TOOL_STARTED → TOOL_COMPLETED → RUN_COMPLETED가 동일한 run_id로 기록됐다.
```

---

## 3. HITL Interruption / Resume E2E

Status: `[o]`

Approval이 필요한 SDK execution이 중단되고,
approve 또는 reject decision 이후 동일한 execution을 재개할 수 있는지 검증한다.

Expected flow:

```text
RUNNING
    ↓
approval interruption
    ↓
WAITING_APPROVAL
    ↓
AgentRun / RunState 저장
    ↓
approve or reject
    ↓
RunState restore
    ↓
RUNNING
    ↓
SDK execution resume
    ↓
COMPLETED 또는 기존 contract에 따른 결과
```

Verify:

* approval interruption이 올바르게 감지된다.
* lifecycle이 `WAITING_APPROVAL` 상태로 전환된다.
* HITL decision이 pending SDK interruption에 적용된다.
* resume 시 새로운 execution을 임의로 생성하지 않고 기존 SDK execution state를 사용한다.
* resume 이후 lifecycle이 기존 transition rule을 따른다.

approve와 reject에서 SDK behavior 또는 Harness behavior가 다르면 각각 Notes에 기록한다.

Notes:

```text
Approve:
- 복원된 RunState의 pending interruption에 approve를 적용하고 해당 state로 resume한 뒤 COMPLETED가 됐다.

Reject:
- 복원된 RunState의 pending interruption에 reject를 적용하고 해당 state로 resume한 뒤 COMPLETED가 됐다.
- 이 검증의 결정론적 SDK 대체 결과에서는 reject도 정상 RunResult를 반환하는 contract로 구성했다.

Other:
- 두 decision 모두 RUNNING → WAITING_APPROVAL → RUNNING → COMPLETED 저장 순서를 확인했다.
```

---

## 4. RunState Persistence / Restore

Status: `[o]`

HITL interruption에 필요한 SDK `RunState`가 `AgentRun`과 구분되어
저장되고 복원되는지 검증한다.

Verify:

* pending SDK `RunState`가 `run_id`를 기준으로 저장된다.
* 해당 `RunState`를 다시 복원할 수 있다.
* 복원된 state로 SDK execution을 이어갈 수 있다.
* `AgentRun`과 SDK `RunState`의 responsibility가 섞이지 않는다.
* Persistence가 approval decision을 직접 적용하지 않는다.

저장 형식이나 SDK state serialization과 관련된 제약이 발견되면 기록한다.

Notes:

```text
- SDK RunState의 `to_string()` 결과가 별도 run_states row에 저장되고,
  `RunState.from_string(agent, serialized_state)`로 복원되는 것을 실제 SQLite에서 검증했다.
- 테스트는 SDK serialization API 경계를 사용하되 실제 SDK state 대신 test double을 사용한다.
```

---

## 5. Tool Failure E2E

Status: `[o]`

Tool execution 중 failure가 발생했을 때 Harness가 이를 올바르게 처리하는지 검증한다.

Expected behavior는 현재 Runtime, Lifecycle, ToolGateway, SDK contract를 기준으로 확인하며
테스트를 통과시키기 위해 새로운 failure policy를 임의로 만들지 않는다.

Verify:

* `TOOL_STARTED` 이후 failure가 발생한다.
* `TOOL_FAILED`가 기록된다.
* Runtime에서 failure가 적절하게 전파된다.
* 해당 실행이 현재 lifecycle contract에 따라 `FAILED` 처리된다.
* 실패한 `AgentRun` 상태가 Persistence에 반영된다.
* failure가 임의로 숨겨지거나 성공으로 처리되지 않는다.

Tool exception에 대한 SDK wrapping, retry, propagation 방식 등
실제 실행 과정에서 발견되는 변수는 반드시 기록한다.

Notes:

```text
Failure type:
- `failure_error_function=None`인 SDK FunctionTool에서 발생한 RuntimeError.

SDK behavior:
- 외부 SDK 실행 loop는 결정론적으로 대체했으므로 모델에 의한 tool error wrapping/retry는 검증 범위가 아니다.
- SDK-compatible FunctionTool adapter는 원래 RuntimeError를 그대로 전파했다.

Harness behavior:
- ToolGateway가 TOOL_STARTED와 TOOL_FAILED를 기록한 뒤 error를 전파했다.
- AgentRuntime이 RUN_FAILED를 기록하고 lifecycle을 FAILED로 전환하여 저장한 뒤 같은 error를 재전파했다.

Other:
- 저장 순서는 RUNNING → FAILED였고 실제 SQLite의 최종 AgentRun도 FAILED였다.
```

---

## 6. Full Test Suite

Status: `[o]`

E2E test를 포함하여 전체 test suite를 실행한다.

Record:

```text
Command:
PYTHONPATH=src uv run pytest -q

Result:
PASS

Passed:
47

Failed:
0

Skipped:
0
```

기존 테스트 실패가 있다면 이번 E2E 변경으로 발생한 regression인지,
기존에 존재하던 문제인지 구분하여 기록한다.

Notes:

```text
- 2026-09-03 최종 실행 결과: 47 passed in 2.31s.
- pyproject.toml에 src layout의 pytest import path 설정이 없어 PYTHONPATH=src가 필요하다.
```

---

## 7. Boundary Review

Status: `[o]`

E2E validation 이후 실제 구현이 `ARCHITECTURE.md`에 정의된
layer responsibility를 침범하지 않는지 검토한다.

Check:

* `AgentRuntime`이 `AgentRun.status`를 직접 변경하지 않는다.
* lifecycle transition은 State Machine을 통한다.
* Persistence가 lifecycle rule을 소유하지 않는다.
* Persistence가 Agent execution을 orchestrate하지 않는다.
* HITL이 SDK execution loop를 재구현하지 않는다.
* Context가 execution orchestration 또는 persistence를 소유하지 않는다.
* Tool이 Harness tracing을 직접 관리하지 않는다.
* Tracing이 execution correctness 또는 lifecycle을 제어하지 않는다.
* `ToolGateway`가 개별 Tool business logic을 소유하지 않는다.
* E2E validation을 위해 새로운 불필요한 abstraction이 추가되지 않았다.

Boundary violation이 발견된 경우 위치와 이유를 기록한다.

Notes:

```text
- AgentRun.status의 domain 변경은 state_machine.py의 transition_to에만 존재한다.
- repository.py의 model.status 대입은 domain lifecycle 변경이 아니라 persistence model mapping이다.
- Runtime은 Lifecycle을 통해 전이하고 SDK Runner 호출 및 저장 시점만 orchestration한다.
- HITL은 RunState API에 decision만 적용하며, Context와 Tracing 및 ToolGateway의 기존 경계도 유지된다.
- 추가된 구현은 E2E test뿐이며 production abstraction이나 architecture 변경은 없다.
```

---

## 8. V0 Completion

Status: `[o]`

다음 항목이 모두 `[o]`가 되었을 때만 Agent Harness v0 validation을 완료한 것으로 본다.

```text
1. Normal Run E2E                       [o]
2. Context / Tool / Trace / Persistence [o]
3. HITL interruption / resume           [o]
4. RunState persistence / restore       [o]
5. Tool failure E2E                     [o]
6. Full test suite                      [o]
7. Boundary review                      [o]
```

Agent Harness v0 E2E validation을 완료했다.

모든 검증이 완료되면:

```text
V0 E2E Validation [o]
```

로 표시하고 `PROJECT.md`의 Current Stage와 Progress를 실제 결과에 맞게 업데이트한다.

Evaluation은 현재 v0 completion requirement에 포함하지 않는다.

Evaluation use case와 domain이 명확해진 이후
별도의 responsibility와 boundary를 결정하여 구현한다.
