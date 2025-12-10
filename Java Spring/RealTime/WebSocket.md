---
id: Spring Boot WebSocket
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# WebSocket
## WebSocket이란?
WebSocket은 클라이언트와 서버 간의 실시간 양방향 통신을 가능하게 하는 통신 프로토콜이다. HTTP와 달리, WebSocket은 한 번 연결이 성립되면 지속적인 연결을 유지하며 데이터를 실시간으로 주고받을 수 있다.
### WebSocket은 왜 사용할까?
WebSocket은 실시간 데이터 전송이 필요한 다양한 애플리케이션에서 사용된다. 예를 들어, 온라인 게임, 채팅 애플리케이션, 주식 시세 표시, 실시간 협업 도구 등에서 WebSocket을 사용하여 데이터를 실시간으로 업데이트할 수 있다.
### WebSocket의 장점과 단점
**장점:**
*   **실시간 양방향 통신**: 서버와 클라이언트가 실시간으로 데이터를 주고받을 수 있다.
*   **낮은 지연 시간**: 지속적인 연결을 유지하므로 HTTP에 비해 지연 시간이 짧다.
*   **서버 푸시**: 서버에서 클라이언트로 데이터를 푸시할 수 있다.
*   **표준 프로토콜**: 대부분의 브라우저와 서버에서 지원하는 표준 프로토콜이다.
**단점:**
*   **HTTP에 비해 복잡한 설정**: HTTP에 비해 설정이 복잡할 수 있다.
*   **연결 관리**: 연결 상태를 지속적으로 관리해야 한다.
*   **확장성**: 많은 수의 연결을 처리하기 위해 확장성을 고려해야 한다.
### WebSocket 사용 예시
*   **온라인 게임**: 실시간으로 게임 상태를 업데이트하고 플레이어 간의 상호 작용을 처리한다.
*   **채팅 애플리케이션**: 메시지를 실시간으로 주고받는다.
*   **주식 시세 표시**: 주식 시세를 실시간으로 업데이트한다.
*   **실시간 협업 도구**: 문서 편집, 화이트보드 등을 실시간으로 공유한다.
## Java Spring WebSocket 구현 예시
### 1. 의존성 추가
Spring Boot 프로젝트에 `spring-boot-starter-websocket` 의존성을 추가해야 한다.

```kotlin title="build.gradle.kts"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-websocket")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```
### 2. WebSocket 설정

```java title="WebSocketConfig.java"
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final MyWebSocketHandler myWebSocketHandler;

    public WebSocketConfig(MyWebSocketHandler myWebSocketHandler) {
        this.myWebSocketHandler = myWebSocketHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(myWebSocketHandler, "/ws").setAllowedOrigins("*");
    }
}
```
*   `@EnableWebSocket` 어노테이션을 사용하여 WebSocket을 활성화한다.
*   `WebSocketConfigurer` 인터페이스를 구현하여 WebSocket 핸들러를 등록한다.
*   `addHandler()` 메서드를 사용하여 WebSocket 핸들러를 특정 URL에 매핑한다.
*   `setAllowedOrigins()` 메서드를 사용하여 CORS 설정을 한다.
### 3. WebSocket 핸들러 구현

```java title="MyWebSocketHandler.java"
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

@Component
public class MyWebSocketHandler extends TextWebSocketHandler {

    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        System.out.println("Received message: " + payload);
        session.sendMessage(new TextMessage("Server received: " + payload));
    }
}
```
*   `TextWebSocketHandler` 클래스를 상속받아 WebSocket 핸들러를 구현한다.
*   `handleTextMessage()` 메서드를 오버라이드하여 클라이언트에서 받은 메시지를 처리한다.
*   `session.sendMessage()` 메서드를 사용하여 클라이언트에 메시지를 보낸다.
### 4. 클라이언트 구현 (JavaScript)

```javascript title="client.js"
const socket = new WebSocket("ws://localhost:8080/ws");

socket.onopen = () => {
    console.log("Connected to WebSocket");
    socket.send("Hello Server!");
};

socket.onmessage = (event) => {
    console.log("Received message: " + event.data);
};

socket.onclose = () => {
    console.log("Disconnected from WebSocket");
};
```
*   `WebSocket` 객체를 사용하여 서버에 연결한다.
*   `onopen` 이벤트 핸들러를 사용하여 연결 성공 시 메시지를 보낸다.
*   `onmessage` 이벤트 핸들러를 사용하여 서버에서 받은 메시지를 처리한다.
*   `onclose` 이벤트 핸들러를 사용하여 연결 종료 시 로그를 출력한다.
### 사용 시 주의사항
- **보안**: WebSocket 연결은 기본적으로 암호화되지 않으므로, WSS (WebSocket Secure)를 사용하여 암호화해야 한다.
- **확장성**: 많은 수의 연결을 처리하기 위해 로드 밸런싱, 클러스터링 등의 기술을 적용해야 한다.
- **에러 처리**: 연결 끊김, 메시지 손실 등의 에러를 처리하기 위한 로직을 구현해야 한다.
- **메시지 형식**: 텍스트, 바이너리 등 다양한 메시지 형식을 지원하므로, 애플리케이션에 맞는 형식을 선택해야 한다.
- **세션 관리**: 사용자 인증, 권한 부여 등을 위한 세션 관리 기능을 구현해야 한다.
## Long Polling, AMQP와 비교

| 기능     | WebSocket       | Long Polling          | AMQP             |
| ------ | --------------- | --------------------- | ---------------- |
| 통신 모델  | 양방향             | 단방향 (클라이언트 -> 서버)     | 양방향 (메시지 큐)      |
| 실시간성   | 높음              | 중간                    | 높음               |
| 서버 부하  | 높음 (지속적인 연결 유지) | 낮음 (이벤트 발생 시에만 응답)    | 중간 (메시지 큐)       |
| 연결 유지  | 연결 유지 (지속적인 연결) | 연결 유지 (Timeout 시 재연결) | 연결 유지 (메시지 큐)    |
| 구현 복잡도 | 높음              | 중간                    | 높음               |
| 사용 사례  | 실시간 채팅, 게임      | 알림, 간단한 상태 업데이트       | 분산 시스템, 마이크로서비스  |
| 장점     | 실시간 양방향 통신      | 서버 자원 효율성             | 확장성, 안정성         |
| 단점     | 서버 부하, 확장성      | 지연 시간, 단방향 통신         | 복잡한 설정, 메시지 큐 관리 |
WebSocket은 실시간 양방향 통신이 필요한 애플리케이션에 적합한 기술이다. 하지만 Long Polling이나 AMQP와 비교하여 장단점이 있으므로, 프로젝트의 요구사항에 따라 적절한 기술을 선택해야 한다.

# Reference
[Spring Boot WebSocket](https://adjh54.tistory.com/573)
[WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
[Spring WebSocket 공식 문서](https://docs.spring.io/spring-framework/reference/websocket.html)