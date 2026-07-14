---
id: Optional 사용 시 주의사항
started: 2025-04-25
tags:
  - Java
  - ✅DONE
group:
  - "[[Java Coding Skills]]"
---

# Optional 사용 시 주의사항

`Optional<T>`은 Method가 정상적으로 값을 찾지 못할 수 있음을 반환 타입에 표현한다. 실패 이유가 필요 없는 “0개 또는 1개”의 조회 결과에 적합하다. 모든 `null`을 감싸는 범용 Container는 아니다.

## 어떤 타입을 선택할까

| 상황 | 타입 |
|---|---|
| 값이 없을 수 있고 이유가 중요하지 않음 | `Optional<T>` |
| 성공 또는 구체적인 실패 이유 | `Either<E, T>` |
| 예외를 던지는 외부 호출 | `Try<T>` 후 경계에서 `Either` 변환 |
| 0개 이상 결과 | `List<T>` |
| 여러 입력 Error 누적 | `Validation<E, T>` |

## 반환 타입에 사용한다

```java
public interface PassengerQueryPort {

    Optional<Passenger> findByPhoneNumber(PhoneNumber phoneNumber);

    List<Passenger> findAllByCenterId(long centerId);
}
```

`findByPhoneNumber`의 부재는 정상적인 조회 결과일 수 있다. 반면 반드시 존재해야 하는 Use Case에서는 Service가 업무 Error로 바꾼다.

```java
public Either<PassengerError, PassengerResource> getPassenger(long passengerId) {
    return passengerPort.findById(passengerId)
                        .<Either<PassengerError, Passenger>>map(Either::right)
                        .orElseGet(() -> Either.left(new PassengerError.NotFound(passengerId)))
                        .map(PassengerResource::from);
}
```

## Field와 Parameter에 넣지 않는다

JPA Entity, DTO와 Domain Field에 `Optional`을 저장하면 Serialization과 Mapping 계약이 복잡해진다. Optional Parameter는 호출자가 Container를 만들어야 하고 Parameter 자체가 `null`일 가능성도 남는다.

```java
public record UpdatePassengerCommand(
    long passengerId,
    String displayName,
    PhoneNumber phoneNumber
) {
}
```

Patch API처럼 “전달하지 않음”과 “명시적으로 제거”를 구분해야 한다면 `Optional` Parameter로 얼버무리지 말고 `FieldUpdate<T>` 같은 명시적 Command 타입을 설계한다.

```java
public sealed interface FieldUpdate<T> {

    record Unchanged<T>() implements FieldUpdate<T> {
    }

    record Replace<T>(T value) implements FieldUpdate<T> {
    }

    record Clear<T>() implements FieldUpdate<T> {
    }
}
```

## Collection을 Optional로 감싸지 않는다

조회 결과가 없으면 빈 불변 Collection을 반환한다. `Optional<List<T>>`는 “Optional 없음”과 “빈 List”라는 중복 상태를 만든다.

```java
public List<BookingResource> findBookings(long passengerId) {
    return bookingPort.findAllByPassengerId(passengerId)
                      .stream()
                      .map(BookingResource::from)
                      .toList();
}
```

Port도 `null` 대신 `List.of()`를 반환한다는 계약을 지켜야 한다.

## `map`, `flatMap`과 `filter`

`map`의 Mapper가 `Optional<U>`를 반환하면 `Optional<Optional<U>>`가 되므로 `flatMap`을 사용한다.

```java
public Optional<PhoneNumber> resolvePrimaryPhone(Passenger passenger) {
    return Optional.ofNullable(passenger.contact())
                   .map(Contact::phoneNumbers)
                   .stream()
                   .flatMap(List::stream)
                   .filter(PhoneNumber::primary)
                   .findFirst();
}
```

중간 Getter가 `null`을 반환하는 Legacy Model이라면 경계를 Adapter로 한정하고 Domain 내부에는 유효한 Value Object를 전달한다.

## `orElse`와 `orElseGet`

`orElse`의 인자는 Optional에 값이 있어도 먼저 평가된다. Database 조회나 비싼 객체 생성은 `orElseGet`으로 지연한다.

```java
Passenger passenger = passengerPort.findByExternalId(externalId)
                                   .orElseGet(() -> passengerRegistration.register(externalId));
```

그러나 조회 후 생성은 동시 요청에서 중복 생성될 수 있다. Unique Constraint와 Upsert 또는 Transaction 재조회로 Race Condition을 처리해야 한다. `orElseGet`만으로 동시성 문제가 해결되지는 않는다.

## 여러 Optional 후보 연결하기

Java 9 이상의 `or`는 첫 번째 값이 없을 때만 다음 Supplier를 평가한다.

```java
public Optional<CenterPolicy> resolvePolicy(long centerId, Region region) {
    return policyPort.findByCenterId(centerId)
                     .or(() -> policyPort.findByRegion(region))
                     .or(policyPort::findGlobalDefault);
}
```

Fallback 우선순위가 업무 규칙이라면 Method 이름과 Test로 순서를 고정한다.

## Optional Stream

여러 객체에서 있을 수도 있는 값을 모을 때 `Optional::stream`이 유용하다.

```java
List<EmailAddress> recipients = passengers.stream()
                                          .map(Passenger::notificationEmail)
                                          .flatMap(Optional::stream)
                                          .distinct()
                                          .toList();
```

Stream 안에서 Repository를 호출하면 N+1 I/O가 생길 수 있다. 먼저 ID를 모아 Batch 조회하고 Memory에서 변환한다.

## Side Effect 분기

값 유무에 따른 Log 같은 선택적 Side Effect는 `ifPresentOrElse`로 표현할 수 있다. 핵심 Business Flow는 `Either`로 바꾸어 반환하는 편이 낫다.

```java
passengerPort.findById(passengerId)
             .ifPresentOrElse(
                 passenger -> auditLogger.found(passenger.getId()),
                 () -> auditLogger.notFound(passengerId)
             );
```

## Primitive Optional

대량 숫자 Stream의 단일 결과에는 `OptionalInt`, `OptionalLong`, `OptionalDouble`이 Boxing을 줄인다.

```java
OptionalLong maximumDistance = drivings.stream()
                                       .mapToLong(Driving::distanceMeters)
                                       .max();
```

Domain API의 가독성이 더 중요한 일반적인 단일 값 조회에서는 Boxing 비용을 먼저 추측하지 말고 Profile 결과로 결정한다.

## 자주 하는 실수

- `Optional` Field, DTO Field 또는 Method Parameter를 만든다.
- `Optional<List<T>>`와 `Optional<Map<K, V>>`를 반환한다.
- `isPresent()` 후 `get()`으로 다시 명령형 분기를 만든다.
- `orElse(expensiveCall())`로 값이 있어도 외부 호출을 실행한다.
- `Optional`이 없음을 업무 Error와 구분하지 않는다.
- `map` 안에서 `null`을 반환하거나 필수 Side Effect를 수행한다.
- Optional Chain 안에서 Repository를 반복 호출한다.

## 기억할 점

`Optional`은 반환값의 부재를 표현하는 좁은 도구다. Collection, 업무 실패와 Patch 의미를 대신하지 않는다. `map`·`flatMap`·`or`로 값의 흐름을 표현하되, 계층 경계에서는 부재를 업무 Error 또는 빈 Collection으로 올바르게 변환해야 한다.

# Reference

- [Java Optional](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Optional.html)
- Effective Java Item 55: 옵셔널 반환은 신중히 하라
