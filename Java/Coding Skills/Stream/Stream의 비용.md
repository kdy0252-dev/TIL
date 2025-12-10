---
id: Stream의 처리 비용
started: 2025-03-11
tags:
  - Java
  - ✅DONE
group:
  - "[[Java Coding Skills]]"
---
# Stream의 비용
## Stream은 무엇인가?
- Stream은 Funtional Programming언어에서 이야기하는 Sequnce와 동일한 용어다.
- Sequnce는 task의 순서를 나열한 것이다.

## Sequence(순서) 개념
```
“밥을 받기 → 설거지하기 → 쓰레기 버리기”
1. deliverMeal()
2. washDishes()
3. throwTrash()
```
이 순서가 뒤바뀌면 안 된다.
이렇게 작업(task)을 정해진 순서대로 처리하라는 뜻이 **Sequential Programming**(순차 프로그래밍)이다.

## 내부 반복자 패턴(Internal Iterator)
객체지향 관점에서는 **Internal Iterator Pattern**이라고도 부른다.
- 전통적 반복문(external iterator)
```java title="External iterator 패턴 예시"
for(OnMealDuty duty : onMealDuties) {
    if(duty.grade.equals("일병")) {
        duty.deliverMeal();
        duty.washDishes();
        duty.throwTrash();
    }
}
```
- 스트림 기반 처리(internal iterator)
```Java title="Interanl iterator 패턴 예시"
List<OnMealDuty> onMealDuties = new ArrayList<>();
onMealDuties.stream()                 // ① 스트림 생성
             .filter(d -> d.grade.equals("일병"))  // ② 중간 연산
             .forEach(d -> {          // ③ 최종 연산
                 d.deliverMeal();
                 d.washDishes();
                 d.throwTrash();
             });
```
- 컬렉션 내부에서 요소 하나하나를 꺼내고 `filter`, `map` 같은 **함수(람다)** 만 우리가 제공
  → Stream 내부에서 순회를 하고 우리는 ‘무엇을 할지’(method)를 Stream에 전달한다. 즉, 컬렉션 처리 로직을 내부로 숨기고, 외부에서는 필요한 연산만 지정하는 것이다.

## 메서드 체이닝(Fluent API)
![[Pasted image 20250508130239.png]]
```Java title="Method Chaining"
stream
  .filter(...)
  .map(...)
  .sorted(...)
  .collect(...);
```
- **중간 연산(Intermediate Operations)**
    - 입력 스트림 → 또 다른 스트림 반환
    - `filter()`, `map()`, `sorted()` 등
    - **지연 평가**: 최종 연산 전까지 실제 처리를 안 한다. 즉, 중간 연산은 파이프라인을 구성하는 역할만 하고, 실제 연산은 최종 연산이 호출될 때 한 번에 처리되는 것이다.
- **최종 연산(Terminal Operations)**
    - 스트림 파이프라인을 **실제로 실행**
    - 결과(리스트, 집계값 등) 반환 또는 부수 효과 발생
    - `forEach()`, `collect()`, `count()`, `sum()` 등

## External iterator, Internal iterator 성능 비교
Langer라는 사람이 자신의 강연에서 loop와 순차 스트림(sequential stream), 그리고 병렬 스트림(parallel stream) 별로 퍼포먼스가 어떤지 벤치마크 실험을 했다.
```java title="External iterator"
int[] a = ints;  
int e = ints.length;  
int m = Integer.MIN_VALUE;  
for (int i = 0; i < e; i++) {  
    if (a[i] > m) {  
        m = a[i];  
    }  
}
```

```java title="Internal iterator"
int m = Arrays.stream(ints).reduce(Integer.MIN_VALUE, Math::max);
```
### 벤치마크 결과
![[Pasted image 20250508130602.png]]
External iterator: 0.36ms
Internal iterator: 5.35ms
약 15배 차이

2015년 JAX London 'Java performance tutorial – How fast are the Java 8 streams?' 발표한 내용
> [!Info] for-loop보다 stream이 느린 이유
>  Compilers have 40+ years of experience optimizing loops and the virtual machine’s JIT compiler is especially apt to optimize for-loops over arrays with an equal stride like the one in our benchmark. Streams on the other hand are a very recent addition to Java and the JIT compiler does not (yet) perform any particularly sophisticated optimizations to them.
- JIT Compiler는 40년 이상 for-loop에 최적화되어 왔고, Streams 방식은 추가된지 얼마 되지 않았으므로, 기존 방식 대비 좋은 성능을 기대하기 어렵다.

### Premitive Type이 아닌 Wrapped Type으로 비교
벤치마크 조건
- ArrayList 500000개의 Integer 타입을 저장
- 이후, Integer 중 가장 큰 원소를 리턴
![[Pasted image 20250508130809.png]]
for-loop: 6.55ms
Internal iterator: 8.33ms
약 1.27배 차이
Iterator를 순회하는 비용의 비율보다 ArrayList를 순회하는 비용 **O(n)** 의 비율이 월등이 높기때문이다.
또한 Wrapped Type Stack의 레퍼런스 변수를 통해 실제 Heap의 객체를 참조하는 방식으로 동작한다.
불연속적인 메모리에 저장되고 따라서 연속적인 메모리에 저장되는 Primiteve Type보다 탐색속도가 느리다.

즉 Iteration Cost 자체가 크다면 For Loop와 Stream의 차이는 유의미하게 좁혀진다.

#### 순회비용(cost of iteration)보다 계산 비용(cost of functionality)이 더 큰 경우
![[Pasted image 20250508131502.png]]
파라미터로 넘겨지는 메소드의 Sin 값을 계산하고 이에 대한 테일러 급수를 계산하는 함수다.
```java title="for loop example"
int[] a = ints;  
int e = a.length;  
double m = Double.MIN_VALUE;for (int i = 0; i < e; i++) {  
     double d = Sine.slowSin(a[i]);  
     if (d > m) m = d;  
}
```

```java title="stream example"
Arrays.stream(ints).mapToDouble(Sine::slowSin).reduce(Double.MIN_VALUE, Math::max);
```
![[Pasted image 20250508131642.png]]
for-loop와 Stream간 유의미한 차이가 발생하지 않는다.

즉 순회비용(cost of iteration)과 계산 비용(cost of functionality)의 합이 큰경우 for-loop와 stream간 유의미한 성능차이는 나지 않는다.

> [!Info] Stream은 경우에 따라서는 for-loop와 동등할정도로 빠르다.
> The ultimate conclusion to draw from this benchmark experiment is NOT that streams are always slower than loops. Yes, streams are sometimes slower than loops, but they can also be equally fast; it depends on the circumstances. The point to take home is that sequential streams are no faster than loops. If you use sequential streams then you don’t do it for performance reasons; you do it because you like the functional programming style.
```Java title="Stream을 Collector로 구성"
dataList = br.lines()
             .map(i->i.split("[|]")
             .collect(Collectors.toList());
```
평균 5,730ms
```java title="Imperative Programming(기존 방식)"
List<String[]> dataList = new ArrayList<String[]>();  
while ((readLine = br.readLine()) != null) {  
       columnDatas = readLine.split("[|]");  
       dataList.add(columnDatas);  
}
```
평균 6113.7ms

Stream이 Cpu 자원은 더 소모한다.(자료 생략)

# Reference
[Java Lambda Expression과 성능](https://brunch.co.kr/@heracul/3)
[for-loop vs stream](https://sigridjin.medium.com/java-stream-api%EB%8A%94-%EC%99%9C-for-loop%EB%B3%B4%EB%8B%A4-%EB%8A%90%EB%A6%B4%EA%B9%8C-50dec4b9974b)
[Java performance tutorial – How fast are the Java 8 streams?](https://devm.io/java/java-performance-tutorial-how-fast-are-the-java-8-streams-118830)