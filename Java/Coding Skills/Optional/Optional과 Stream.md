---
id: Optional과 Stream
started: 2025-03-06
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# Optional과 Stream을 함께 사용하는 이유

`Optional<T>`는 값이 없을 수 있다는 사실을 반환 Type으로 표현한다. `Stream<T>`은 0개 이상의 값을 변환하는 Pipeline이다. Java 9의 `Optional.stream()`은 “0개 또는 1개”인 Optional을 Stream Pipeline에 자연스럽게 연결한다.

Optional의 목적은 모든 `null`을 감싸는 것이 아니라 **결과가 없을 수 있는 API 계약을 호출자가 무시하지 못하게 하는 것**이다.

## Optinal Chaining
### 값이 있는지 체크
```java title="Optional Chaining 예시"
public String getTeamNameFromDevice(Optional<Device> optionalDevice) {
    return optionalDevice
        .map(Device::getOwner)
        .map(User::getTeam)
        .map(Team::getName)
        .orElseThrow(() -> new IllegalStateException("team was not found"));
}
```
Optional Chaining은 Optional 객체 내에 값이 존재하는지 확인하고, 값이 존재할 경우에만 다음 메서드를 실행하는 방식이다. 위 예시에서는 `optDevice`가 `Device` 객체를 가지고 있다면, `getOwner()`, `getTeam()`, `getName()` 메서드를 순차적으로 호출하여 팀 이름을 반환한다. 만약 `optDevice`가 비어있거나 중간에 null 값이 발생하면 `orElseThrow()` 메서드를 통해 `IllegalStateException` 예외를 발생시킨다.
### 조건을 만족할때 동작
```java title="Optional로 특정 변수에 값이 있다면 동작을 수행시킬 수 있다."
Optional<Member> member = Optional.ofNullable(id)
    .flatMap(service::findById);
```
`findById()`가 이미 `Optional<Member>`를 반환한다면 `flatMap()`을 사용한다. 먼저 `existsById()`를 호출하면 같은 Row를 두 번 조회하고 두 호출 사이에 Data가 바뀔 수도 있다. 한 번의 조회 결과로 존재 여부와 값을 함께 표현한다.

## map과 flatMap의 차이

```text
map:     T -> R
flatMap: T -> Optional<R>
```

```java
Optional<Optional<Member>> nested = optionalId.map(service::findById);
Optional<Member> flat = optionalId.flatMap(service::findById);
```

`map()`의 Mapper가 `null`을 반환하면 결과는 Empty Optional이 된다. 하지만 Mapper가 Optional을 반환하면 Optional이 중첩되므로 `flatMap()`이 필요하다.
## Method Chaining
### Stream으로 Map 생성하기
```java title="Stream으로 Map 생성하기"
Map<String, ValueDto> newList  
    = list.stream()  
                 .collect(Collectors.toMap(  
                     this::getKey,  
                     this::generateValue  
                 ));
```
**설명:**
Stream을 사용하여 List를 Map으로 변환하는 예시이다. `stream()` 메서드를 통해 List를 Stream으로 변환하고, `collect()` 메서드를 사용하여 Stream의 각 요소를 key-value 쌍으로 변환하여 Map으로 수집한다. `Collectors.toMap()` 메서드는 key와 value를 생성하는 함수를 인자로 받는다.
*   `this::getKey`: Stream의 각 요소에서 key를 추출하는 메서드 레퍼런스이다.
*   `this::generateValue`: Stream의 각 요소에서 value를 생성하는 메서드 레퍼런스이다.
**추가 설명:**
Stream을 사용하면 데이터를 변환하고 수집하는 다양한 작업을 간결하게 표현할 수 있다. `map()`, `filter()`, `reduce()` 등 다양한 메서드를 사용하여 데이터를 처리할 수 있으며, `collect()` 메서드를 사용하여 결과를 List, Map, Set 등 다양한 형태로 수집할 수 있다.
### Optional을 Stream으로 변환하기
Java 9부터는 Optional 객체를 Stream으로 변환할 수 있다. 이를 통해 Optional 객체가 값을 가지고 있을 때만 Stream 연산을 수행할 수 있다.
```java title="Optional을 Stream으로 변환하는 예시"
Optional<EmailAddress> email = passenger.notificationEmail();
Stream<EmailAddress> stream = email.stream();
```
만약 Optional이 비어있다면, `stream()` 메서드는 빈 Stream을 반환한다. 이를 통해 NullPointerException을 방지하고 안전하게 Stream 연산을 수행할 수 있다.
### Stream에서 Optional로 변환하기
Stream에서 특정 조건을 만족하는 첫 번째 요소를 Optional로 반환할 수 있다.
```java title="Stream에서 Optional로 변환하는 예시"
Optional<Booking> latestCompletedBooking = bookings.stream()
                                                     .filter(Booking::isCompleted)
                                                     .max(Comparator.comparing(Booking::completedAt));
```
`findFirst()` 메서드는 Stream에서 첫 번째 요소를 Optional로 반환한다. 만약 Stream이 비어있다면, 빈 Optional을 반환한다.

## Optional 목록에서 존재하는 값만 꺼내기

```java
List<Optional<Member>> candidates = findCandidates();

List<Member> members = candidates.stream()
    .flatMap(Optional::stream)
    .toList();
```

각 Optional은 값이 있으면 요소 하나, 없으면 요소 0개의 Stream이 된다. `flatMap()`이 이를 하나의 `Stream<Member>`로 합친다.

Java 8에서는 다음처럼 표현할 수 있지만 Java 9 이상에서는 `Optional::stream`이 의도를 더 잘 드러낸다.

```java
.filter(Optional::isPresent)
.map(Optional::get)
```

## Stream Pipeline 안에서 Repository를 호출할 때

```java
// ID마다 Repository를 호출하지 않고 Batch 조회한다.
List<Passenger> passengers = passengerPort.findAllByIds(passengerIds);
```

표현은 간결하지만 ID 수만큼 Query가 실행될 수 있다. `findAllById(ids)`처럼 Bulk Query가 가능하면 Database 왕복을 줄이는 편이 낫다. 함수형 표현이 I/O 비용을 자동으로 최적화하지는 않는다.

## Optional을 반환해야 하는 경우

- 조회 결과가 정상적으로 없을 수 있다.
- Caller가 없음에 대한 정책을 결정해야 한다.
- `null`과 실제 값의 경계를 API에서 명확히 하고 싶다.

반대로 Collection은 값이 없으면 빈 Collection을 반환하면 되므로 `Optional<List<T>>`가 필요하지 않은 경우가 많다. Method Parameter와 Entity Field에 Optional을 사용하면 Framework 호환성과 호출부가 복잡해질 수 있다.

## 기억할 점

Optional과 Stream을 함께 쓰는 목적은 Null Check 문법을 숨기는 것이 아니다. 값이 없을 수 있는 계산을 Type으로 유지하다가, 여러 결과를 처리하는 경계에서 0개 또는 1개의 Stream으로 자연스럽게 펼치는 것이다.

# Reference
[Optional Chaining](https://velog.io/@hksdpr/JAVA-Optional%EC%9D%98-%EC%B6%A9%EA%B2%A9%EC%A0%81%EC%9D%B8-%EC%82%AC%EC%9A%A9%EB%B2%95-map%EC%9D%84-%EC%9D%B4%EC%9A%A9%ED%95%9C-%EC%B2%B4%EC%9D%B4%EB%8B%9D)
