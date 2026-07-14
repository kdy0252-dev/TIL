---
id: Application Service Orchestration
started: 2026-05-21
tags:
  - ✅DONE
  - Architecture
  - DDD
  - Service
group:
  - "[[Java Spring Architecture]]"
---
# Application Service Orchestration

## 1. 개요 (Overview)
Controller가 직접 호출하는 Application Service는 Use Case의 전체 업무 흐름을 보여주는 **Orchestrator**입니다. 상세 계산, 상태 검증, 데이터 조립과 예외 변환까지 한 클래스에 넣으면 흐름을 이해하기 어렵고 테스트가 거대해집니다.

좋은 Orchestrator는 "무엇을 어떤 순서로 수행하는가"를 보여주고, 각 단계의 세부 규칙은 Domain Model이나 Internal Service에 위임합니다.

---

## 2. 책임 배치

| 책임 | 위치 |
|---|---|
| HTTP 검증·변환 | Inbound Adapter |
| Use Case 단계와 Transaction 경계 | Application Service |
| 상태 전이·불변식·계산 | Domain Model·Domain Service |
| 복잡한 조회·조립 | Internal Loader·Assembler |
| DB·외부 API 호출 | Out Port와 Adapter |
| 기술 예외 변환 | Outbound Adapter |

---

## 3. Orchestrator 예제

```java
@Transactional
public DrivingResource create(CreateDrivingCommand command) {
    DrivingContext context = contextLoader.load(command);
    Driving driving = drivingCreator.create(command, context);
    Driving saved = saveDrivingOutPort.save(driving);
    eventPublisher.publish(DrivingCreated.from(saved));
    return resourceAssembler.assemble(saved, context);
}
```

Top-level Method만 읽어도 업무 단계가 보여야 합니다.

---

## 4. Internal Service 분리 기준
- 하나의 단계가 독립적인 이름과 규칙을 가집니다.
- 여러 Use Case에서 재사용됩니다.
- 예외 처리나 조건 분기가 전체 흐름을 가립니다.
- 별도 Test가 이해를 쉽게 합니다.
- 외부 데이터 여러 개를 조립합니다.

단순 한 줄 위임을 위해 클래스를 만들지는 않습니다. 분리는 추상화 수가 아니라 인지 부하를 줄여야 합니다.

---

## 5. Self-invocation 문제
Spring Proxy 기반 `@Transactional`, `@Async`, `@Retry`는 같은 객체 내부의 `this.method()` 호출에 적용되지 않습니다. 세부 단계를 별도 Bean으로 분리하는 이유를 Proxy 우회 해결에만 두기보다 Transaction과 책임 경계를 함께 명확히 해야 합니다.

---

## 6. 실무 사례 적용 관점
이 사례는 Controller-facing Service에서 업무 흐름을 열거하고 `internal` Package의 Loader, Validator, Processor, Assembler로 세부 처리를 위임합니다. Domain Model의 `create()`, `load()`, 상태 변경 메서드가 불변식을 소유합니다.

여러 Vertical Slice를 조합할 때는 Orchestrator Slice가 각 Slice의 공개 Use Case를 호출합니다. 다른 Slice의 Internal Service를 재사용하지 않습니다.

---

## 7. 테스트 전략
- Orchestrator Test: 단계 순서, 결과 조합, 실패 전파
- Domain Test: 상태 전이와 계산 규칙
- Internal Service Test: 상세 분기와 데이터 처리
- Adapter Test: 기술 예외와 외부 계약
- Integration Test: Transaction과 실제 Wiring

---

## 8. Transaction 경계
Application Service는 Use Case의 원자성 경계를 소유합니다. 모든 하위 메서드에 습관적으로 `@Transactional`을 붙이지 않습니다.

```text
Application Service Transaction
  -> Aggregate Load
  -> Business Method
  -> Save
  -> Outbox Insert
COMMIT
```

외부 API는 가능하면 Transaction 밖에서 호출하거나 Outbox로 분리합니다. 반드시 Transaction 중 호출해야 한다면 Timeout과 Lock 점유 영향을 명시합니다.

## 9. Read-Modify-Write 경쟁
Aggregate를 읽고 변경해 저장하는 사이 다른 Transaction이 상태를 바꿀 수 있습니다. Version Column을 이용한 Optimistic Lock과 업무 상태 조건을 사용합니다.

Orchestrator는 Lock 예외를 업무 오류로 변환할지 재시도할지 결정하고, Domain은 현재 상태에서 허용되는 전이를 검증합니다.

## 10. 오류 모델

```text
Adapter Technical Error
  -> Out Port Error
  -> Application Error
  -> Web Error Response
```

Top-level Service가 모든 Exception을 Catch해 문자열로 바꾸지 않습니다. Adapter가 기술 오류를 안정적인 오류 유형으로 변환하고, Application은 업무 흐름에 필요한 분기만 처리합니다.

## 11. Loader와 Assembler
- **Loader**: Use Case 실행에 필요한 상태를 Port에서 가져옴
- **Context**: 여러 입력을 의미 있는 묶음으로 전달
- **Processor**: 한 단계의 업무 처리
- **Assembler**: 결과를 Resource로 조립

Loader가 Domain 결정을 내리거나 Assembler가 DB를 조회하지 않게 책임을 제한합니다.

## 12. 다른 Slice 조합
여러 Slice가 필요한 흐름은 Orchestrator가 공개 Use Case를 호출합니다.

```text
Trip Orchestrator
  -> BookingLookupUseCase
  -> VehicleScheduleUseCase
  -> DrivingCreateUseCase
```

하나의 Transaction이 여러 Slice의 Table을 직접 수정하면 소유권이 흐려집니다. 각 Slice의 공개 Command를 통하거나 Eventual Consistency가 적합한지 판단합니다.

## 13. Domain Service와 Application Service
Domain Service는 외부 기술 없이 여러 Domain Object에 걸친 순수한 업무 계산을 담당합니다. Application Service는 조회·저장·외부 호출과 Transaction을 조정합니다.

Clock, Repository, HTTP Client가 필요한 로직을 Domain Service라고 부르며 숨기지 않습니다.

## 14. 안티패턴
- Controller가 여러 Repository를 직접 호출
- Application Service에 수백 줄의 조건·계산
- 모든 세부 메서드를 Public Service Bean으로 분리
- 다른 Slice의 Internal Service 재사용
- Domain Entity를 HTTP Response로 직접 반환
- Self-invocation으로 Proxy 기능이 적용될 것이라 가정

## 15. Review 체크리스트
- Public Method만 읽어 Use Case 흐름이 보이는가?
- 각 업무 규칙의 단일 소유자가 있는가?
- Transaction 안에 불필요한 Network 호출이 있는가?
- 다른 Slice의 공개 계약만 사용하는가?
- 세부 클래스 분리가 인지 부하를 실제로 줄이는가?

---

## 16. 실무 사례 적용 진단과 개선 과제

`BulkDispatchService`, `ManualDispatchService` 등은 Observation과 내부 Resolver·Loader를 활용해 Orchestrator 분리를 진행하고 있습니다. 반면 일부 Use Case는 세부 조회 조립, 예외 변환, 외부 호출과 상태 변경을 한 Class에서 다뤄 변경 영향이 큽니다.

우선 Controller가 직접 호출하는 Service를 대상으로 Transaction 범위, 외부 I/O, 상태 전이를 표로 만들고, 상세 계산은 Domain Model, 조회 조립은 Loader/Assembler, 외부 실패 처리는 Adapter로 이동합니다. 단순히 Private Method를 다른 Bean으로 옮기는 것이 아니라 의존 방향과 책임을 함께 분리해야 합니다.

완료 기준은 최상위 Service Method가 5~7개의 업무 단계만 읽히고, Self-invocation에 의존하지 않으며, 각 내부 Service를 독립 Test할 수 있고 Transaction·Observation 경계가 Test로 고정된 상태입니다.

---

# Reference
- [[차량 배차 플랫폼 소프트웨어 아키텍처 사례]]
- [[Vertical Slice와 Modular Monolith]]
- [[Hexagonal Architecture]]
