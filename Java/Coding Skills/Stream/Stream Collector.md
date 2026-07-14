---
id: Stream Collector
started: 2025-04-24
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# Stream Collector

Stream의 중간 연산인 `map`, `filter`는 아직 결과 Container를 만들지 않는다. 마지막에 `List`, `Set`, `Map`이나 하나의 통계값으로 결과를 모으는 연산이 필요하다. 이 역할을 하는 것이 `collect()`와 `Collector`다.

Collector를 단순히 “List로 바꾸는 함수”로만 이해하면 중복 Key, 순서, 변경 가능성, 병렬 처리에서 예상 밖의 결과를 만나기 쉽다. 먼저 배열 수집부터 시작해 Collector의 구성 원리까지 살펴본다.

## toArray는 왜 Object[]를 반환할까?

인자가 없는 `Stream.toArray()`는 Runtime에 구체적인 배열 Component Type을 알 수 없으므로 `Object[]`를 반환한다.

```java title="Object[]을 반환한다"
Object[] accounts = accountDtos.stream()
    .map(Account::from)
    .toArray();
```

`Object[]`는 `Account[]`로 안전하게 Cast할 수 없다. 배열 생성자를 전달하면 Stream이 올바른 Type의 배열을 만든다.

```java title="Account[]을 반환한다"
Account[] accounts = accountDtos.stream()
    .map(Account::from)
    .toArray(Account[]::new);
```

## collect가 하는 일

`collect()`는 Stream Element를 변경 가능한 결과 Container에 누적한 뒤 최종 결과를 만든다. 개념적으로 Collector는 네 부분으로 이루어진다.

1. `supplier`: 빈 결과 Container를 만든다.
2. `accumulator`: Element 하나를 Container에 넣는다.
3. `combiner`: 병렬 처리에서 부분 결과 둘을 합친다.
4. `finisher`: 필요하면 누적 Container를 최종 Type으로 변환한다.

대부분은 직접 구현하지 않고 `Collectors`의 검증된 Factory를 사용한다. 그래도 이 구조를 알면 병렬 Stream에서 결합 가능한 연산이어야 하는 이유를 이해할 수 있다.

## List로 수집하기

```java title="toList()로 List 만들기"
List<String> names = Stream.of("Alice", "Bob", "Charlie")
    .toList();
```

Java 16의 `Stream.toList()`가 반환하는 List는 수정할 수 없다. `Collectors.toList()`는 구체적인 구현 Type과 변경 가능성을 API 계약으로 보장하지 않는다. 수정 가능한 `ArrayList`가 반드시 필요하면 의도를 명시한다.

```java
ArrayList<String> names = Stream.of("Alice", "Bob", "Charlie")
    .collect(Collectors.toCollection(ArrayList::new));
```

## Set으로 중복 제거하기

```java title="toSet()으로 중복 제거하기"
Set<String> names = Stream.of("Alice", "Bob", "Charlie", "Alice")
    .collect(Collectors.toSet());
```

중복 판단에는 Element의 `equals()`와 `hashCode()`가 사용된다. `toSet()`은 Encounter Order를 보장하지 않으므로 입력 순서를 유지해야 하면 `LinkedHashSet`을 선택한다.

```java
Set<String> orderedNames = names.stream()
    .collect(Collectors.toCollection(LinkedHashSet::new));
```

## Map과 중복 Key 정책

```java title="toMap()으로 이름과 길이 연결하기"
Map<String, Integer> nameLengths = Stream.of("Alice", "Bob", "Charlie")
    .collect(Collectors.toMap(
        Function.identity(),
        String::length
    ));
```

첫 번째 Function은 Key, 두 번째 Function은 Value를 만든다. 같은 Key가 두 번 나오면 두 인자 버전의 `toMap()`은 `IllegalStateException`을 던진다. 어떤 값을 남길지 업무 규칙이 있다면 Merge Function을 명시한다.

```java
Map<String, Member> latestMemberByEmail = members.stream()
    .collect(Collectors.toMap(
        Member::email,
        Function.identity(),
        (previous, current) -> current,
        LinkedHashMap::new
    ));
```

중복이 원래 존재하면 안 되는 데이터라면 임의로 마지막 값을 선택해 문제를 숨기지 않는다. 예외를 유지하거나 중복을 명확하게 검증하는 편이 낫다.

## groupingBy로 일대다 Map 만들기

같은 Key에 여러 값을 보존하려면 `toMap`보다 `groupingBy`가 자연스럽다.

```java
Map<Grade, List<Student>> studentsByGrade = students.stream()
    .collect(Collectors.groupingBy(Student::grade));
```

Downstream Collector를 전달하면 Group별 Count나 합계를 바로 계산할 수 있다.

```java
Map<Grade, Long> studentCountByGrade = students.stream()
    .collect(Collectors.groupingBy(
        Student::grade,
        Collectors.counting()
    ));
```

## partitioningBy는 두 Group만 만든다

Predicate 결과가 참과 거짓인 두 Group으로 나눌 때 사용한다.

```java
Map<Boolean, List<Order>> ordersByPaid = orders.stream()
    .collect(Collectors.partitioningBy(Order::isPaid));
```

Key가 반드시 `true`와 `false`라는 점에서 임의의 Key를 만드는 `groupingBy`와 다르다.

## 숫자 집계와 Summary

합계 하나만 필요하면 Primitive Stream이 간단하다.

```java
long totalAmount = orders.stream()
    .mapToLong(Order::amount)
    .sum();
```

Count, Sum, Min, Average, Max를 함께 볼 때는 Summary Collector를 사용한다.

```java
LongSummaryStatistics statistics = orders.stream()
    .collect(Collectors.summarizingLong(Order::amount));
```

금액처럼 정확한 소수가 필요하면 `double` 평균보다 `BigDecimal`과 명시적인 반올림 규칙을 사용한다.

## joining으로 문자열 만들기

반복문에서 문자열을 `+`로 계속 연결하면 중간 String 객체가 많이 생긴다. `joining`은 구분자와 접두·접미사를 의도와 함께 표현한다.

```java
String csv = names.stream()
    .collect(Collectors.joining(",", "[", "]"));
```

값에 쉼표나 따옴표가 들어갈 수 있는 실제 CSV라면 단순 `joining`이 아니라 Escape 규칙을 지원하는 CSV Library를 사용해야 한다.

## collectingAndThen으로 마지막 변환하기

수집 후 한 번의 변환이 필요할 때 사용한다.

```java
List<String> immutableNames = names.stream()
    .collect(Collectors.collectingAndThen(
        Collectors.toList(),
        List::copyOf
    ));
```

Java 16 이상에서 단순히 수정 불가능한 List만 필요하다면 `Stream.toList()`가 더 간단하다. `collectingAndThen`은 다른 Collector의 결과를 Domain Type으로 감싸는 경우처럼 실제 후처리가 있을 때 유용하다.

## 병렬 Stream에서 주의할 점

Collector의 결합 연산은 순서와 Grouping 결과에 영향을 줄 수 있다. 병렬화하려면 다음 조건을 확인한다.

- Accumulator가 공유 외부 상태를 변경하지 않는다.
- Combiner가 부분 결과를 손실 없이 결합한다.
- Encounter Order가 필요한지 분명하다.
- 작은 Collection에서 병렬화 비용이 계산 이득보다 크지 않은지 Benchmark한다.

특히 `forEach`로 외부 `ArrayList`에 추가하는 코드는 Collector가 아니다. 병렬 Stream에서는 Race Condition을 만들 수 있다.

```java
// 피해야 할 공유 변경 상태
List<String> unsafeResult = new ArrayList<>();
names.parallelStream().forEach(unsafeResult::add);

// Stream이 결과 Container를 관리한다.
List<String> safeResult = names.parallelStream().toList();
```

Collector를 고를 때는 단순히 최종 Type만 보지 않는다. **중복 Key를 어떻게 처리할지, 순서를 보존할지, 결과를 수정할 수 있어야 하는지, 병렬 결합이 안전한지**가 수집 연산의 진짜 계약이다.

# Reference
[Java API - Collector](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Collector.html)
[Java API - Collectors](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Collectors.html)
[Java API - Stream](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Stream.html)
