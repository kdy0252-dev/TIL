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

`Assert` 클래스를 사용하면 null 값 또는 비어 있는 값에 대한 검사를 간편하게 수행하고, 특정 조건이 만족되지 않을 경우 예외를 발생시킬 수 있습니다.

## IllegalArgumentException 처리

```java title="Assert.notEmpty로 IllegalArgumentException을 발생 시킬 수 있다."
import org.springframework.util.Assert;

Assert.notEmpty(email, "email must not be empty");
```

`Assert.notEmpty()` 메서드는 문자열, 컬렉션, 배열 등이 비어 있지 않은지 확인합니다. 만약 비어 있다면, `IllegalArgumentException`이 발생합니다. 두 번째 인자는 예외 발생 시 출력할 메시지입니다.

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

# Reference