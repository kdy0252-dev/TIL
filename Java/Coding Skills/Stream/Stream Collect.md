---
id: Stream Collector
started: 2025-04-25
tags:
  - ✅DONE
  - Java
group:
  - "[[Java Coding Skills]]"
---
# Stream Collect

## Stream.collect() 이란?
Stream의 `collect()` 메서드는 스트림의 요소들을 수집하여 특정 자료구조로 변환하는 최종 연산(Terminal Operation)이다. 스트림의 요소들을 List, Set, Map 등 다양한 형태로 변환하거나, 통계적인 요약 정보를 추출하는 데 사용된다.

```java title="Stream.collect() 정의문"
@Override
public <R, A> R collect(Collector<? super P_OUT, A, R> collector) {
    // 파이프라인을 실행하여, collector 전략에 따라 A 타입의 누적 결과를 만들고
    // finisher() 를 적용해 R 타입의 최종 결과를 반환
    return evaluate(ReduceOps.makeRef(collector));
}
```
*   **파라미터:** `Collector<? super T, A, R>` 타입의 `collector`
    *   `T`: 스트림 요소의 타입
    *   `A`: 누적기(Accumulator) 타입
    *   `R`: 최종 결과 타입
*   **리턴 타입:** `R`
## ReduceOps.makeRef
```java title="ReduceOps.java"
static <T, A, R> TerminalOp<T, R> makeRef(Collector<? super T, A, R> collector) {
    // Collector의 supplier, accumulator, combiner, finisher를 꺼내
    // RefPipeline을 위한 ReduceOp 객체를 생성
    return new ReferencePipeline.ReduceOp<>(
        collector.characteristics(),
        collector.supplier(),
        collector.accumulator(),
        collector.combiner(),
        collector.finisher());
}
```
`ReduceOps.makeRef()` 메서드는 `Collector` 인터페이스의 구현체를 받아 `ReferencePipeline`을 위한 `ReduceOp` 객체를 생성한다. 이 객체는 스트림의 요소들을 어떻게 누적하고 최종 결과를 만들지를 정의한다.
## ReferencePipeline.ReduceOp
```java title="ReferencePipeline.java"
static final class ReduceOp<T, A, R> implements TerminalOp<T, R>, /* ... */ {
    private final Supplier<A> supplier;
    private final BiConsumer<A, T> accumulator;
    private final BinaryOperator<A> combiner;
    private final Function<A, R> finisher;
    private final Set<Collector.Characteristics> characteristics;

    ReduceOp(Set<Characteristics> cs,
             Supplier<A> supplier,
             BiConsumer<A, T> accumulator,
             BinaryOperator<A> combiner,
             Function<A, R> finisher) {
        this.characteristics   = cs;
        this.supplier          = supplier;
        this.accumulator       = accumulator;
        this.combiner          = combiner;
        this.finisher          = finisher;
    }

    @Override
    public R evaluateSequential(PipelineHelper<T> helper, Spliterator<T> spliterator) {
        A result = helper.wrapAndCopyInto(
            supplier.get(), accumulator, spliterator);
        return finish(result);
    }

    @Override
    public R evaluateParallel(PipelineHelper<T> helper, Spliterator<T> spliterator) {
        A result = helper.mergeMapReduce(
            supplier, accumulator, combiner, spliterator);
        return finish(result);
    }

    private R finish(A result) {
        return characteristics.contains(Collector.Characteristics.IDENTITY_FINISH)
             ? (R) result
             : finisher.apply(result);
    }
}
```
`ReferencePipeline.ReduceOp` 클래스는 스트림의 요소들을 누적하고 최종 결과를 생성하는 핵심 로직을 담고 있다.
*   `supplier()`: 누적 결과를 저장할 컨테이너를 생성한다.
*   `accumulator()`: 스트림의 각 요소를 컨테이너에 누적한다.
*   `combiner()`: 병렬 처리 시, 각각의 컨테이너를 하나로 합친다.
*   `finisher()`: 최종 결과를 변환한다.
## Collector
```java title="Collector.java"
@FunctionalInterface
public interface Collector<T, A, R> {
    /**
     * 초기 빈 누적 컨테이너를 생성하는 Supplier.
     */
    Supplier<A> supplier();

    /**
     * 컨테이너 A에 스트림 요소 T를 추가하는 누산 함수.
     */
    BiConsumer<A, T> accumulator();

    /**
     * 병렬 처리 시 두 중간 컨테이너를 합치는 함수.
     */
    BinaryOperator<A> combiner();

    /**
     * 최종적으로 누적 컨테이너 A를 결과 타입 R로 변환.
     */
    Function<A, R> finisher();

    /**
     * 최적화를 위한 힌트(IDENTITY_FINISH, CONCURRENT, UNORDERED).
     */
    Set<Characteristics> characteristics();

    /**
     * Collector 특성을 나타내는 열거형.
     */
    enum Characteristics {
        CONCURRENT,
        UNORDERED,
        IDENTITY_FINISH
    }

    /**
     * 가장 일반적으로 쓰이는 팩토리 메서드 예시(구현부 생략).
     */
    static <T, A, R> Collector<T, A, R> of(
            Supplier<A> supplier,
            BiConsumer<A, T> accumulator,
            BinaryOperator<A> combiner,
            Function<A, R> finisher,
            Characteristics... characteristics) {
        // 구현: 내부적으로 특성 집합 생성 후 new CollectorImpl<>(...)
        throw new UnsupportedOperationException();
    }
}
```
`Collector` 인터페이스는 `collect()` 메서드에 전달되는 인자로, 스트림 요소를 어떻게 수집할지를 정의한다. `Collector`는 다음 네 가지 함수를 제공한다.
*   `supplier()`: 누적 결과를 저장할 컨테이너를 생성한다.
*   `accumulator()`: 스트림의 각 요소를 컨테이너에 누적한다.
*   `combiner()`: 병렬 처리 시, 각각의 컨테이너를 하나로 합친다.
*   `finisher()`: 최종 결과를 변환한다.
## collect() 사용 예시
```java title="collect()를 사용하여 List로 변환"
List<String> names = Stream.of("Alice", "Bob", "Charlie")
                        .collect(Collectors.toList());
System.out.println(names); // [Alice, Bob, Charlie]
```

```java title="collect()를 사용하여 Set으로 변환"
Set<String> names = Stream.of("Alice", "Bob", "Charlie", "Alice")
                       .collect(Collectors.toSet());
System.out.println(names); // [Alice, Bob, Charlie]
```

```java title="collect()를 사용하여 Map으로 변환"
Map<String, Integer> nameLengths = Stream.of("Alice", "Bob", "Charlie")
                                       .collect(Collectors.toMap(
                                           name -> name,
                                           String::length
                                       ));
System.out.println(nameLengths); // {Alice=5, Bob=3, Charlie=7}
```
**예시 설명:**
*   `Collectors.toList()`: 스트림의 요소들을 List로 수집한다.
*   `Collectors.toSet()`: 스트림의 요소들을 Set으로 수집한다. 중복된 요소는 제거된다.
*   `Collectors.toMap()`: 스트림의 요소들을 Map으로 수집한다. 첫 번째 인자는 key를 생성하는 함수이고, 두 번째 인자는 value를 생성하는 함수이다.
## collect()를 언제 사용해야 할까?
*   스트림의 요소들을 List, Set, Map 등 다른 자료구조로 변환해야 할 때
*   스트림의 요소들을 그룹화하거나 분할해야 할 때
*   스트림의 요소들에 대한 통계적인 요약 정보를 추출해야 할 때 (평균, 합계, 최대/최소값 등)

# Reference