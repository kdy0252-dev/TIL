---
id: WebSocket Secure
started: 2025-05-28
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# WebSocket Secure (WSS)
## WebSocket Secure란?
WebSocket Secure (WSS)는 WebSocket 프로토콜을 암호화된 연결을 통해 사용하는 것을 의미한다. WSS는 TLS (Transport Layer Security) 또는 SSL (Secure Sockets Layer) 프로토콜을 사용하여 WebSocket 연결을 암호화하여 보안을 강화한다.
### WebSocket Secure는 왜 사용할까?
WebSocket Secure는 WebSocket 연결을 통해 전송되는 데이터를 보호하기 위해 사용된다. WSS는 다음과 같은 보안 기능을 제공한다.
*   **데이터 암호화**: 전송되는 데이터를 암호화하여 제3자가 데이터를 가로채더라도 내용을 읽을 수 없도록 한다.
*   **인증**: 서버와 클라이언트 간의 신뢰성을 보장한다.
*   **무결성**: 데이터가 전송 중에 변조되지 않았음을 확인한다.
### WebSocket Secure의 장점과 단점
**장점:**
*   **보안**: 데이터 암호화, 인증, 무결성 검증을 통해 보안을 강화한다.
*   **호환성**: 대부분의 브라우저와 서버에서 지원한다.
*   **기존 WebSocket과 동일한 기능**: 기존 WebSocket과 동일한 기능을 제공하면서 보안을 강화한다.
**단점:**
*   **추가 설정**: TLS/SSL 인증서를 설정해야 한다.
*   **성능**: 암호화로 인해 약간의 성능 저하가 발생할 수 있다.
### WebSocket Secure 사용 예시
*   **금융 거래**: 민감한 금융 거래 데이터를 안전하게 전송한다.
*   **개인 정보**: 개인 식별 정보 (PII)를 안전하게 전송한다.
*   **의료 정보**: 환자 의료 정보를 안전하게 전송한다.
*   **보안 채팅**: 메시지를 암호화하여 보안을 강화한다.
## Java Spring WebSocket Secure 구현 예시
### 1. TLS/SSL 인증서 준비
WebSocket Secure를 사용하려면 TLS/SSL 인증서가 필요하다. 자체 서명된 인증서를 사용하거나, 인증 기관 (CA)에서 발급받은 인증서를 사용할 수 있다.
### 2. Spring Boot 설정
```yaml title="application.yml"
server:
  port: 8443
  ssl:
    enabled: true
    key-store: classpath:keystore.p12
    key-store-password: changeit
    key-store-type: PKCS12
    key-alias: tomcat
```
*   `server.port`: HTTPS 포트를 8443으로 설정한다.
*   `server.ssl.enabled`: SSL을 활성화한다.
*   `server.ssl.key-store`: 키 저장소 파일 경로를 설정한다.
*   `server.ssl.key-store-password`: 키 저장소 비밀번호를 설정한다.
*   `server.ssl.key-store-type`: 키 저장소 유형을 설정한다.
*   `server.ssl.key-alias`: 키 별칭을 설정한다.
### 3. WebSocket 설정
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
*   WebSocket 설정은 일반 WebSocket과 동일하다.
### 4. WebSocket 핸들러 구현
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
*   WebSocket 핸들러 구현은 일반 WebSocket과 동일하다.
### 5. 클라이언트 구현 (JavaScript)
```javascript title="client.js"
const socket = new WebSocket("wss://localhost:8443/ws");

socket.onopen = () => {
    console.log("Connected to WebSocket Secure");
    socket.send("Hello Server!");
};

socket.onmessage = (event) => {
    console.log("Received message: " + event.data);
};

socket.onclose = () => {
    console.log("Disconnected from WebSocket Secure");
};
```
*   `WebSocket` 객체를 생성할 때 `wss://` 프로토콜을 사용한다.
*   포트를 HTTPS 포트 (8443)로 변경한다.
## WebSocket, WebSocket Secure 비교

| 기능   | WebSocket | WebSocket Secure |
| ---- | --------- | ---------------- |
| 프로토콜 | ws://     | wss://           |
| 암호화  | No        | Yes              |
| 보안   | 낮음        | 높음               |
| 포트   | 80, 8080  | 443, 8443        |
| 인증서  | 필요 없음     | 필요               |
| 성능   | 약간 더 빠름   | 약간 느림            |
### 사용 시 주의사항
*   **TLS/SSL 인증서 관리**: TLS/SSL 인증서를 안전하게 관리해야 한다.
*   **CORS 설정**: 필요한 경우 CORS 설정을 적절하게 해야 한다.
*   **성능**: 암호화로 인해 약간의 성능 저하가 발생할 수 있으므로, 성능 테스트를 통해 적절한 설정을 해야 한다.
*   **프록시 설정**: 프록시 서버를 사용하는 경우, WebSocket Secure 연결을 지원하도록 설정해야 한다.

WebSocket Secure는 WebSocket 연결을 암호화하여 보안을 강화하는 중요한 기술이다. 민감한 데이터를 전송하는 애플리케이션에서는 WebSocket Secure를 사용하는 것이 좋다.

# Reference
[RFC 6455 - The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
[Spring Boot WebSocket](https://spring.io/guides/gs/messaging-stomp-websocket/)