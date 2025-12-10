---
id: State Pattern
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
---
# State Pattern
## State Pattern이란?
FSM(finite state machine with terminal state)을 구현하는 디자인 패턴 중 하나이다. State Pattern은 객체의 내부 상태가 변경됨에 따라 객체의 행동을 변경할 수 있게 하는 디자인 패턴이다. 마치 객체가 자신의 클래스를 바꾸는 것처럼 보이게 한다.
## 핵심 아이디어
*   **상태(State)**: 객체의 특정 상황이나 조건을 나타낸다.
*   **Context**: 상태에 따라 행동이 달라지는 객체이다. Context는 현재 상태를 가지고 있으며, 상태 변경 요청을 상태 객체에 위임한다.
*   **전이(Transition)**: Context의 상태가 변경되는 것을 의미한다.
## 코드
간단한 예제를 위해서 신호등 파란불 빨간불을 전환하는 코드를 작성한다.
```java title="TrafficLight.java"
@Setter
public class TrafficLight {
    private TrafficLightState trafficLightState;

    public void print() {
        trafficLightState.print();
    }

    public void changeState() {
        trafficLightState.changeState(this);
    }
}

```

```java title="TrafficLightState.interface"
public interface TrafficLightState {

    void changeState(TrafficLight trafficLight);

    void print();
}
```

```java title="RedLight.java"
@Slf4j
public class RedLight implements TrafficLightState {
    @Override
    public void changeState(TrafficLight trafficLight) {
        trafficLight.setTrafficLightState(new GreenLight());
    }

    @Override
    public void print() {
        log.info("Red light");
    }
}
```

```java title="GreenLight.java"
@Slf4j
public class GreenLight implements TrafficLightState {
    @Override
    public void changeState(TrafficLight trafficLight) {
        trafficLight.setTrafficLightState(new RedLight());
    }

    @Override
    public void print() {
        log.info("Green light");
    }
}
```

```java title="실행코드"
void statePatternTest() {
    TrafficLight trafficLight = new TrafficLight();

    trafficLight.setTrafficLightState(new RedLight());

    trafficLight.print();
    trafficLight.changeState();
    trafficLight.print();
    trafficLight.changeState();
    trafficLight.print();
}
```
위와 같이 구현하면 TrafficLight 메소드의 변경 없이 상태만 추가할 수 있으므로 OCP를 만족한다.
## 장점
*   **OCP (Open/Closed Principle) 만족**: 새로운 상태를 추가해도 기존 코드를 수정할 필요가 없다. TrafficLight 예시에서 새로운 색깔의 상태를 추가하더라도 `TrafficLight` 클래스의 코드를 변경할 필요가 없다.
*   **SRP (Single Responsibility Principle) 만족**: 각 상태는 자신의 책임만 수행하므로 코드가 간결해진다.
*   **상태 변화를 중앙 집중적으로 관리**: Context에서 상태 변화를 관리하므로 상태 로직이 분산되지 않는다.
## 단점
*   상태가 많아지면 클래스 수가 늘어 코드 관리가 복잡해질 수 있다.
*   상태 전이 로직이 복잡해지면 전체 구조를 이해하기 어려울 수 있다.
## 주의사항
**상태 폭발 방지**: 상태가 너무 많아지지 않도록 설계 단계에서 상태를 단순화하거나 그룹화하는 것을 고려해야 한다. 
**Context와 State 간의 의존성 관리**: Context가 State에 너무 많은 의존성을 가지지 않도록 주의해야 한다. 인터페이스를 통해 결합도를 낮추는 것이 좋다. 상태 객체는 상태 관리 로직만 포함하고, 비즈니스 로직은 Context나 별도의 서비스 객체에 두어 SRP를 지키도록 한다.
**상태 전이 로직의 일관성 유지**: 상태 전이 로직이 여러 곳에 분산되지 않도록 중앙 집중적으로 관리해야 한다. 
**테스트 용이성 확보**: 각 상태에 대한 테스트 케이스를 작성하여 상태 전이가 올바르게 이루어지는지 확인해야 한다.
## 실제 활용 사례
*   **GUI 프레임워크**: 버튼의 상태(활성화, 비활성화, 클릭)에 따라 다른 동작을 수행
*   **게임 개발**: 캐릭터의 상태(걷기, 뛰기, 점프)에 따라 다른 애니메이션 및 로직을 적용
*   **네트워크 프로토콜**: 연결 상태(대기, 연결 중, 연결 완료)에 따라 다른 데이터 처리 방식을 사용
*   **전자상거래**: 주문 상태(장바구니, 결제 완료, 배송 중, 배송 완료)에 따라 다른 프로세스를 진행
# Reference
[State Pattern 영상](https://www.youtube.com/watch?v=278vXJkgXoY&ab_channel=%EC%BD%94%EB%93%9C%EC%97%86%EB%8A%94%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D)