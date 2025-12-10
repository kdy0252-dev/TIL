---
id: Command Pattern
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
---
# Command Pattern

## 정의
Command Pattern은 요청을 객체(Command)로 캡슐화하여 요청을 보내는 객체(Invoker)와 요청을 처리하는 객체(Receiver)를 분리하는 패턴입니다. 이는 마치 **리모컨(Invoker)으로 TV(Receiver)를 조작할 때, 각 버튼(Command)이 특정 동작(채널 변경, 볼륨 조절 등)을 수행하도록 하는 것**과 같습니다. 각 버튼은 실제 TV를 제어하는 코드를 캡슐화하고 있으며, 리모컨은 어떤 버튼이 눌렸는지에 따라 해당 명령을 실행합니다.

코드에서 보자면 Invoker는 command를 호출하는 호출자가 된다.
Receiver는 Command 객체가 조작할 객체를 자신의 멤버변수로 들고있는데 이것들이 Receiver이다.
Command 객체는 Receiver를 조작하는 명령을 실행시키는 주체이다.

## 목적
* 요청을 큐에 저장하거나, 로그로 기록하거나, 취소할 수 있도록 합니다.
* Invoker와 Receiver 사이의 의존성을 줄입니다.

## 구성 요소
* **Command**: 실행될 연산을 캡슐화하는 인터페이스입니다.
* **ConcreteCommand**: Command 인터페이스를 구현하고, 특정 Receiver에 대한 연산을 수행합니다.
* **Invoker**: Command 객체를 사용하여 요청을 실행합니다.
* **Receiver**: 요청을 처리하는 객체입니다.
* **Client**: Command 객체를 생성하고 Invoker에 제공합니다.

## 구현 예시 (Java)
```java title="CommandPatternExample.java"
// Command Interface
interface Command {
    void execute();
}

// Concrete Command
class LightOnCommand implements Command {
    private Light light;

    public LightOnCommand(Light light) {
        this.light = light;
    }

    @Override
    public void execute() {
        light.on();
    }
}

// Receiver
class Light {
    public void on() {
        System.out.println("Light is on");
    }

    public void off() {
        System.out.println("Light is off");
    }
}

// Invoker
class RemoteControl {
    private Command command;

    public void setCommand(Command command) {
        this.command = command;
    }

    public void pressButton() {
        command.execute();
    }
}

// Client
public class Client {
    public static void main(String[] args) {
        Light light = new Light();
        LightOnCommand lightOnCommand = new LightOnCommand(light);

        RemoteControl remoteControl = new RemoteControl();
        remoteControl.setCommand(lightOnCommand);
        remoteControl.pressButton(); // Output: Light is on
    }
}
```

## 장점
*   **결합도 감소**: Invoker와 Receiver 사이의 의존성을 줄여줍니다.
*   **유연성**: 새로운 Command를 쉽게 추가할 수 있습니다.
*   **재사용성**: Command 객체를 여러 번 사용할 수 있습니다.
*   **Undo/Redo 기능**: Command 패턴을 사용하여 실행 취소 및 재실행 기능을 구현할 수 있습니다.

## 단점
*   클래스 수가 증가하여 코드 복잡성이 증가할 수 있습니다.

## 활용 사례
*   GUI 애플리케이션의 메뉴 또는 버튼 동작
*   트랜잭션 처리
*   매크로 기록 및 실행

>[!Info] Command Pattern은 Invoker와 Receiver 사이의 결합도를 낮추고 유연한 시스템을 구축하는 데 유용한 디자인 패턴입니다.

# Reference
[Commend Pattern 영상](https://www.youtube.com/watch?v=bUULgkwaicQ&ab_channel=%EC%BD%94%EB%93%9C%EC%97%86%EB%8A%94%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D)