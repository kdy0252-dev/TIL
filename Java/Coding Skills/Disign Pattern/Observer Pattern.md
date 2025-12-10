---
id: Observer Pattern
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
---
# Observer Pattern
## Observer Pattern이란?
Observer 패턴은 Subject의 상태 변화를 Observer들에게 알리는 디자인 패턴이다. Observer(Subscriber, Listener)는 Event를 기다리면서 Event가 생기면 반응하여 함수를 호출하는 패턴이다. **주 객체(Subject)의 상태 변화를 감시하는 객체(Observer) 목록을 유지하고, 상태 변화가 있을 때마다 해당 객체들에게 자동으로 알림을 보내는 방식**이다.
![[Pasted image 20250514221654.png]]
## 구성 요소
*   **Subject**: 상태 변화를 감시하는 대상 객체. Observer 목록을 관리하고, 상태 변화가 있을 때 Observer들에게 알림을 보낸다.
*   **Observer**: Subject의 상태 변화를 감지하고, 알림을 받았을 때 특정 동작을 수행하는 객체.
*   **ConcreteSubject**: Subject 인터페이스를 구현하는 실제 클래스. 상태 변화를 감지하고 Observer들에게 알림을 보낸다.
*   **ConcreteObserver**: Observer 인터페이스를 구현하는 실제 클래스. Subject의 상태 변화에 따라 특정 동작을 수행한다.
## 동작 방식
1.  Observer는 Subject에 등록하여 상태 변화를 감지할 준비를 한다.
2.  Subject의 상태가 변하면, Subject는 등록된 모든 Observer에게 알림을 보낸다.
3.  각 Observer는 알림을 받으면, 미리 정의된 동작을 수행한다.
## 코드
```java title="Observer.interface"
public interface Observer {
    void update();
}
```

```java title="ReceiverOne.java"
@Slf4j
public class ReceiverOne implements Observer {
    @Override
    public void update() {
        log.info("update complete_1");
    }
}
```

```java title="ReceiverTwo.java"
@Slf4j
public class ReceiverTwo implements Observer {
    @Override
    public void update() {
        log.info("update complete_2");
    }
}
```

```java title="Event.java"
public class Event {
    List<Observer> observerList = new ArrayList<>();

    public void register(Observer observer) {
        observerList.add(observer);
    }
    public void notifyToObserver() {
        observerList.forEach(Observer::update);
    }}
```

```java title="invoker"
void observerPatternTest() {
    // 이 함수가 invoker    Event notifier = new Event();
    notifier.register(new ReceiverOne());
    notifier.register(new ReceiverTwo());

    notifier.notifyToObserver();
}
```
위 예시는 아주 간단한 Observer 패턴이지만
*   Observer 패턴을 바라보는 Observer 패턴
*   register에 여러 method 파라미터 받기
*   notify 함수를 여러개를 구현
과 같이 응용이 가능하다.
## 장점
*   **낮은 결합도**: Subject와 Observer는 서로에 대해 거의 알지 못하므로, 결합도가 낮아 유지보수 및 확장이 용이하다.
*   **유연성**: 새로운 Observer를 쉽게 추가할 수 있다.
*   **재사용성**: Subject와 Observer를 독립적으로 재사용할 수 있다.
## 단점
*   **알림 누락 가능성**: Observer가 너무 많거나, 알림 처리 시간이 오래 걸리는 경우 알림이 누락될 수 있다.
*   **예측 불가능한 동작**: Observer의 동작이 예측하기 어렵거나, Observer 간의 의존성이 있는 경우 문제가 발생할 수 있다.
## 활용 사례
*   **GUI (Graphical User Interface)**: 버튼 클릭, 마우스 이동 등의 이벤트 처리
*   **주식 시장**: 주가 변동에 따른 알림
*   **소셜 미디어**: 팔로우, 좋아요 등의 알림

## 비동기 프로그래밍에서의 활용

옵저버 패턴은 비동기 프로그래밍에서 작업 완료 후 결과를 처리하는 데 유용하게 사용될 수 있다. Promise나 콜백 함수 기반의 비동기 작업은 작업 완료 시점에 특정 함수(콜백 함수)를 실행하여 결과를 전달한다. 이러한 방식은 옵저버 패턴의 Subject(작업)가 상태 변화(작업 완료)를 Observer(콜백 함수)에게 알리는 것과 유사하게 볼 수 있다.

예를 들어, Promise의 `then()` 메서드는 작업 성공 시 실행할 콜백 함수를 등록하는 역할을 한다. 이는 옵저버 패턴에서 Observer를 Subject에 등록하는 것과 같다. 작업이 완료되면 Promise는 등록된 콜백 함수를 실행하여 결과를 전달하는데, 이는 Subject가 Observer에게 알림을 보내는 것과 유사하다.

하지만 Promise나 콜백 함수는 옵저버 패턴의 모든 기능을 제공하지는 않는다. 옵저버 패턴에서는 Subject가 Observer 목록을 직접 관리하지만, Promise나 콜백 함수에서는 이러한 관리 기능이 명시적으로 드러나지 않는다.

그럼에도 불구하고 비동기 프로그래밍에서 Promise나 콜백 함수를 사용하는 방식은 옵저버 패턴의 기본적인 아이디어를 활용하여 비동기 작업의 결과를 효율적으로 처리할 수 있도록 해준다.
# Reference
[Observer Pattern 영상](https://www.youtube.com/watch?v=1dwx3REUo34&ab_channel=%EC%BD%94%EB%93%9C%EC%97%86%EB%8A%94%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D)