---
id: Command Pattern
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
---

# Command Pattern

Command Pattern은 “무엇을 실행할지”를 값으로 만든다. 호출자는 Receiver의 Method를 직접 호출하지 않고 Command를 Queue에 저장하거나 Handler에 전달한다. 실행 시각을 늦추고, 재시도·감사·권한 검사·멱등성 같은 공통 정책을 적용할 때 유용하다.

## Command와 DTO를 구분한다

Web Request는 외부 Protocol DTO이고 Command는 Application이 이해하는 검증된 입력이다. Controller에서 Request를 Command로 명시적으로 변환한다.

```java
public record CancelBookingCommand(
    long bookingId,
    String reason,
    String idempotencyKey,
    AuditActor actor
) {
    public CancelBookingCommand {
        Objects.requireNonNull(reason);
        Objects.requireNonNull(idempotencyKey);
        Objects.requireNonNull(actor);
    }
}
```

## Handler 계약

```java
@FunctionalInterface
public interface CommandHandler<C, R> {
    R handle(C command);
}
```

```java
@Service
@RequiredArgsConstructor
public class CancelBookingCommandHandler
    implements CommandHandler<CancelBookingCommand, BookingResource> {

    private final BookingPort bookingPort;
    private final IdempotencyPort idempotencyPort;
    private final BookingEventOutboxPort outboxPort;
    private final BookingExceptionMapper exceptionMapper;

    @Override
    @Transactional
    public BookingResource handle(CancelBookingCommand command) {
        return idempotencyPort.findResult(command.idempotencyKey())
                              .map(Either::<BookingError, BookingResource>right)
                              .orElseGet(() -> execute(command))
                              .getOrElseThrow(exceptionMapper::toException);
    }

    private Either<BookingError, BookingResource> execute(CancelBookingCommand command) {
        return bookingPort.findById(command.bookingId())
                          .flatMap(booking -> booking.cancel(command.reason(), command.actor()))
                          .flatMap(bookingPort::save)
                          .flatMap(saved -> outboxPort.append(BookingCancelled.from(saved))
                                                      .map(ignored -> saved))
                          .map(BookingResource::from)
                          .flatMap(resource -> idempotencyPort.save(command.idempotencyKey(), resource)
                                                              .map(ignored -> resource));
    }
}
```

Command Handler는 `booking.cancel`이라는 Domain 규칙, 저장과 Outbox를 순서대로 조율한다. 내부 Pipeline의 실패는 Handler 경계에서 Application Exception으로 바꾸고 HTTP Mapping은 Controller Advice가 결정한다.

## Queue에 저장하는 Command

Process Memory의 Lambda는 재시작 후 복원할 수 없다. Durable Queue에 넣을 Command는 Type, Schema Version, ID와 생성 시각을 직렬화 가능한 값으로 저장한다.

```java
public record CommandEnvelope<T>(
    UUID commandId,
    String commandType,
    int schemaVersion,
    Instant createdAt,
    String tenantId,
    T payload
) {
    public static <T> CommandEnvelope<T> create(
        String commandType,
        int schemaVersion,
        String tenantId,
        T payload,
        Clock clock
    ) {
        return new CommandEnvelope<>(
            UUID.randomUUID(),
            commandType,
            schemaVersion,
            clock.instant(),
            tenantId,
            payload
        );
    }
}
```

Consumer는 `commandId`로 중복 실행을 막고, 모르는 Schema Version은 DLQ로 보낸다. “한 번만 전달”을 기대하지 않고 같은 Command가 여러 번 와도 결과가 같게 설계한다.

## Command Bus

작은 Application에서는 Handler 직접 주입이 더 단순하다. Command 종류가 많고 Middleware가 필요할 때 Registry 기반 Bus를 고려한다.

```java
@Component
public class CommandBus {

    private final Map<Class<?>, CommandHandler<?, ?>> handlers;

    public CommandBus(List<CommandHandler<?, ?>> handlers, CommandTypeResolver typeResolver) {
        this.handlers = handlers.stream()
                                .collect(Collectors.toUnmodifiableMap(
                                    typeResolver::commandTypeOf,
                                    Function.identity(),
                                    (first, duplicate) -> {
                                        throw new IllegalStateException("Duplicate command handler");
                                    }
                                ));
    }

    public <C, R> R dispatch(C command) {
        return Optional.ofNullable(handlers.get(command.getClass()))
                       .map(handler -> this.<C, R>cast(handler).handle(command))
                       .orElseThrow(() -> new CommandHandlerNotFoundException(command.getClass()));
    }
}
```

Generic Cast는 Registry 내부 한곳에 격리하고 등록 시 Type 계약을 검증한다. 모든 Service 호출을 무조건 Bus로 우회시키면 추적성과 Type 안전성이 오히려 나빠질 수 있다.

## Undo의 한계

Memory Editor의 Undo는 반대 Command로 구현할 수 있다. 결제·Message 발행·외부 API처럼 이미 밖으로 나간 Side Effect는 과거를 지우는 것이 아니라 별도의 보상 Command가 필요하다. 보상도 실패할 수 있으므로 상태와 재시도 정책을 저장한다.

## 기억할 점

Command는 Method 호출을 Class로 포장하는 장식이 아니다. 요청을 값으로 만들어 실행을 늦추고 공통 정책을 적용하는 도구다. Durable Command라면 멱등성, Versioning, 감사와 실패 복구가 Pattern의 일부다.

# Reference

- [Refactoring.Guru - Command](https://refactoring.guru/design-patterns/command)
