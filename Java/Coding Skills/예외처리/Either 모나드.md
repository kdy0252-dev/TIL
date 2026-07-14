---
id: Either 모나드
started: 2025-12-29
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
  - "[[Functional Programming]]"
---

# Either 모나드

`Either<L, R>`는 실패와 성공을 하나의 반환 타입으로 표현한다. 관례상 `Left`는 실패, `Right`는 성공이다. `Optional<T>`가 값의 부재만 알려 준다면 `Either<Error, T>`는 왜 실패했는지까지 타입으로 전달한다. FMS 구조에서는 이 타입을 모든 계층에 그대로 노출하지 않고 Domain Model과 Out Port의 실패 계약으로 제한한다.

## 언제 사용하는가

- 입력 검증처럼 호출자가 실패 이유에 따라 행동해야 할 때
- Out Port가 외부 시스템·Database 실패를 반환할 때
- 여러 실패 가능한 단계를 `flatMap`으로 합성할 때
- 예외를 숨기지 않고 Domain·Out Port 계약에 드러낼 때

Programmer Error, 불변식 위반과 복구 불가능한 환경 오류까지 무조건 `Either`로 바꾸는 것은 아니다. 호출자가 처리할 수 있는 예상된 실패를 값으로 만들 때 가장 유용하다.

## 직접 구현하지 않고 Vavr를 사용한다

Production에서는 검증되지 않은 자체 `Either`를 만들기보다 Vavr의 `io.vavr.control.Either`를 사용한다. 직접 구현하면 Variance, Stack Safety, `sequence`, `traverse`와 Law 검증까지 책임져야 한다.

```java
import io.vavr.control.Either;

Either<BookingError, Booking> result = Either.right(booking);

Either<BookingError, Booking> failure = Either.left(
    new BookingError.NotFound(bookingId)
);
```

`map`은 성공값의 타입을 바꾸고, `flatMap`은 다음 실패 가능한 연산을 연결한다. `mapLeft`는 Error를 상위 계층의 Error로 변환한다.

## Hexagonal Architecture에서의 경계

FMS 스타일에서는 Domain Model이 자신의 규칙을 갖고, Application Service가 흐름을 조율하며, 외부 실패는 Port의 `Either`로 받는다.

```text
Web Adapter -> In Port -> Application Service -> Out Port -> Persistence Adapter
```

### Error를 문자열로 만들지 않는다

문자열 Error는 Compiler가 종류를 구분할 수 없고 필드도 잃는다. 업무 의미가 있는 Sealed Interface로 정의한다.

```java
public sealed interface BookingError {

    record NotFound(long bookingId) implements BookingError {
    }

    record AlreadyCancelled(long bookingId) implements BookingError {
    }

    record PersistenceFailure(long bookingId, Throwable cause) implements BookingError {
    }
}
```

### Out Port

```java
public interface BookingPort {

    Either<BookingError, Booking> findById(long bookingId);

    Either<BookingError, Booking> save(Booking booking);
}
```

### Persistence Adapter

Database Driver가 던진 예외는 Adapter에서 업무 Error로 바꾼다. `Try`는 던져진 예외를 잡는 경계, `Either`는 이후 Application 흐름의 계약이다.

```java
@Component
@RequiredArgsConstructor
public class BookingPersistenceAdapter implements BookingPort {

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

### Domain Model

Domain은 영속성 예외를 알지 않는다. 상태 변경 가능 여부를 의미 있는 Method로 검사하고 새 상태를 만든다.

```java
@Getter
@Builder(access = AccessLevel.PRIVATE)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
public final class Booking {

    private final long id;
    private final BookingStatus status;
    private final Audit audit;

    public static Booking load(long id, BookingStatus status, Audit audit) {
        return Booking.builder()
                      .id(id)
                      .status(status)
                      .audit(audit)
                      .build();
    }

    public Either<BookingError, Booking> cancel(AuditActor actor) {
        return Either.cond(
            status != BookingStatus.CANCELLED,
            () -> Booking.builder()
                         .id(id)
                         .status(BookingStatus.CANCELLED)
                         .audit(audit.updatedBy(actor))
                         .build(),
            () -> new BookingError.AlreadyCancelled(id)
        );
    }
}
```

### Application Service

Controller가 호출하는 최상위 Service는 `Either`를 반환하지 않는다. Domain과 Out Port의 `Either`를 합성한 뒤 구체적인 Application Exception으로 변환한다. 각 단계의 세부 규칙은 Domain과 Adapter에 둔다.

```java
@Service
@RequiredArgsConstructor
public class CancelBookingService implements CancelBookingUseCase {

    private final BookingPort bookingPort;
    private final AuditActorResolver auditActorResolver;
    private final BookingExceptionMapper exceptionMapper;

    @Override
    public BookingResource cancel(CancelBookingCommand command) {
        return bookingPort.findById(command.bookingId())
                          .flatMap(booking -> booking.cancel(auditActorResolver.currentActor()))
                          .flatMap(bookingPort::save)
                          .map(BookingResource::from)
                          .getOrElseThrow(exceptionMapper::toException);
    }
}
```

중간에 `Left`가 생기면 이후 `flatMap`과 `map`은 실행되지 않는다. Service의 마지막 경계에서 `BookingNotFoundException`, `BookingAlreadyCancelledException`처럼 Controller Advice가 처리할 예외로 바뀐다.

## 여러 결과 합치기

`List<Either<E, T>>`를 그대로 반환하면 호출자가 각 원소를 풀어야 한다. 하나라도 실패하면 전체를 실패시키는 경우 `sequence`를 사용한다. Vavr Collection을 Domain Collection으로 노출하지 않기 위해 마지막에 `java.util.List`로 바꾼다.

```java
public Either<BookingError, List<Booking>> loadAll(List<Long> bookingIds) {
    return Either.sequence(
                     bookingIds.stream()
                               .map(bookingPort::findById)
                               .toList()
                 )
                 .map(values -> values.toJavaList());
}
```

모든 검증 Error를 한꺼번에 모아야 한다면 Fail-fast인 `Either`보다 Vavr `Validation`이 맞다.

## 경계에서 HTTP 응답으로 변환하기

Domain Error를 Controller에서 `fold()`하거나 `instanceof`로 분기하지 않는다. Service가 Application Exception을 던지고 전역 Exception Handler가 HTTP 의미로 변환한다.

```java
@RestController
@RequiredArgsConstructor
public class BookingController {

    private final CancelBookingUseCase cancelBookingUseCase;
    @PostMapping("/bookings/{bookingId}/cancellation")
    public ResponseEntity<BookingResponse> cancel(@PathVariable long bookingId) {
        BookingResource resource = cancelBookingUseCase.cancel(
            new CancelBookingCommand(bookingId)
        );
        return ResponseEntity.ok(BookingResponse.from(resource));
    }
}
```

```java
@RestControllerAdvice
public class BookingExceptionHandler {

    @ExceptionHandler(BookingNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(BookingNotFoundException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.NOT_FOUND,
            exception.getMessage()
        );
        problem.setProperty("code", "BOOKING_NOT_FOUND");
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
    }
}
```

## 자주 하는 실수

- `Either<String, T>`로 Error 구조를 잃는다.
- `get()`으로 강제로 꺼내 `Either`의 안전성을 없앤다.
- 모든 Method를 `Either<Exception, T>`로 만들어 업무 실패 종류를 감춘다.
- 최상위 Service나 In Port가 `Either`를 반환해 Controller까지 Domain Error를 노출한다.
- Controller가 `fold()`로 Error를 HTTP 응답으로 직접 Mapping한다.
- `peek`에서 State를 변경해 Pipeline의 결과를 예측하기 어렵게 만든다.
- Domain, Port와 Controller가 같은 Error 타입을 공유해 계층 경계를 흐린다.

## 기억할 점

`Either`의 목적은 `try-catch` 문법을 없애는 것이 아니라 Domain과 Out Port 실패를 함수 합성이 가능한 계약으로 만드는 것이다. 최상위 Service는 그 계약을 소비해 Application Exception으로 바꾸고, Controller Advice가 HTTP 응답을 책임진다.

# Reference

- [Vavr Either](https://docs.vavr.io/#_either)
