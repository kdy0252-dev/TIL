---
id: Clean Architecture
started: 2025-05-28
tags:
  - ✅DONE
group:
  - "[[Architecture]]"
---

# Clean Architecture

Clean Architecture는 업무 정책을 Framework, Database, Web와 외부 Provider의 변화로부터 보호하는 의존성 규칙이다. 안쪽 계층은 바깥쪽 계층을 알지 않고, Source Code Dependency는 Domain을 향한다.

```text
Web Adapter -> In Port -> Application Service -> Domain
                               |
                               v
                            Out Port
                               ^
                               |
                    Persistence/External Adapter
```

## 계층의 역할

| 계층 | 책임 | 알면 안 되는 것 |
|---|---|---|
| Domain | 불변식, 상태 전이와 계산 | HTTP, JPA, Provider DTO |
| Application | Use Case 흐름과 Transaction 경계 | 구체 Repository·SDK |
| In Port | 외부에서 호출할 업무 계약 | Controller Request |
| Out Port | Application이 필요한 외부 계약 | Vendor API 세부사항 |
| In Adapter | Protocol 검증과 Request/Response Mapping | JPA Entity |
| Out Adapter | Database·SDK와 Domain Mapping | Web DTO |

## 실무 예제: 예약 취소

### Domain Model

Domain은 Framework Annotation 없이 예약 취소 가능 여부와 상태 변경을 책임진다.

```java
@Getter
@Builder(access = AccessLevel.PRIVATE)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
public final class Booking {

    private final long id;
    private final BookingStatus status;
    private final Cancellation cancellation;
    private final Audit audit;

    public static Booking create(AuditActor actor) {
        return Booking.builder()
                      .id(TSID.fast().toLong())
                      .status(BookingStatus.PENDING)
                      .audit(Audit.createdBy(actor))
                      .build();
    }

    public static Booking load(
        long id,
        BookingStatus status,
        Cancellation cancellation,
        Audit audit
    ) {
        return Booking.builder()
                      .id(id)
                      .status(status)
                      .cancellation(cancellation)
                      .audit(audit)
                      .build();
    }

    public Either<BookingError, Booking> cancel(
        CancellationReason reason,
        AuditActor actor,
        Instant cancelledAt
    ) {
        return Either.cond(
            status.canCancel(),
            () -> Booking.builder()
                         .id(id)
                         .status(BookingStatus.CANCELLED)
                         .cancellation(new Cancellation(reason, cancelledAt))
                         .audit(audit.updatedBy(actor))
                         .build(),
            () -> new BookingError.InvalidCancellationState(id, status)
        );
    }
}
```

### In Port와 Command

```java
public record CancelBookingCommand(
    long bookingId,
    CancellationReason reason,
    AuditActor actor
) {
}

public interface CancelBookingUseCase {
    Either<BookingError, BookingResource> cancel(CancelBookingCommand command);
}
```

### Out Port

```java
public interface LoadBookingPort {
    Either<BookingError, Booking> findById(long bookingId);
}

public interface SaveBookingPort {
    Either<BookingError, Booking> save(Booking booking);
}

public interface BookingEventOutboxPort {
    Either<BookingError, Void> append(BookingCancelled event);
}
```

### Application Service

Service는 상위 업무 흐름만 열거한다. 취소 규칙, Mapping과 예외 변환을 내부에 펼치지 않는다.

```java
@Service
@Application
@RequiredArgsConstructor
public class CancelBookingService implements CancelBookingUseCase {

    private final LoadBookingPort loadBookingPort;
    private final SaveBookingPort saveBookingPort;
    private final BookingEventOutboxPort outboxPort;
    private final Clock clock;

    @Override
    @Transactional
    public Either<BookingError, BookingResource> cancel(CancelBookingCommand command) {
        return loadBookingPort.findById(command.bookingId())
                              .flatMap(booking -> booking.cancel(
                                  command.reason(),
                                  command.actor(),
                                  clock.instant()
                              ))
                              .flatMap(saveBookingPort::save)
                              .flatMap(saved -> outboxPort.append(BookingCancelled.from(saved))
                                                          .map(ignored -> saved))
                              .map(BookingResource::from);
    }
}
```

### Web Adapter

Request는 Bean Validation으로 Protocol 형식을 검사하고 Command로 변환한다. Domain Model이나 JPA Entity를 Response로 직접 노출하지 않는다.

```java
public record CancelBookingRequest(
    @NotBlank
    @Size(max = 500)
    String reason
) {
    public CancelBookingCommand toCommand(long bookingId, AuditActor actor) {
        return new CancelBookingCommand(
            bookingId,
            CancellationReason.of(reason),
            actor
        );
    }
}
```

```java
@RestController
@RequiredArgsConstructor
@RequestMapping("/bookings")
public class BookingController {

    private final CancelBookingUseCase cancelBookingUseCase;
    private final BookingErrorResponseMapper errorMapper;

    @Operation(summary = "예약 취소")
    @PostMapping("/{bookingId}/cancellation")
    public ResponseEntity<BookingResponse> cancel(
        @PathVariable long bookingId,
        @Valid @RequestBody CancelBookingRequest request,
        @AuthenticationPrincipal AccountPrincipal principal
    ) {
        return cancelBookingUseCase.cancel(request.toCommand(bookingId, principal.toAuditActor()))
                                   .fold(
                                       errorMapper::toResponse,
                                       resource -> ResponseEntity.ok(BookingResponse.from(resource))
                                   );
    }
}
```

### Persistence Adapter

JPA Entity와 Domain의 변환은 Mapper가 맡고 Database 예외는 Adapter에서 Port Error로 바꾼다.

```java
@Component
@Adapter
@RequiredArgsConstructor
public class BookingPersistenceAdapter implements LoadBookingPort, SaveBookingPort {

    private final BookingJpaRepository repository;
    private final BookingPersistenceMapper mapper;

    @Override
    @Transactional(readOnly = true)
    public Either<BookingError, Booking> findById(long bookingId) {
        return repository.findById(bookingId)
                         .map(mapper::toDomain)
                         .<Either<BookingError, Booking>>map(Either::right)
                         .orElseGet(() -> Either.left(new BookingError.NotFound(bookingId)));
    }

    @Override
    @Transactional
    public Either<BookingError, Booking> save(Booking booking) {
        return Try.of(() -> repository.save(mapper.toEntity(booking)))
                  .map(mapper::toDomain)
                  .toEither()
                  .mapLeft(cause -> new BookingError.PersistenceFailure(booking.getId(), cause));
    }
}
```

JPA Entity는 Persistence Adapter 안에 있고 Setter를 외부에 노출하지 않는다. 신규 Entity 생성과 기존 Entity 갱신은 Mapper와 의미 있는 `apply` Method로 제한한다.

## Error 경계

- Domain Error는 업무 규칙 실패를 표현한다.
- Out Adapter는 SDK·Database 예외를 Application Error로 변환한다.
- Web Adapter는 업무 Error를 HTTP Status와 Error Body로 변환한다.
- `Throwable`, Provider DTO와 JPA Entity가 계층을 가로지르지 않는다.

## Test 전략

1. Domain Model은 Framework 없이 상태 전이와 불변식을 단위 Test한다.
2. Application Service는 Port Fake로 업무 흐름과 Error 전파를 Test한다.
3. Persistence Adapter는 Testcontainers로 Mapping과 Query를 통합 Test한다.
4. Controller는 Validation, HTTP Mapping과 인증을 Slice Test한다.
5. Port 구현은 공통 Contract Test로 대체 가능성을 확인한다.

## 과도한 계층화 피하기

단순 CRUD 하나에도 무조건 Class를 여러 개 만드는 것이 목표는 아니다. 업무 규칙, 외부 변경 가능성, 독립 Test와 재사용 경계가 있을 때 계층이 가치가 있다. Mapper가 단순 Field 복사뿐이고 변경 가능성도 없다면 Record Factory로 충분할 수 있다.

## 기억할 점

Clean Architecture의 핵심은 Folder 이름이 아니라 의존 방향이다. Domain은 업무 언어로 완결되고, Application은 Port를 통해 외부를 사용하며, Adapter가 Framework와 Provider 세부사항을 변환해야 한다.

# Reference

- [Clean Architecture](https://www.oreilly.com/library/view/clean-architecture-a/9780134494272/)
- [[Hexagonal Architecture]]
