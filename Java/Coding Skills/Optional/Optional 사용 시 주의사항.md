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

Java 8부터 도입된 `Optional<T>`은 `null`을 직접 다루는 것보다 안전하고 명시적인 방법을 제공하지만, 잘못 사용하면 오히려 코드 복잡도를 높이고 성능을 저하시킬 수 있습니다. 올바른 사용법과 주의사항을 상세히 정리합니다.

## 1. Optional이란?
`Optional<T>`는 `null`이 될 수 있는 객체를 감싸는 Wrapper 클래스입니다.
- **주 목적**: 결과 없음(null)을 명확하게 표현하여 `NullPointerException`(NPE)을 방지하고, 클라이언트 코드에게 명시적으로 처리를 강제하는 것입니다.
- **설계 의도**: 메서드의 **반환 타입**으로 제한적으로 사용되도록 설계되었습니다.

---

## 2. 절대 하지 말아야 할 것 (Anti-Patterns)

### 1. 필드(멤버 변수)로 사용하지 말 것
`Optional`은 데이터를 저장하기 위한 용도가 아닙니다. 필드로 사용하면 직렬화(Serialization) 문제가 발생하고, 메모리 사용량이 불필요하게 증가합니다.

```java
// BAD: 직렬화 시 문제 발생 가능, 메모리 낭비
public class Member {
    private Optional<String> name; 
}

// GOOD: null을 허용하거나 별도의 null 처리 로직 사용
public class Member {
    private String name;
}
```

> **직렬화 문제**: `Optional` 클래스는 `Serializable` 인터페이스를 구현하지 않았습니다. 따라서 Jackson이나 Java 기본 직렬화를 사용할 때 예기치 않은 오류가 발생하거나, 비효율적인 JSON 형태(`{"present":true, ...}`)로 매핑될 수 있습니다.

### 2. 생성자나 메서드의 파라미터로 사용하지 말 것
파라미터로 `Optional`을 받으면 호출자가 `Optional.of`나 `Optional.empty()`로 감싸서 넘겨야 하므로 호출 코드가 지저분해집니다. 또한, 파라미터 자체가 `null`인 경우도 체크해야 하므로 복잡도가 증가합니다.

```java
// BAD
public void updateMember(Optional<String> name) {
    if (name != null && name.isPresent()) { ... }
}

// GOOD: 오버로딩을 사용하거나 null 체크를 내부에서 수행
public void updateMember(String name) {
    if (name != null) { ... }
}
```

### 3. 컬렉션을 Optional로 감싸지 말 것
`Optional<List<T>>`는 절대 사용하지 마세요. 컬렉션은 비어있음(`empty`)을 자체적으로 표현할 수 있습니다.

```java
// BAD
public Optional<List<String>> getNames() { ... }

// GOOD: 빈 리스트 반환 (Collections.emptyList())
public List<String> getNames() {
    return result != null ? result : Collections.emptyList();
}
```

### 4. 단지 null 체크를 위해 사용하지 말 것
`Optional`을 생성하고 `.get()`하는 비용은 단순 `null` 체크보다 훨씬 비쌉니다.

```java
// BAD
return Optional.ofNullable(user).orElse(defaultUser);

// GOOD
return user != null ? user : defaultUser;
```

---

## 3. 올바른 사용법 (Best Practices)

### 1. 반환 타입으로만 사용하세요
메서드가 값을 반환하지 못할 가능성이 있을 때만 `Optional`을 반환 타입으로 사용합니다.

### 2. `get()` 호출 전에는 반드시 `isPresent()`를 확인하거나, `orElse` 계열 메서드를 사용하세요
`get()`을 바로 호출하는 것은 `NoSuchElementException`을 발생시킬 수 있어 위험합니다. 가능한 `get()` 사용을 피하고 함수형 스타일로 처리하세요.

### 3. `orElse()` vs `orElseGet()` 구분하기
- `orElse(T other)`: 값이 있든 없든 **항상 실행**됩니다. 이미 생성된 상수나 값을 사용할 때 적합합니다.
- `orElseGet(Supplier<? extends T> other)`: 값이 **없을 때만 실행**됩니다. 객체 생성 비용이 비싸거나 연산이 필요한 경우 사용합니다.

```java
// BAD: 값이 있어도 createNewUser()가 실행되어 불필요한 DB 접근이나 객체 생성이 발생
User user = findUser().orElse(createNewUser());

// GOOD: 값이 없을 때만 실행됨
User user = findUser().orElseGet(() -> createNewUser());
```

### ✅ 4. Primitve Type은 전용 Optional 사용하기
`Optional<Integer>`, `Optional<Long>` 대신 `OptionalInt`, `OptionalLong`, `OptionalDouble`을 사용하면 Boxing/Unboxing 오버헤드를 줄일 수 있습니다.

---

## 4. Java 버전에 따른 변화

### Java 8
- `isPresent()`: 값 존재 여부 확인
- `ifPresent(Consumer)`: 값이 있으면 동작 수행
- `orElse()`, `orElseGet()`, `orElseThrow()`: 값 부재 시 처리
- `map()`, `flatMap()`, `filter()`: 스트림과 유사한 처리

### Java 9
- **`ifPresentOrElse(Consumer, Runnable)`**: 값이 있으면 Consumer, 없으면 Runnable 실행 (매우 유용)
- `or(Supplier)`: 값이 없을 때 다른 Optional로 대체
- `stream()`: Stream으로 자동 변환

### Java 10
- `orElseThrow()`: 인자 없이 사용 가능 (`NoSuchElementException` 발생). `get()`보다 명시적이라 권장됨.

---

## 5. 상세 활용 예제

### Map과 FlatMap 활용
중첩된 객체 구조에서 `null` 안전하게 값 꺼내기.

```java
// Before: 지옥의 null 체크
if (order != null) {
    Member member = order.getMember();
    if (member != null) {
        Address address = member.getAddress();
        if (address != null) {
            return address.getCity();
        }
    }
}

// After: Optional 활용
return Optional.ofNullable(order)
    .map(Order::getMember)
    .map(Member::getAddress)
    .map(Address::getCity)
    .orElse("Unknown");
```

### ifPresentOrElse 사용 (Java 9+)
값이 있을 때와 없을 때의 로직을 깔끔하게 분기 처리.

```java
Optional<User> userOpt = findUser(id);

// Java 8 Style
if (userOpt.isPresent()) {
    log.info("User found: " + userOpt.get());
} else {
    log.warn("User not found");
}

// Java 9+ Style
userOpt.ifPresentOrElse(
    user -> log.info("User found: " + user),
    () -> log.warn("User not found")
);
```

### 빈 컬렉션 처리와 Stream 연결
Optional이 비어있으면 빈 스트림으로 처리하여 로직을 이어갈 수 있습니다.

```java
List<String> items = getOptionalList() // Optional<List<String>> 반환 가정
    .stream() // Java 9 method: Stream<List<String>>
    .flatMap(List::stream) // List<String> -> Stream<String>
    .collect(Collectors.toList());
```

## 6. 결론
> "Optional은 리턴 타입으로 사용되도록 설계되었다. 메서드 인자, 맵의 키, 인스턴스 필드 등으로 사용하는 것은 설계 의도에 어긋나며 성능상 이점도 없다."
> — Brian Goetz (Java Language Architect)

- **Optional은 비싸다**: 객체 생성 비용이 듭니다. 성능이 매우 중요한 루프 안에서는 `null` 체크가 나을 수 있습니다.
- **가독성을 위해 사용하라**: 복잡한 null 체크를 줄이고 의도를 명확히 할 때 빛을 발합니다.
- **직렬화를 피하라**: DTO나 엔티티(Entity)에는 사용하지 마세요. 반환 값(Return Value)으로만 사용하세요.

# Reference
- [Java SE 8 Optional Javadoc](https://docs.oracle.com/javase/8/docs/api/java/util/Optional.html)
- [Effective Java Item 55: 옵셔널 반환은 신중히 하라]
- [Toss Tech One: Optional 제대로 활용하기]