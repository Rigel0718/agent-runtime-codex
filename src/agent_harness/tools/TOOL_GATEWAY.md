# Tool Gateway

## 목적

`ToolGateway`는 OpenAI Agents SDK의 Agent가 사용하는 Tool에 대해
**Harness가 제어할 수 있는 실행 경계(execution boundary)** 를 제공한다.

OpenAI Agents SDK는 계속해서 Agent 실행과 Tool을 언제 호출할지 결정하는 역할을 담당한다.

`ToolGateway`는 SDK의 Tool 호출 루프를 재구현하지 않으면서, Harness가 관리하는 Tool을 찾고 실행하는 과정을 제어한다.

개념적인 구조는 다음과 같다.

```text
OpenAI Agents SDK
        ↓
SDK Tool Call
        ↓
ToolGateway
        ↓
Actual Tool
```

## Responsibilities

초기 `ToolGateway`는 다음 역할을 담당한다.

* Harness가 관리하는 Tool을 등록한다.
* 등록된 Tool을 찾는다.
* 등록된 Tool을 실행한다.
* Tool 호출 인자를 실제 Tool에 전달한다.
* 실제 Tool의 실행 결과를 반환한다.
* 등록되지 않은 Tool의 실행을 거부한다.
* 실제 Tool에서 발생한 오류를 조용히 무시하지 않고 그대로 전파한다.

구현은 명확하고 최소한으로 유지한다.

## Responsibility Boundary

`ToolGateway`는 다음 역할을 담당하지 않는다.

* SDK Agent 실행을 orchestration하지 않는다.
* `AgentRun`의 lifecycle status를 직접 변경하지 않는다.
* 개별 Tool의 business logic을 구현하지 않는다.
* OpenAI Agents SDK의 Agent execution loop를 재구현하지 않는다.
* OpenAI Agents SDK의 tool-calling loop를 재구현하지 않는다.
* Persistence를 구현하지 않는다.
* HITL 또는 approval flow를 구현하지 않는다.
* Tracing을 구현하지 않는다.
* Context management를 구현하지 않는다.
* Evaluation을 구현하지 않는다.

또한 다음 기능은 초기 MVP 범위에 포함하지 않는다.

* Permission policy
* Retry
* Timeout
* Audit logging
* Sandbox execution

이 기능들은 이후 각각의 component가 구현될 때 Tool Gateway와 통합할 수 있다.

## 초기 설계

현재 책임을 만족하는 가장 작은 구조를 사용한다.

초기 MVP에서는 `ToolGateway`가 내부적으로 단순한 registry를 소유하는 것으로 충분하다.

개념적으로 다음과 같다.

```text
ToolGateway
    ├── register
    ├── resolve
    └── execute
```

위 이름은 각각의 책임을 표현하기 위한 것이며, 반드시 동일한 형태의 public API를 구현해야 한다는 의미는 아니다.

현재 구현에서 실제로 필요하지 않다면 다음과 같은 별도의 abstraction을 미리 만들지 않는다.

* ToolRegistry
* ToolExecutor
* ToolPolicy
* ToolResult
* ToolContext

## ToolGateway의 책임

`ToolGateway`는 Tool 실행을 관리하지만 개별 Tool의 business logic을 소유하지 않는다.

예를 들어 다음과 같은 구조를 가진다.

```text
ToolGateway
    ↓
Search Tool
    ↓
Search implementation
```

Gateway는 어떤 등록된 Tool을 실행할지 결정하고 해당 Tool에 실행을 위임한다.

실제 Tool이 무엇을 수행하는지는 각 Tool 구현의 책임이다.

## OpenAI Agents SDK 연동

Agent execution loop는 계속해서 OpenAI Agents SDK가 담당해야 한다.

Harness에서 다음과 같은 실행 흐름을 직접 구현하지 않는다.

```text
model response
    ↓
detect tool call
    ↓
execute tool
    ↓
send result to model
    ↓
repeat
```

이 과정은 OpenAI Agents SDK의 책임이다.

대신 SDK와 호환되는 Tool의 실행이 `ToolGateway`를 통과하도록 연결한다.

개념적인 구조는 다음과 같다.

```text
SDK Agent
    ↓
SDK-compatible Tool
    ↓
ToolGateway
    ↓
Actual Tool
```

구체적인 연동 방식은 현재 설치된 OpenAI Agents SDK API와 기존 repository의 구현 방식을 따른다.

SDK 내부 동작을 임의로 가정하거나, SDK의 Agent 또는 Runner 동작을 custom implementation으로 대체하지 않는다.

## AgentRuntime과의 관계

`AgentRuntime`과 `ToolGateway`는 서로 다른 실행 경계를 관리한다.

`AgentRuntime`은 **Agent 단위 실행**을 관리한다.

```text
AgentRuntime
    ↓
AgentLifecycle.start()
    ↓
OpenAI Agents SDK Runner
    ↓
success / failure
    ↓
AgentLifecycle
```

`ToolGateway`는 **Tool 단위 실행**을 관리한다.

```text
SDK Tool Call
    ↓
ToolGateway
    ↓
Actual Tool
```

따라서 `ToolGateway`가 lifecycle이나 runtime의 책임을 가져가서는 안 된다.

## Tests

초기 구현에서는 최소한 다음 동작을 검증한다.

* 등록된 Tool을 실행할 수 있다.
* Tool 호출 인자가 실제 Tool에 올바르게 전달된다.
* 실제 Tool의 실행 결과가 올바르게 반환된다.
* 등록되지 않은 Tool은 실행할 수 없다.
* 실제 Tool에서 발생한 오류가 조용히 무시되지 않는다.

SDK 연동이 구현된다면 SDK와 호환되는 Tool 실행이 실제로 `ToolGateway`를 통과하는지도 검증한다.

테스트에서 실제 OpenAI API 호출을 사용하지 않는다.

OpenAI Agents SDK 내부 동작 자체를 테스트하거나 재현하지 않는다.

## 현재 구현 범위

현재 Tool Gateway 단계의 목표는
**Harness가 제어할 수 있는 안정적인 Tool 실행 경계를 만드는 것**이다.

현재 단계에서는 다음 흐름을 구현하는 데 필요한 기능만 구현한다.

```text
register
    ↓
resolve
    ↓
execute
```

그리고 SDK의 Tool 실행을 Gateway로 연결하기 위해 필요한 최소한의 연동만 구현한다.

향후 Harness infrastructure를 현재 단계에서 미리 구현하지 않는다.

## Future Integration

`ToolGateway`는 향후 다음과 같은 Harness 기능이 연결될 수 있는 지점으로 사용한다.

* HITL
* Tracing
* Persistence
* Execution policy

이 기능들은 향후 각 component의 구현 단계에서 다루며, 현재 Tool Gateway 단계에서는 구현하지 않는다.
