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
![[Pasted image 20250514221718.png]]
Tree 구조를 사용할때 유용하다.
## 구성 요소
*   **Component**: 모든 객체(개별 객체 및 복합 객체)에 대한 공통 인터페이스를 정의한다.
*   **Leaf**: Component의 기본 구현 클래스로, 더 이상 하위 객체를 가질 수 없는 개별 객체를 나타낸다.
*   **Composite**: Component 인터페이스를 구현하며, Leaf 객체들을 포함하는 복합 객체를 나타낸다. Composite는 자식 객체들을 관리하는 메서드(추가, 제거 등)를 제공한다.
## 동작 방식
1.  클라이언트는 Component 인터페이스를 통해 객체에 접근한다.
2.  개별 객체(Leaf)는 자신의 작업을 직접 수행한다.
3.  복합 객체(Composite)는 자식 객체들에게 작업을 위임하고, 필요에 따라 자식 객체들의 결과를 결합한다.
## 코드
```java title="Component.interface"
public interface Component {
    void execute();
}
```

```java title="Composite.java"
@Slf4j
public class Composite implements Component {
    private final List<Component> componentList = new ArrayList<>();

    public void add(Component component) {
        componentList.add(component);
    }

    @Override
    public void execute() {
        log.info("Composite");
        componentList.forEach(Component::execute);
    }
}
```

```java title="Leaf.java"
@Slf4j
public class Leaf implements Component {
    @Override
    public void execute() {
        log.info("Leaf");
    }
}
```

```java title="Composite 패턴 사용 예시"
void compositeTest() {
    Composite composite_1 = new Composite();
    Composite composite_0 = new Composite();

    composite_1.add(new Leaf());
    composite_1.add(new Leaf());

    composite_0.add(new Leaf());
    composite_0.add(new Leaf());
    composite_0.add(composite_1);

    composite_0.execute();
}
```
## 장점
*   **유연성**: 새로운 Component를 쉽게 추가할 수 있다.
*   **단순성**: 클라이언트는 개별 객체와 복합 객체를 동일하게 다룰 수 있다.
*   **확장성**: 복잡한 트리 구조를 쉽게 구축할 수 있다.
## 단점
*   트리 구조가 너무 복잡해지면 관리가 어려워질 수 있다.
*   Component 인터페이스가 너무 많은 메서드를 포함하게 될 수 있다.
## 활용 사례
*   GUI (Graphical User Interface) : 윈도우, 버튼, 텍스트 필드 등의 UI 요소들을 트리 구조로 표현
*   파일 시스템 : 파일과 디렉터리를 트리 구조로 표현
*   조직도 : 회사 조직을 트리 구조로 표현
# Reference
[Component Pattern 영상](https://www.youtube.com/watch?v=XXvrHAsfTso&ab_channel=%EC%BD%94%EB%93%9C%EC%97%86%EB%8A%94%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D)