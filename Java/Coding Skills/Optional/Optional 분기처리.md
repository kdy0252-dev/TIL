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

Optional은 `null`을 완전히 없애는 도구가 아니다. 값이 없을 수 있는 지점에서 `Optional.empty()`를 만들고, 호출자가 기본값·예외·대체 조회 중 하나를 명시적으로 선택하도록 만드는 도구다.
## isPresent()를 사용한 분기 처리
Optional 객체에 값이 있는지 확인하고, 값이 있을 때만 특정 코드를 실행할 수 있다.

```java title="Optional에 값이 있는 경우만 람다 함수 실행"
Optional<Account> account = findAccount();
account.ifPresent(existingAccount -> existingAccount.changeAmount(1000));
```
위 예시에서 `ifPresent()` 메서드는 Optional 객체에 값이 있을 때만 람다 함수를 실행한다.
## isPresent()와 함께 null 체크
`ofNullable()` 메서드를 사용하면 null 값을 Optional 객체로 감쌀 수 있다. 이를 통해 null 체크와 함께 `ifPresent()`를 사용할 수 있다.
```java title="null 체크와 함께 사용"
findAccount()
    .ifPresent(account -> account.changeAmount(1000));
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
Account account = findAccount()
        .orElse(new Account("default", 0));
```
위 예시에서 `orElse()` 메서드는 Optional 객체에 값이 없으면 새로운 Account 객체를 생성하여 반환한다.
## orElseGet()을 사용한 지연된 기본값 설정
`orElseGet()` 메서드를 사용하면 Optional 객체에 값이 없을 때만 Supplier 함수를 실행하여 기본값을 설정할 수 있다.

```java title="orElseGet()을 사용한 지연된 기본값 설정"
Account account = findAccount()
        .orElseGet(() -> new Account("default", 0));
```

위 예시에서 `orElseGet()` 메서드는 Optional 객체에 값이 없을 때만 새로운 Account 객체를 생성하여 반환한다. `orElse()`와 달리 Supplier 함수를 사용하므로, 기본값 생성 비용이 비쌀 경우에 유용하다.

`orElse()`의 인자는 Optional에 값이 있어도 먼저 평가된다.

```java
Account account = existingAccount.orElse(loadDefaultAccount());
// existingAccount에 값이 있어도 loadDefaultAccount()가 호출된다.

Account lazyAccount = existingAccount.orElseGet(this::loadDefaultAccount);
// 값이 없을 때만 호출된다.
```

대체 값이 상수처럼 이미 존재하면 `orElse`, Query·File I/O·객체 생성이 필요하면 `orElseGet`을 사용한다.
## orElseThrow()를 사용한 예외 발생
`orElseThrow()` 메서드를 사용하면 Optional 객체에 값이 없을 때 예외를 발생시킬 수 있다.

```java title="orElseThrow()를 사용한 예외 발생"
Account account = findAccount()
        .orElseThrow(() -> new IllegalArgumentException("Account not found"));
```
위 예시에서 `orElseThrow()` 메서드는 Optional 객체에 값이 없으면 IllegalArgumentException 예외를 발생시킨다.
## stream()을 사용한 Optional 처리
Java 9부터는 Optional 객체를 Stream으로 변환하여 처리할 수 있다. 이를 통해 Optional 객체가 비어있을 경우 빈 스트림을 반환하고, 값이 있을 경우 해당 값을 포함하는 스트림을 반환한다.
```java title="stream()을 사용한 Optional 처리"
Optional<Account> account = findAccount();
account.stream()
       .forEach(existingAccount -> existingAccount.changeAmount(1000));
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
        *   컬렉션 내에 Optional 객체가 여러 개 있을 경우 `flatMap(Optional::stream)`으로 존재하는 값만 추출할 수 있다.

## 값이 없을 때 다른 Optional 조회하기

Java 9의 `or()`는 첫 Optional이 비어 있을 때만 대체 Optional을 계산한다.

```java
Optional<Member> member = primaryRepository.findById(id)
    .or(() -> archiveRepository.findById(id));
```

`orElseGet()`은 `Member`를 반환하지만 `or()`는 `Optional<Member>`를 반환하는 Supplier를 받는 차이가 있다.

## filter로 값의 조건 표현하기

```java
Member activeMember = repository.findById(id)
    .filter(Member::isActive)
    .orElseThrow(() -> new MemberNotActiveException(id));
```

여기서는 “회원이 없음”과 “비활성 회원”이 같은 Empty 경로로 합쳐진다. 두 경우를 다른 오류로 알려야 한다면 Optional Chain보다 명시적인 Domain 분기가 더 정확하다.

## Side Effect와 ifPresent

`ifPresent()`는 반환값이 없는 Side Effect에 사용한다. Domain State 변경, 외부 Message 전송과 저장이 Chain 곳곳에 섞이면 실패 흐름을 추적하기 어렵다.

```java
repository.findById(id)
    .map(Member::email)
    .ifPresent(notificationSender::sendWelcome);
```

중요한 업무 흐름이라면 “없으면 아무것도 하지 않는다”가 올바른 정책인지 확인한다. Optional이 Error를 조용히 삼키는 도구가 되어서는 안 된다.

## Optional 자체가 null이면 안 된다

Optional 반환 Method는 `null` 대신 반드시 `Optional.empty()`를 반환해야 한다. `Optional<Optional<T>>`, Optional Field와 Optional Parameter는 대개 API를 더 복잡하게 만든다.

## 기억할 점

Optional 분기에서 중요한 것은 Method 이름을 외우는 것이 아니라 값이 없을 때의 업무 의미를 선택하는 것이다. 기본값, 대체 조회, 무시와 예외는 서로 다른 정책이며 호출부에서 분명히 보여야 한다.

# Reference
