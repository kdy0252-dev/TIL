---
id: Observer Pattern
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
---

# Observer Pattern

Observer Pattern은 한 객체의 Event를 여러 Subscriber가 받도록 Publisher와 Subscriber를 분리한다. 단순 Listener List를 넘어 Delivery 시점, 실패 격리, 순서, 중복과 Transaction 경계를 함께 설계해야 한다.

## Domain Event

Event는 “무언가 하라”는 Command가 아니라 이미 발생한 사실이다. 과거형 이름과 업무 식별자를 사용한다.

```java
public sealed interface BookingDomainEvent {
    UUID eventId();
    long bookingId();
    Instant occurredAt();
}

public record BookingCancelled(
    UUID eventId,
    long bookingId,
    String reason,
    Instant occurredAt
) implements BookingDomainEvent {
}
```

Domain Model은 Subscriber를 알지 않고 State 변경과 함께 Event를 만든다.

```java
public Either<BookingError, BookingChange> cancel(String reason, AuditActor actor, Clock clock) {
    return Either.cond(
        status.canCancel(),
        () -> {
            Booking cancelled = copyWith(BookingStatus.CANCELLED, audit.updatedBy(actor));
            BookingCancelled event = new BookingCancelled(
                UUID.randomUUID(), id, reason, clock.instant()
            );
            return new BookingChange(cancelled, List.of(event));
        },
        () -> new BookingError.InvalidCancellationState(id, status)
    );
}
```

## Process 내부 Observer

같은 Transaction 안에서 반드시 실행돼야 하는 반응은 동기 Listener로 구성할 수 있다.

```java
@Component
@RequiredArgsConstructor
public class BookingCancellationAuditListener {

    private final BookingAuditPort auditPort;

    @TransactionalEventListener(phase = TransactionPhase.BEFORE_COMMIT)
    public void on(BookingCancelled event) {
        auditPort.append(BookingAuditRecord.from(event))
                 .getOrElseThrow(BookingAuditException::new);
    }
}
```

Listener 실패가 원 Transaction을 Rollback해야 하는지 먼저 결정한다. `AFTER_COMMIT` Listener 실패는 이미 Commit된 업무를 되돌릴 수 없다.

## Process 밖으로 전달하는 Observer

Message Broker에 직접 Publish한 뒤 Database Commit이 실패하거나, Commit 후 Publish 전에 Process가 죽는 Dual Write 문제가 있다. Transactional Outbox를 사용하면 Aggregate 변경과 Event 저장을 같은 Transaction에 묶을 수 있다.

```java
@Service
@RequiredArgsConstructor
public class CancelBookingService implements CancelBookingUseCase {

    private final BookingPort bookingPort;
    private final BookingEventOutboxPort outboxPort;
    private final BookingExceptionMapper exceptionMapper;

    @Override
    @Transactional
    public BookingResource cancel(CancelBookingCommand command) {
        return bookingPort.findById(command.bookingId())
                          .flatMap(booking -> booking.cancel(command.reason(), command.actor(), command.clock()))
                          .flatMap(change -> bookingPort.save(change.booking())
                                                    .flatMap(saved -> outboxPort.appendAll(change.events())
                                                                                 .map(ignored -> saved)))
                          .map(BookingResource::from)
                          .getOrElseThrow(exceptionMapper::toException);
    }
}
```

Outbox Publisher가 Commit된 Event를 Broker로 재시도하고 Consumer는 `eventId`로 중복을 제거한다.

## Subscriber 실패 격리

여러 Subscriber를 한 Thread에서 순서대로 호출하면 앞 Subscriber의 지연과 실패가 뒤로 전파된다. 중요한 Subscriber는 독립 Consumer Group, Retry Topic과 DLQ를 가진다.

```java
@Component
@RequiredArgsConstructor
public class BookingCancelledNotificationConsumer {

    private final NotificationPort notificationPort;
    private final ProcessedEventPort processedEventPort;

    @Transactional
    public void consume(BookingCancelled event) {
        processedEventPort.exists(event.eventId())
                                 .filter(processed -> !processed)
                                 .<Either<NotificationError, Boolean>>map(Either::right)
                                 .orElseGet(() -> Either.left(new NotificationError.AlreadyProcessed(event.eventId())))
                                 .flatMap(ignored -> notificationPort.sendCancellation(event))
                                 .flatMap(ignored -> processedEventPort.markProcessed(event.eventId()))
                                 .getOrElseThrow(NotificationConsumeException::new);
    }
}
```

“이미 처리됨”을 Error가 아닌 성공적 No-op로 모델링할 수도 있다. 중요한 것은 중복 Delivery 정책을 명시하는 것이다.

## Event 순서와 Version

- 같은 Aggregate의 Event는 `aggregateId + aggregateVersion`을 포함한다.
- Broker Partition Key를 Aggregate ID로 두면 같은 Partition 안의 순서를 이용할 수 있다.
- Consumer는 기대 Version보다 미래 Event가 오면 재시도하거나 재조회한다.
- Event Schema는 Consumer가 독립 배포될 수 있도록 호환성을 유지한다.

## Observer를 쓰지 않는 편이 나은 경우

- 호출 결과가 즉시 필요하고 실패를 호출자에게 반환해야 한다.
- Subscriber가 하나뿐이고 직접 Method 호출이 더 명확하다.
- Event 순서와 Transaction을 보장할 Infrastructure가 없다.
- 실제로는 “작업을 수행하라”는 Command인데 Event로 이름만 바꾼 경우다.

## 기억할 점

Observer Pattern의 핵심은 `List<Listener>`가 아니다. Event의 의미, Transaction, Delivery 보장, 중복, 순서와 Subscriber 실패를 설계해야 느슨한 결합이 운영 가능한 구조가 된다.

# Reference

- [Spring Modulith Events](https://docs.spring.io/spring-modulith/reference/events.html)
- [[Transactional Outbox 패턴]]
