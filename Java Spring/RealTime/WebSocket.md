---
id: WebSocket
started: 2025-05-09
tags:
  - ✅DONE
group: "[[Java Spring RealTime]]"
---

# Spring WebSocket

WebSocket은 하나의 TCP Connection에서 Client와 Server가 양방향 Message를 주고받는 Protocol이다. HTTP Upgrade로 연결한 뒤에는 요청·응답이 아니라 장시간 Connection, Message 순서, Backpressure와 재연결을 직접 관리해야 한다.

## 연결 수명

```text
HTTP Upgrade -> Authentication -> Session 등록
-> Message 수신/검증/처리 -> Ping/Pong
-> 정상 종료 또는 Timeout -> Session 제거
```

Load Balancer Idle Timeout보다 짧은 Heartbeat를 보내고, 배포 Drain 시 새 Connection을 막은 뒤 기존 Session에 재연결 신호를 보낸다.

## Configuration

```java
@ConfigurationProperties(prefix = "application.websocket")
public record WebSocketProperties(List<String> allowedOrigins, int maxMessageBytes) {
    public WebSocketProperties {
        allowedOrigins = List.copyOf(allowedOrigins);
    }
}
```

```java
@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class WebSocketConfiguration implements WebSocketConfigurer {

    private final VehicleLocationWebSocketHandler handler;
    private final AuthenticatedHandshakeInterceptor handshakeInterceptor;
    private final WebSocketProperties properties;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(handler, "/ws/vehicle-locations")
                .addInterceptors(handshakeInterceptor)
                .setAllowedOrigins(properties.allowedOrigins().toArray(String[]::new));
    }
}
```

Production에서 `setAllowedOrigins("*")`를 사용하지 않는다. 인증 Cookie를 쓰는 Browser Connection은 Origin 검사가 CSWSH 방어선이 된다.

## Typed Message

```java
public sealed interface ClientWebSocketMessage {

    record SubscribeVehicle(long vehicleId, long afterSequence)
        implements ClientWebSocketMessage {
    }

    record UnsubscribeVehicle(long vehicleId)
        implements ClientWebSocketMessage {
    }
}

public record WebSocketEnvelope<T>(
    UUID messageId,
    String type,
    int schemaVersion,
    T payload
) {
}
```

임의 문자열 Echo가 아니라 Type, Version과 Message ID가 있는 Protocol을 사용한다. 역직렬화 전에 최대 Byte를 검사하고 모르는 Version은 명시적 Error로 응답한다.

## Handler

```java
@Component
@RequiredArgsConstructor
public class VehicleLocationWebSocketHandler extends TextWebSocketHandler {

    private final ObjectMapper objectMapper;
    private final WebSocketMessageDecoder decoder;
    private final VehicleSubscriptionService subscriptionService;
    private final WebSocketSessionRegistry sessionRegistry;

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessionRegistry.register(SessionContext.from(session));
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        decode(message)
            .flatMap(clientMessage -> subscriptionService.handle(session.getId(), clientMessage))
            .flatMap(response -> send(session, response))
            .getOrElseThrow(WebSocketProtocolException::new);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessionRegistry.remove(session.getId());
    }

    private Either<WebSocketError, ClientWebSocketMessage> decode(TextMessage message) {
        return ValidationUtil.must(
                                 message,
                                 value -> value.getPayloadLength() <= decoder.maxMessageBytes(),
                                 new WebSocketError.MessageTooLarge(message.getPayloadLength())
                             )
                             .toEither()
                             .flatMap(decoder::decode);
    }

    private Either<WebSocketError, Void> send(
        WebSocketSession session,
        ServerWebSocketMessage response
    ) {
        return Try.run(() -> session.sendMessage(
                      new TextMessage(objectMapper.writeValueAsBytes(response))))
                  .toEither()
                  .mapLeft(cause -> new WebSocketError.SendFailure(session.getId(), cause));
    }
}
```

Spring의 기본 Servlet WebSocket Session에 여러 Thread가 동시에 `sendMessage`하지 않게 Session별 직렬화 Queue 또는 `ConcurrentWebSocketSessionDecorator`를 사용한다. 느린 Client의 Pending Byte와 전송 시간을 제한한다.

## Broadcast와 Backpressure

모든 Session을 순회하며 무제한 Message를 쌓지 않는다.

- Topic/Vehicle별 Subscriber Index를 둔다.
- Session별 Outbound Queue Byte 상한을 둔다.
- 위치처럼 최신 값이 중요한 Data는 오래된 Pending Update를 덮어쓴다.
- 결제·업무 Event처럼 Drop 불가 Data는 WebSocket이 아니라 Durable 조회 경로를 함께 제공한다.
- Slow Consumer 수, Queue Byte와 Drop 수를 Metric으로 수집한다.

## 재연결

Client는 Exponential Backoff와 Jitter로 재연결하고 마지막 처리 Sequence를 보낸다. Server가 Replay Buffer 범위 안이면 누락 Event를 재전송하고, 범위를 벗어나면 REST Snapshot을 다시 조회하도록 알린다.

## Test

- 인증·Origin이 잘못된 Handshake 거부
- 잘못된 JSON, Type, Version과 초과 크기 Message 거부
- 같은 Session의 Subscribe/Unsubscribe 멱등성
- 느린 Client Queue 상한과 Drop Policy
- Connection 종료 후 Registry 정리
- 배포 Drain과 재연결 Sequence 복구

## 기억할 점

WebSocket은 Controller Method 하나가 아니라 Connection Lifecycle을 운영하는 기능이다. Typed Protocol, 인증, Origin, Session별 Backpressure, Heartbeat, 재연결과 Drain을 함께 설계해야 한다.

# Reference

- [Spring WebSocket](https://docs.spring.io/spring-framework/reference/web/websocket.html)
