---
id: Stream parallelStream
started: 2025-04-25
tags:
  - ✅DONE
  - Java
  - Concurrency
group: "[[Java Coding Skills]]"
---

# Java parallelStream은 언제 빨라지고 언제 위험한가

`parallelStream()`은 Collection 연산을 여러 Thread에서 나누어 실행한다. Method 하나만 바꾸면 병렬화되지만, 병렬 실행 비용과 공유 자원까지 사라지는 것은 아니다. “데이터가 많으면 빠르다”가 아니라 **분할 가능한 CPU 연산이 충분히 비쌀 때** 효과가 있다.

## 기본 사용

```java
List<Result> results = values.parallelStream()
    .map(Parser::parse)
    .map(Processor::process)
    .toList();
```

Terminal Operation인 `toList()`를 호출한 Thread는 전체 결과가 완성될 때까지 기다린다. 내부 작업이 여러 Thread에서 병렬로 실행된다는 뜻이지 호출 API가 비동기 Future를 반환한다는 뜻은 아니다.

## Fork·Compute·Join

Parallel Stream은 Source의 `Spliterator`를 작은 작업으로 분할하고 일반적으로 `ForkJoinPool.commonPool()`에서 실행한다.

```text
1,000개 입력
-> 500 / 500
-> 250 / 250 / 250 / 250
-> Worker별 연산
-> 부분 결과 결합
```

ArrayList와 Array는 중간 지점을 빠르게 찾을 수 있어 분할이 쉽다. LinkedList, Iterator 기반 Source와 크기를 알 수 없는 Stream은 분할 비용이 크거나 작업이 불균형해질 수 있다.

## 대략적인 성능 조건

병렬 처리 시간은 다음 비용을 포함한다.

```text
parallel time
≈ split + scheduling + element work / cores + merge + coordination
```

요소별 연산이 단순한 덧셈이면 Scheduling 비용이 더 클 수 있다. 반면 큰 수의 Hash 계산이나 독립적인 Image 변환처럼 요소별 CPU 비용이 크면 Core를 활용할 가능성이 있다.

“몇 건 이상이면 빠르다”는 고정 기준은 없다. Data 구조, 연산 비용, Core 수, JIT Warm-up과 다른 Process 부하가 결과를 바꾼다. JMH로 실제 환경을 Benchmark한다.

## CPU-bound와 Blocking I/O

Common Pool의 Worker 수는 CPU 병렬 처리에 맞춰진다. 각 작업이 HTTP, Database나 File I/O를 기다리면 Worker가 Block되어 Pool 전체와 같은 JVM의 다른 Parallel Stream까지 지연될 수 있다.

```java
// 피하는 편이 좋은 예: 요청 수 제어와 Timeout이 보이지 않는다.
users.parallelStream()
    .map(user -> externalApi.getProfile(user.id()))
    .toList();
```

I/O 동시성은 명시적인 Executor, `CompletableFuture`, Virtual Thread 또는 Reactive Client로 Timeout·Concurrency Limit·취소를 제어하는 편이 낫다.

## 공유 상태가 위험한 이유

```java
List<Integer> output = new ArrayList<>();
values.parallelStream().forEach(output::add); // Race Condition
```

`ArrayList`는 Thread-safe하지 않다. 크기와 내부 배열 변경이 충돌해 누락이나 예외가 발생할 수 있다. Stream은 Side Effect 대신 결과를 반환하게 만든다.

```java
List<Integer> output = values.parallelStream()
    .map(value -> value * 2)
    .toList();
```

Concurrent Collection을 사용하면 Data Race는 막을 수 있지만 Lock 경합 때문에 병렬화 이점이 사라질 수 있다.

## 순서

Ordered Source에서 `toList()`와 `forEachOrdered()`는 Encounter Order를 보존할 수 있다. 그러나 순서를 유지하기 위한 Coordination은 비용이 든다.

```java
List<ProcessedRoute> orderedRoutes = routes.parallelStream()
                                           .map(routeProcessor::process)
                                           .toList(); // Ordered Stream의 Encounter Order 보존
```

연산이 순서에 의존한다면 병렬화 가능성부터 다시 검토한다. `findAny()`는 병렬 환경에서 빠른 결과를 허용하고 `findFirst()`는 첫 요소 계약을 지켜야 한다.

## Reduce의 결합 법칙

병렬 Reduce의 연산은 결합 법칙을 만족해야 한다.

```text
(a op b) op c == a op (b op c)
```

정수 덧셈은 만족하지만 뺄셈은 만족하지 않는다. Floating-point 덧셈도 수학적으로는 결합적이어도 반올림 때문에 분할 순서에 따라 마지막 Bit가 달라질 수 있다.

Identity는 어떤 부분 작업에 적용돼도 결과를 바꾸지 않아야 한다. 잘못된 Identity와 Combiner는 Sequential에서는 우연히 맞고 Parallel에서 틀릴 수 있다.

## Common Pool 공유 문제

Application의 여러 기능이 같은 Common Pool을 사용하면 무거운 Parallel Stream 하나가 다른 요청을 방해할 수 있다. 특히 Server 요청 처리 중 사용하면 Traffic 증가에 따라 동시에 여러 Parallel Stream이 생성돼 CPU Oversubscription이 발생한다.

독립 Pool에서 Parallel Stream을 실행하는 우회 방식은 구현 세부사항과 중첩 작업 때문에 주의가 필요하다. 명시적인 작업 분할이 중요하다면 처음부터 Executor나 Structured Concurrency를 선택하는 편이 제어하기 쉽다.

## 올바른 Benchmark

단순 `System.currentTimeMillis()` 한 번으로 비교하면 JIT, GC와 Warm-up에 왜곡된다. JMH로 다음을 분리한다.

- Sequential과 Parallel 결과가 같은지
- Warm-up 후 평균과 분산
- 다양한 Data Size
- 다른 Core 수와 동시 요청 부하
- Allocation과 GC

운영 목표가 단일 작업의 최소 시간인지, Server 전체 Throughput인지도 구분한다. 한 요청이 모든 Core를 사용해 빨라져도 동시에 처리할 요청 수는 줄 수 있다.

## 기억할 점

`parallelStream()`은 비동기 API도, 무조건적인 성능 Option도 아니다. 분할하기 쉬운 Source, 충분히 큰 독립 CPU 연산, 결합 가능한 결과와 여유 Core가 함께 있을 때만 유리하다. 정확성을 먼저 확인하고 JMH와 실제 동시 부하로 이점을 증명해야 한다.

# Reference

- [Java Stream API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Stream.html)
- [Java ForkJoinPool](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ForkJoinPool.html)
