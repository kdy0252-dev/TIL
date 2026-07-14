---
id: Composite Pattern
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
---
# Composite Pattern

## Composite Pattern이란?
Composite 패턴은 객체들을 트리 구조로 구성하여, 개별 객체와 객체 그룹을 동일한 방식으로 다룰 수 있게 하는 디자인 패턴이다. 다시 말해, **전체-부분 관계**를 나타내는 데 유용하며, 클라이언트는 개별 객체와 복합 객체(composite)를 구분 없이 사용할 수 있다.
![[Composite Pattern - 01.png]]
Tree 구조를 사용할때 유용하다.

중요한 점은 단순히 Tree를 만드는 것이 아니라, Client가 Leaf와 Group에 같은 연산을 호출해도 의미 있는 결과를 얻는다는 것이다. File과 Directory에 `size()`를 호출하거나 상품과 상품 묶음에 `price()`를 호출하는 경우가 대표적이다.
## 구성 요소
*   **Component**: 모든 객체(개별 객체 및 복합 객체)에 대한 공통 인터페이스를 정의한다.
*   **Leaf**: Component의 기본 구현 클래스로, 더 이상 하위 객체를 가질 수 없는 개별 객체를 나타낸다.
*   **Composite**: Component 인터페이스를 구현하며, Leaf 객체들을 포함하는 복합 객체를 나타낸다. Composite는 자식 객체들을 관리하는 메서드(추가, 제거 등)를 제공한다.
## 동작 방식
1.  클라이언트는 Component 인터페이스를 통해 객체에 접근한다.
2.  개별 객체(Leaf)는 자신의 작업을 직접 수행한다.
3.  복합 객체(Composite)는 자식 객체들에게 작업을 위임하고, 필요에 따라 자식 객체들의 결과를 결합한다.
## 실무 예제: 복합 요금 항목

`execute()`처럼 의미가 넓은 이름 대신 Domain 연산을 공통 계약으로 둔다. 단일 요금과 요금 묶음 모두 금액 계산과 항목 평탄화를 지원한다.

```java
public sealed interface FareComponent permits FareLine, FareGroup {

    Money amount();

    Stream<FareLine> flatten();
}

public record FareLine(FareType type, Money amount) implements FareComponent {

    public FareLine {
        Objects.requireNonNull(type);
        Objects.requireNonNull(amount);
    }

    @Override
    public Stream<FareLine> flatten() {
        return Stream.of(this);
    }
}

public record FareGroup(String name, List<FareComponent> children) implements FareComponent {

    public FareGroup {
        Objects.requireNonNull(name);
        children = List.copyOf(children);
    }

    @Override
    public Money amount() {
        return children.stream()
                       .map(FareComponent::amount)
                       .reduce(Money.ZERO, Money::add);
    }

    @Override
    public Stream<FareLine> flatten() {
        return children.stream().flatMap(FareComponent::flatten);
    }
}
```

Application Service는 Leaf와 Group을 구분하지 않고 같은 연산을 호출한다.

```java
public FareSummary summarize(FareComponent root) {
    Map<FareType, Money> amountByType = root.flatten()
                                               .collect(Collectors.toUnmodifiableMap(
                                                   FareLine::type,
                                                   FareLine::amount,
                                                   Money::add
                                               ));
    return new FareSummary(root.amount(), amountByType);
}
```

`children`을 방어적으로 복사하므로 외부에서 Tree를 변경할 수 없다. Tree 구성 자체가 업무 검증을 필요로 하면 `FareGroup.create`가 최대 깊이, 빈 Group과 허용하지 않는 조합을 `Validation`으로 검사하게 한다.
## 장점
*   **유연성**: 새로운 Component를 쉽게 추가할 수 있다.
*   **단순성**: 클라이언트는 개별 객체와 복합 객체를 동일하게 다룰 수 있다.
*   **확장성**: 복잡한 트리 구조를 쉽게 구축할 수 있다.
## 단점
*   트리 구조가 너무 복잡해지면 관리가 어려워질 수 있다.
*   Component 인터페이스가 너무 많은 메서드를 포함하게 될 수 있다.

## 투명성과 안전성의 Trade-off

Component에 `add()`와 `remove()`까지 넣으면 Client가 Leaf와 Composite를 완전히 같은 Type으로 다룰 수 있지만, Leaf의 `add()`는 지원할 수 없어 예외나 빈 구현이 생긴다. 자식 관리 Method를 Composite에만 두면 Type 안전성은 높아지지만 Client가 구체 Type을 알아야 한다.

업무 연산은 공통 Interface에 두고 구조 변경은 Builder나 Composite 전용 API로 제한하는 절충이 흔하다.

## 순환과 깊이 문제

일반 Tree라면 자식이 조상을 다시 참조하지 못하게 해야 한다. 순환이 생기면 재귀 연산이 종료되지 않는다. 사용자 입력으로 매우 깊은 Tree가 만들어질 수 있다면 재귀 호출의 Stack Overflow, 전체 순회 비용과 최대 깊이 제한도 고려한다.

## Composite를 쓰지 않는 편이 나은 경우

- Leaf와 Group에 적용할 공통 업무 연산이 없다.
- 구조가 Tree가 아니라 임의 Graph이며 순환이 핵심이다.
- 단순 Collection 한 단계로 충분하다.
- 객체마다 지원하지 않는 Method가 많아 Interface가 거짓말하게 된다.
## 활용 사례
*   GUI (Graphical User Interface) : 윈도우, 버튼, 텍스트 필드 등의 UI 요소들을 트리 구조로 표현
*   파일 시스템 : 파일과 디렉터리를 트리 구조로 표현
*   조직도 : 회사 조직을 트리 구조로 표현
# Reference
[Component Pattern 영상](https://www.youtube.com/watch?v=XXvrHAsfTso&ab_channel=%EC%BD%94%EB%93%9C%EC%97%86%EB%8A%94%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D)
[Refactoring.Guru - Composite](https://refactoring.guru/design-patterns/composite)
