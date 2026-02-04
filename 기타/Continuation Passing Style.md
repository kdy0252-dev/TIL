---
id: Continuation Passing Style (CPS)
started: 2026-02-04
tags:
  - Functional-Programming
  - Architecture
  - Design-Pattern
group:
  - "[[Computer Science]]"
---

# Continuation Passing Style (CPS) 가이드

## 1. 개요 (Overview)
**Continuation Passing Style (CPS)**는 프로그램의 제어 흐름을 명시적으로 함수에 전달하는 프로그래밍 스타일이다. 일반적인 함수가 작업을 마친 후 호출자에게 값을 반환(Return)하는 것과 달리, CPS에서는 "다음에 수행할 작업"을 담은 함수인 **Continuation**(연속체)을 인자로 받아, 작업이 끝나면 이를 호출함으로써 제어를 넘긴다.

함수형 프로그래밍의 핵심 개념 중 하나이며, 비동기 프로그래밍, 예외 처리, 컴파일러 최적화 등에 광범위하게 활용된다.

---

## 2. Direct Style vs Continuation Passing Style

### 2.1 Direct Style (일반적인 방식)
함수가 값을 계산하고 스택을 통해 호출자에게 결과값을 돌려주는 방식이다.

```java
public int add(int a, int b) {
    return a + b; // 직접 결과를 반환
}

int result = add(10, 20);
System.out.println(result); // 반환받은 후 다음 작업 수행
```

### 2.2 CPS (Continuation 방식)
함수가 결과값을 반환하지 않는다. 대신 결과를 가지고 수행할 **함수(Continuation)**를 인자로 받아서 실행한다.

```java
public void addCPS(int a, int b, Consumer<Integer> continuation) {
    continuation.accept(a + b); // 결과를 다음 작업(continuation)에 넘김
}

addCPS(10, 20, result -> {
    System.out.println(result); // 여기서 다음 작업이 일어남
});
```

---

## 3. CPS의 특징과 장점

### 3.1 명시적인 제어 흐름 (Explicit Control Flow)
CPS에서는 루프(`for`, `while`), 조건문(`if`), 예외 처리(`try-catch`) 등의 제어 구조를 모두 함수의 호출로 대체할 수 있다. 이는 제어 흐름을 데이터처럼 다룰 수 있게 하며, 프로그램의 실행 과정을 선형적으로 추적하기 쉽게 만든다.

### 3.2 꼬리 재귀 최적화 (Tail Call Optimization, TCO)
CPS로 작성된 코드는 본질적으로 **Tail Call** 형태를 띤다. 함수가 마지막에 다른 함수(Continuation)를 호출하며 종료되기 때문에, 호출 스택(Stack Frame)을 유지할 필요가 없다. 
- JVM 자체는 TCO를 강제하지 않지만, CPS 스타일을 활용하면 **Trampolining** 기법을 통해 스택 오버플로우 없이 깊은 재귀를 구현할 수 있다.

### 3.3 비동기 프로그래밍의 이론적 기초
우리가 흔히 사용하는 `Callback` 패턴이나 JavaScript의 `Promise.then()`은 CPS의 구체적인 구현체이다. 비동기 작업이 완료된 후 수행될 로직을 Continuation으로 넘겨줌으로써 Non-blocking 처리를 가능하게 한다.

---

## 4. 고급 활용 예시

### 4.1 복합 계산 (Composition)
CPS를 사용하면 여러 단계를 거치는 계산을 체이닝할 수 있다.

```java
// Vavr를 사용한 선언형 CPS 스타일 예시
public <T, R> Function<Consumer<R>, Void> mapCPS(T value, Function<T, R> mapper) {
    return continuation -> {
        R result = mapper.apply(value);
        continuation.accept(result);
        return null;
    };
}

// 10에 2를 곱하고, 그 결과에 5를 더하는 흐름
addCPS(10, 10, res1 -> 
    addCPS(res1, 5, res2 -> 
        System.out.println("Final Result: " + res2)
    )
);
```

### 4.2 예외 처리 (Success & Failure Continuation)
CPS를 확장하여 성공 시와 실패 시의 Continuation을 각각 전달함으로써 우아한 에러 핸들링이 가능하다.

```java
public void divideCPS(int a, int b, 
                      Consumer<Integer> onSuccess, 
                      Consumer<Throwable> onFailure) {
    try {
        onSuccess.accept(a / b);
    } catch (Exception e) {
        onFailure.accept(e);
    }
}

divideCPS(10, 0,
    res -> System.out.println("Result: " + res),
    err -> System.err.println("Error: " + err.getMessage())
);
```

---

## 5. CPS와 컴파일러 최적화
현대의 많은 컴파일러(예: GHC, Kotlin, Swift 등)는 소스 코드를 최적화하는 중간 과정에서 CPS를 사용한다. 그 이유는 다음과 같다:
1. **분석 용이성**: 모든 제어 흐름이 함수 호출로 단일화되어 정적 분석이 쉬워진다.
2. **함수 인라인화**: Continuation을 분석하여 불필요한 함수 호출을 제거하고 인라인화하기 유리하다.
3. **리소스 관리**: 세이브포인트나 컨텍스트 스위칭이 필요한 지점을 명확히 정의할 수 있다.

---

## 6. 결론
Continuation Passing Style은 단순히 "콜백을 사용하는 코딩 스타일"을 넘어, **함수의 실행 완료와 제어권의 이동을 분리**하는 강력한 추상화 도구이다. 명령형 스타일의 반환 값에 의존하는 대신 제어권을 명시적으로 넘김으로써, 복잡한 비동기 로직이나 깊은 재귀적 구조를 보다 견고하게 설계할 수 있다.

특히 Java의 **Vavr**나 **Project Loom**과 같은 환경에서 함수형 패러다임을 깊게 적용하고자 한다면, CPS는 반드시 이해해야 할 핵심 개념이다.

---

# 7. Reference
- [C2 Wiki: Continuation Passing Style](https://wiki.c2.com/?ContinuationPassingStyle)
- [Continuation-Passing Style: Theory and Practice](https://dl.acm.org/doi/10.1145/258948.258951)
- [Functional Programming in Java: CPS approach](https://www.baeldung.com/java-continuation-passing-style)

---

# Appendix: Trampolining과 Stack
Java와 같이 TCO를 지원하지 않는 런타임에서 CPS를 적용할 때 발생할 수 있는 스택 오버플로우 문제를 해결하기 위해 **Trampolining**을 사용한다.

- **원리**: 폰 노이만 구조의 스택 빌드업 대신, 루프 안에서 함수 객체를 반환받아 순차적으로 실행한다.
- **Vavr 활용**: `io.vavr.control.Trampoline`을 사용하면 CPS 스타일의 재귀 호출을 안전하게 힙(Heap) 메모리 영역에서 처리할 수 있다.

```java
// Vavr Trampoline 예시
static Trampoline<Integer> fib(int n, int a, int b) {
    return n == 0 ? Trampoline.done(a) : Trampoline.more(() -> fib(n - 1, b, a + b));
}

// 스택을 소모하지 않고 계산 수행
int result = fib(1000, 0, 1).get();
```

---
