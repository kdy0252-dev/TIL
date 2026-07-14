---
id: Assert로 Null Check
started: 2025-04-25
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# Assert로 Null Check

## Assert를 사용한 Null Check

Spring의 `Assert`는 Method 내부의 전제 조건과 객체 상태를 빠르게 검증하는 Utility다. Java의 `assert` Keyword와 다르며 JVM Option으로 꺼지지 않는다. 조건이 맞지 않으면 항상 Exception을 던진다.

## IllegalArgumentException 처리

```java title="문자열 입력 검증"
import org.springframework.util.Assert;

Assert.hasText(email, "email must not be blank");
```

`hasText()`는 `null`, 빈 문자열과 공백만 있는 문자열을 거부한다. Collection에는 `notEmpty()`, 단순 객체에는 `notNull()`을 사용한다.

```java
Assert.notNull(memberId, "memberId must not be null");
Assert.notEmpty(items, "items must not be empty");
```

## Assert의 다른 값 체크 함수

다음은 `Assert` 클래스에서 제공하는 다양한 값 체크 함수들입니다.

- isTrue: 조건이 참인지 확인
- isNull: 객체가 null인지 확인
- hasLength: 문자열의 길이가 0보다 큰지 확인
- hasText: 문자열에 내용이 있는지 확인 (공백 제외)
- noNullElements: 배열에 null 요소가 없는지 확인
- isInstanceOf: 객체가 특정 클래스의 인스턴스인지 확인
- isAssignable: 특정 클래스를 할당할 수 있는지 확인
- state: 객체의 상태가 유효한지 확인

>[!INFO] `state(boolean, String)` 함수를 사용하면 `IllegalStateException`을 발생시킬 수 있습니다.

## Argument와 State를 구분하기

```java
Assert.isTrue(amount.signum() > 0, "amount must be positive");
Assert.state(order.isPayable(), "order is not payable");
```

Caller가 잘못된 Argument를 전달한 경우 `IllegalArgumentException`, 객체의 현재 상태 때문에 작업할 수 없는 경우 `IllegalStateException`이 의미에 맞다.

## API 입력 검증과는 목적이 다르다

Controller Request 검증에는 Bean Validation을 사용하는 편이 좋다.

```java
record CreateMemberRequest(
    @NotBlank @Email String email
) {}
```

Bean Validation은 Field별 오류, 국제화와 일관된 400 Response를 만들기 쉽다. Spring `Assert` Exception을 그대로 외부에 노출하면 내부 메시지와 500 Response가 나갈 수 있다. Assert는 주로 내부 Programming Contract에 사용하고 업무 규칙 위반은 의미 있는 Domain Exception으로 표현한다.

## Objects.requireNonNull과 비교

`Objects.requireNonNull()`은 Null 하나를 검사하며 `NullPointerException`을 던진다. Constructor에서 필수 Dependency를 확인하는 단순한 경우에 적합하다. Spring `Assert`는 Text, Collection, Type과 State 등 더 다양한 조건을 제공하지만 Spring 의존성이 Domain Model까지 퍼지는 Trade-off가 있다.

## 기억할 점

Assert는 복잡한 업무 Validation Framework가 아니다. 호출자가 반드시 지켜야 할 전제와 개발 과정의 잘못된 상태를 Fail-fast로 드러내는 도구다. 사용자 입력, 업무 오류와 내부 불변식을 같은 Exception으로 처리하지 않는다.

# Reference
