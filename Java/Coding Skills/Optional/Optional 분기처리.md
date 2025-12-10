---
id: Optional isPresent
started: 2025-04-24
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# Optional 분기 처리
## Optional이란?
Optional은 Java 8부터 도입된 클래스로, 값이 존재할 수도 있고 존재하지 않을 수도 있는 컨테이너 타입이다. NullPointerException을 방지하고 코드의 가독성을 높이는 데 사용된다.
## isPresent()를 사용한 분기 처리
Optional 객체에 값이 있는지 확인하고, 값이 있을 때만 특정 코드를 실행할 수 있다.

```java title="Optional에 값이 있는 경우만 람다 함수 실행"
Optional<Account> account = Optional.ofNullable(findAccount());
account.ifPresent(acc -> acc.setAmount(1000));
```
위 예시에서 `ifPresent()` 메서드는 Optional 객체에 값이 있을 때만 람다 함수를 실행한다.
## isPresent()와 함께 null 체크
`ofNullable()` 메서드를 사용하면 null 값을 Optional 객체로 감쌀 수 있다. 이를 통해 null 체크와 함께 `ifPresent()`를 사용할 수 있다.
```java title="null 체크와 함께 사용"
Optional.ofNullable(findAccount())
        .ifPresent(account -> account.setAmount(1000));
```
## ifPresentOrElse()를 사용한 분기 처리
`ifPresentOrElse()` 메서드를 사용하면 값이 있을 때와 없을 때 각각 다른 코드를 실행할 수 있다.
```java title="ifPresentOrElse()를 사용한 분기 처리"
Optional<User> user = Optional.ofNullable(findUser("example@example.com"));
user.ifPresentOrElse(
    existUser -> updateTokens(token, existUser),
    () -> saveUser("example@example.com"));
```
위 예시에서 `ifPresentOrElse()` 메서드는 Optional 객체에 값이 있으면 `updateTokens()` 메서드를 실행하고, 값이 없으면 `saveUser()` 메서드를 실행한다.
## orElse()를 사용한 기본값 설정
`orElse()` 메서드를 사용하면 Optional 객체에 값이 없을 때 기본값을 설정할 수 있다.
```java title="orElse()를 사용한 기본값 설정"
Account account = Optional.ofNullable(findAccount())
        .orElse(new Account("default", 0));
```
위 예시에서 `orElse()` 메서드는 Optional 객체에 값이 없으면 새로운 Account 객체를 생성하여 반환한다.
## orElseGet()을 사용한 지연된 기본값 설정
`orElseGet()` 메서드를 사용하면 Optional 객체에 값이 없을 때만 Supplier 함수를 실행하여 기본값을 설정할 수 있다.

```java title="orElseGet()을 사용한 지연된 기본값 설정"
Account account = Optional.ofNullable(findAccount())
        .orElseGet(() -> new Account("default", 0));
```

위 예시에서 `orElseGet()` 메서드는 Optional 객체에 값이 없을 때만 새로운 Account 객체를 생성하여 반환한다. `orElse()`와 달리 Supplier 함수를 사용하므로, 기본값 생성 비용이 비쌀 경우에 유용하다.
## orElseThrow()를 사용한 예외 발생
`orElseThrow()` 메서드를 사용하면 Optional 객체에 값이 없을 때 예외를 발생시킬 수 있다.

```java title="orElseThrow()를 사용한 예외 발생"
Account account = Optional.ofNullable(findAccount())
        .orElseThrow(() -> new IllegalArgumentException("Account not found"));
```
위 예시에서 `orElseThrow()` 메서드는 Optional 객체에 값이 없으면 IllegalArgumentException 예외를 발생시킨다.
## stream()을 사용한 Optional 처리
Java 9부터는 Optional 객체를 Stream으로 변환하여 처리할 수 있다. 이를 통해 Optional 객체가 비어있을 경우 빈 스트림을 반환하고, 값이 있을 경우 해당 값을 포함하는 스트림을 반환한다.
```java title="stream()을 사용한 Optional 처리"
Optional<Account> account = Optional.ofNullable(findAccount());
account.stream()
       .forEach(acc -> acc.setAmount(1000));
```
## 더 나은 Optional 활용을 위한 팁
*   Optional을 필드나 메서드 파라미터로 사용하는 것은 권장되지 않는다.
    *   **이유**:
        *   **필드**: 클래스의 상태를 나타내는 필드로 Optional을 사용하면, 클래스의 복잡성이 증가하고 직렬화/역직렬화 과정에서 문제가 발생할 수 있다. 또한, 필드가 Optional인 경우 항상 `isPresent()`를 사용하여 null 체크를 해야 하므로 번거롭다.
        *   **메서드 파라미터**: 메서드 파라미터로 Optional을 사용하면, 호출자가 항상 Optional 객체를 생성해서 전달해야 하므로 불필요한 오버헤드가 발생할 수 있다. 또한, 메서드 내부에서 Optional을 처리하는 로직이 추가되어 가독성이 떨어질 수 있다.
*   Optional은 반환 타입으로만 사용하는 것이 좋다.
    *   **이유**:
        *   메서드가 값을 반환하지 못할 경우, null 대신 Optional을 반환함으로써 호출자에게 "값이 없을 수 있음"을 명시적으로 알릴 수 있다. 이를 통해 호출자는 반환 값이 null인지 체크하는 대신 Optional API를 사용하여 안전하게 값을 처리할 수 있다.
*   컬렉션 내의 Optional 처리는 `stream()`을 활용하는 것이 좋다.
    *   **이유**:
        *   컬렉션 내에 Optional 객체가 여러 개 있을 경우, `stream()`을 사용하여 Optional 객체들을 필터링하고 값을 추출하는 것이 더 효율적이고 가독성이 좋다. 예를 들어, `map(Optional::stream).flatMap(Stream::of)`를 사용하여 Optional이 비어있지 않은 값만 추출할 수 있다.

# Reference