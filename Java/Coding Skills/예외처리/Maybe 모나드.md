---
id: Maybe 모나드
started: 2025-12-29
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
  - "[[Functional Programming]]"
---

# Maybe 모나드와 Java Optional

Maybe는 값이 있는 `Just<T>`와 없는 `Nothing`을 하나의 타입으로 표현한다. Java 표준 Library에서는 같은 목적에 `Optional<T>`을 사용한다. FMS 스타일에서는 Vavr `Option`을 추가하지 않고 `java.util.Optional`을 사용해 Collection·Framework와의 상호 운용 비용을 줄인다.

## 핵심 연산

| 연산 | 역할 |
|---|---|
| `ofNullable` | `null`일 수 있는 Legacy 값을 경계에서 감싼다. |
| `map` | 값이 있을 때 `T -> U` 변환을 적용한다. |
| `flatMap` | 값이 있을 때 `T -> Optional<U>`를 적용하고 중첩을 제거한다. |
| `filter` | Predicate를 만족하지 않으면 빈 값으로 만든다. |
| `or` | 비어 있을 때 다음 Optional Supplier를 평가한다. |
| `orElseGet` | 비어 있을 때만 대체값을 계산한다. |
| `stream` | 0개 또는 1개 값을 Stream Pipeline에 연결한다. |

## 실무 예제: 연락처 선택

Passenger는 여러 연락처를 가질 수 있고 Primary Email이 없으면 Center 기본 Email을 사용한다.

```java
public record Contact(
    ContactType type,
    String value,
    boolean primary,
    boolean verified
) {
}

public Optional<EmailAddress> resolveNotificationEmail(
    Passenger passenger,
    CenterPolicy centerPolicy
) {
    return passenger.contacts()
                    .stream()
                    .filter(contact -> contact.type() == ContactType.EMAIL)
                    .filter(Contact::primary)
                    .filter(Contact::verified)
                    .map(Contact::value)
                    .map(EmailAddress::parse)
                    .findFirst()
                    .or(centerPolicy::defaultNotificationEmail);
}
```

`findFirst`는 Encounter Order에 의존한다. Primary Contact가 여러 개 생길 수 없다면 Domain 생성 시 불변식을 검증해야 한다.

## 부재를 업무 Error로 승격하기

Optional은 이유를 보존하지 않는다. Use Case에서 값이 반드시 필요하면 `Either`로 바꾼다.

```java
public Either<NotificationError, EmailAddress> requireNotificationEmail(
    Passenger passenger,
    CenterPolicy centerPolicy
) {
    return resolveNotificationEmail(passenger, centerPolicy)
        .<Either<NotificationError, EmailAddress>>map(Either::right)
        .orElseGet(() -> Either.left(
            new NotificationError.EmailUnavailable(passenger.getId())
        ));
}
```

## 중첩 구조 평탄화

Legacy Model의 Getter가 `null`을 반환해도 Adapter 경계에서만 `ofNullable`로 받아 Domain에는 유효한 Value를 넘긴다.

```java
public Optional<String> resolveCity(LegacyBooking booking) {
    return Optional.ofNullable(booking)
                   .map(LegacyBooking::getPassenger)
                   .map(LegacyPassenger::getAddress)
                   .map(LegacyAddress::getCity)
                   .map(String::trim)
                   .filter(city -> !city.isEmpty());
}
```

`map`은 Mapper가 `null`을 반환하면 빈 Optional로 바꾼다. 새 Domain Model에서는 Field 자체가 유효하도록 생성 시점에 검증하는 편이 낫다.

## 여러 Optional을 조합하기

두 값이 모두 필요할 때 중첩 `flatMap`을 길게 쓰기보다 의미 있는 Domain Factory로 조합한다.

```java
public Optional<PickupAssignment> createAssignment(
    Optional<Driver> driver,
    Optional<Vehicle> vehicle
) {
    return driver.flatMap(assignedDriver ->
        vehicle.map(assignedVehicle -> PickupAssignment.of(assignedDriver, assignedVehicle))
    );
}
```

독립적인 Field 검증 Error를 모두 모아야 한다면 Optional이 아니라 `Validation.combine`을 사용한다.

## Collection과 함께 사용하기

```java
List<DeviceToken> activeTokens = passengers.stream()
                                           .map(Passenger::pushToken)
                                           .flatMap(Optional::stream)
                                           .filter(DeviceToken::active)
                                           .distinct()
                                           .toList();
```

`Optional<List<T>>`는 만들지 않는다. 0개 이상은 빈 `List<T>`로 표현하고, 여러 객체의 선택적 단일 값만 `Optional::stream`으로 평탄화한다.

## Maybe Law를 실무적으로 이해하기

- `map(identity())`는 원래 Optional과 같아야 한다.
- `flatMap(Optional::of)`는 원래 Optional과 같아야 한다.
- Mapper는 입력 Optional을 바꾸거나 외부 State를 변경하지 않는 편이 합성에 안전하다.

Side Effect가 Mapper 안에 있으면 값이 비어 있을 때 실행되지 않고, Pipeline 구조 변경에 따라 실행 횟수가 달라진다. 필수 저장과 Message 발행은 명시적인 Service 단계로 둔다.

## 피해야 할 사용

- JPA Entity·DTO·Domain Field에 `Optional` 저장
- Method Parameter로 `Optional` 전달
- `Optional<List<T>>` 반환
- `isPresent()` 뒤 `get()` 호출
- 업무 실패 이유를 Optional의 빈 값으로 손실
- `orElse(expensiveCall())`로 불필요한 외부 호출 실행
- Optional Pipeline 안에서 Repository를 반복 호출

## 기억할 점

Maybe의 가치는 `null`을 Container로 감싸는 데 있지 않다. 값의 부재를 Method Signature에 드러내고, `map`과 `flatMap`으로 안전하게 합성하는 데 있다. Java에서는 표준 `Optional`을 사용하고, 부재가 업무 실패가 되는 경계에서 `Either`로 변환한다.

# Reference

- [Java Optional](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Optional.html)
