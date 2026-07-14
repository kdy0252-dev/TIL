---
id: SAGA Pattern
started: 2025-04-10
tags:
  - ✅DONE
group:
  - "[[Java Spring Design Pattern]]"
---

# SAGA Pattern

Saga는 하나의 ACID Transaction으로 묶을 수 없는 여러 Service의 변경을 짧은 Local Transaction과 보상 작업으로 조율하는 Pattern이다. 물리적으로 과거를 지우는 Rollback이 아니라 이미 발생한 업무를 의미론적으로 상쇄한다.

## 기본 흐름

```text
T1 예약 생성 -> T2 결제 승인 -> T3 배차 확정

T3 실패
-> C2 결제 승인 취소
-> C1 예약 취소
```

보상도 외부 호출이며 실패할 수 있다. “모든 것을 catch하고 역순 Method를 호출”하는 Memory-only 구현은 Process Crash 후 어디까지 실행됐는지 복구하지 못한다. Saga ID, 현재 단계, 각 Command ID와 보상 상태를 Durable Storage에 기록해야 한다.

## Choreography와 Orchestration

| 방식 | 흐름 소유자 | 장점 | 위험 |
|---|---|---|---|
| Choreography | Event를 구독하는 각 Service | 느슨한 결합, 작은 흐름에 단순 | 전체 흐름 파악과 순환 Event가 어려움 |
| Orchestration | 중앙 Saga Workflow | 상태·Timeout·보상이 한곳에 보임 | Orchestrator 비대화 가능 |

단계가 둘뿐이고 독립적인 Event 반응이라면 Choreography가 충분할 수 있다. 단계, 분기, Timeout과 보상이 늘어나면 Temporal 같은 Durable Workflow Engine을 검토한다.

## 상태 모델

```java
public enum BookingSagaStage {
    STARTED,
    BOOKING_CREATED,
    PAYMENT_APPROVED,
    DISPATCH_CONFIRMED,
    COMPLETED,
    COMPENSATING,
    COMPENSATED,
    MANUAL_RECOVERY_REQUIRED
}

public record BookingSaga(
    UUID sagaId,
    long bookingId,
    BookingSagaStage stage,
    String paymentApprovalId,
    String dispatchId,
    long version
) {
    public BookingSaga advance(BookingSagaStage next) {
        return new BookingSaga(sagaId, bookingId, next, paymentApprovalId, dispatchId, version + 1);
    }

    public BookingSaga withPaymentApproval(String approvalId) {
        return new BookingSaga(
            sagaId, bookingId, BookingSagaStage.PAYMENT_APPROVED, approvalId, dispatchId, version + 1
        );
    }

    public BookingSaga withDispatch(String confirmedDispatchId) {
        return new BookingSaga(
            sagaId, bookingId, BookingSagaStage.DISPATCH_CONFIRMED,
            paymentApprovalId, confirmedDispatchId, version + 1
        );
    }
}
```

`version`으로 Optimistic Lock을 적용해 같은 Saga를 두 Worker가 동시에 진행하지 못하게 한다. 각 외부 Command의 Idempotency Key는 `sagaId + step`으로 고정한다.

## Port

```java
public interface BookingSagaPort {
    Either<SagaError, BookingSaga> create(StartBookingSagaCommand command);
    Either<SagaError, BookingSaga> findById(UUID sagaId);
    Either<SagaError, BookingSaga> save(BookingSaga saga);
}

public interface PaymentCommandPort {
    Either<SagaError, PaymentApproval> approve(ApprovePaymentCommand command);
    Either<SagaError, Void> cancel(CancelPaymentCommand command);
}

public interface DispatchCommandPort {
    Either<SagaError, DispatchConfirmation> confirm(ConfirmDispatchCommand command);
    Either<SagaError, Void> cancel(CancelDispatchCommand command);
}
```

## Orchestrator

Top-level Service는 단계만 나열하고 외부 예외 변환과 세부 검증은 각 Adapter·Domain Component에 둔다.

```java
@Service
@RequiredArgsConstructor
public class StartBookingSagaService implements StartBookingSagaUseCase {

    private final BookingSagaPort sagaPort;
    private final PaymentCommandPort paymentPort;
    private final DispatchCommandPort dispatchPort;
    private final SagaRecoveryAlarm recoveryAlarm;
    private final BookingSagaCompensationService compensationService;

    @Override
    public Either<SagaError, BookingSagaResource> start(StartBookingSagaCommand command) {
        Either<SagaError, BookingSaga> execution = sagaPort.create(command)
            .flatMap(saga -> approvePayment(saga, command))
            .flatMap(saga -> confirmDispatch(saga, command))
            .flatMap(saga -> sagaPort.save(saga.advance(BookingSagaStage.COMPLETED)));

        return execution.fold(
            error -> compensationService.compensate(command.sagaId(), error)
                                        .flatMap(ignored -> Either.left(error)),
            saga -> Either.right(BookingSagaResource.from(saga))
        );
    }

    private Either<SagaError, BookingSaga> approvePayment(
        BookingSaga saga,
        StartBookingSagaCommand command
    ) {
        ApprovePaymentCommand paymentCommand = new ApprovePaymentCommand(
            saga.sagaId() + ":payment-approval",
            saga.bookingId(),
            command.amount()
        );
        return paymentPort.approve(paymentCommand)
                          .map(approval -> saga.withPaymentApproval(approval.id()))
                          .flatMap(sagaPort::save);
    }

    private Either<SagaError, BookingSaga> confirmDispatch(
        BookingSaga saga,
        StartBookingSagaCommand command
    ) {
        ConfirmDispatchCommand dispatchCommand = new ConfirmDispatchCommand(
            saga.sagaId() + ":dispatch-confirmation",
            saga.bookingId(),
            command.serviceDate()
        );
        return dispatchPort.confirm(dispatchCommand)
                           .map(confirmation -> saga.withDispatch(confirmation.id()))
                           .flatMap(sagaPort::save);
    }
}
```

실제 Network 호출 사이에 Process가 죽을 수 있으므로 “외부 호출 성공 후 Saga 저장 전”의 틈도 처리해야 한다. 같은 Idempotency Key로 재호출했을 때 Provider가 기존 결과를 반환하도록 하고, Workflow 재개 시 단계별 결과를 Reconcile한다.

## 보상 Service

```java
@Service
@RequiredArgsConstructor
public class BookingSagaCompensationService {

    private final BookingSagaPort sagaPort;
    private final PaymentCommandPort paymentPort;
    private final DispatchCommandPort dispatchPort;

    public Either<SagaError, BookingSaga> compensate(UUID sagaId, SagaError cause) {
        return sagaPort.findById(sagaId)
                       .flatMap(saga -> sagaPort.save(saga.advance(BookingSagaStage.COMPENSATING)))
                       .flatMap(this::cancelDispatchWhenRequired)
                       .flatMap(this::cancelPaymentWhenRequired)
                       .flatMap(saga -> sagaPort.save(saga.advance(BookingSagaStage.COMPENSATED)))
                       .peekLeft(error -> recoveryAlarm.raise(sagaId, cause, error));
    }

    private Either<SagaError, BookingSaga> cancelDispatchWhenRequired(BookingSaga saga) {
        return Optional.ofNullable(saga.dispatchId())
                       .<Either<SagaError, BookingSaga>>map(dispatchId ->
                           dispatchPort.cancel(new CancelDispatchCommand(
                               saga.sagaId() + ":dispatch-cancellation",
                               dispatchId
                           )).map(ignored -> saga)
                       )
                       .orElseGet(() -> Either.right(saga));
    }

    private Either<SagaError, BookingSaga> cancelPaymentWhenRequired(BookingSaga saga) {
        return Optional.ofNullable(saga.paymentApprovalId())
                       .<Either<SagaError, BookingSaga>>map(approvalId ->
                           paymentPort.cancel(new CancelPaymentCommand(
                               saga.sagaId() + ":payment-cancellation",
                               approvalId
                           )).map(ignored -> saga)
                       )
                       .orElseGet(() -> Either.right(saga));
    }
}
```

보상은 실제 완료된 단계만 역순으로 실행하고, 각 보상 Command도 멱등해야 한다. 보상 실패를 Log만 남기고 끝내지 않고 Retry Schedule과 `MANUAL_RECOVERY_REQUIRED` 상태를 저장한다.

## 격리성

Saga 중간 State는 다른 Transaction에 보일 수 있다. 다음 기법을 조합한다.

- `PENDING`, `COMPENSATING` 같은 Semantic Lock 상태
- Aggregate Version을 이용한 Optimistic Lock
- 순서가 바뀌어도 안전한 Commutative Update
- 조회 시 완료 State만 노출하는 Policy
- Reconciliation Job으로 오래 멈춘 Saga 탐지

## 운영 Metric

- 단계별 성공·실패·Timeout 수
- Stage 체류 시간 P95/P99
- Retry와 보상 횟수
- `MANUAL_RECOVERY_REQUIRED` Saga 수와 나이
- Idempotency 중복 Hit 수
- Orphan 외부 Transaction Reconciliation 결과

## 기억할 점

Saga의 핵심은 `try-catch`와 보상 Method가 아니다. 단계 State를 Durable하게 저장하고, Command를 멱등하게 만들며, Crash 후 재개·보상 실패·Reconciliation까지 운영할 수 있어야 한다.

# Reference

- [Microservices.io - Saga](https://microservices.io/patterns/data/saga.html)
- [Temporal Saga Pattern](https://docs.temporal.io/develop/java/compensating-actions)
