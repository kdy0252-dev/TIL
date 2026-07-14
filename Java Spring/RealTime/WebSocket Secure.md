---
id: WebSocket Secure
started: 2025-05-28
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---

# WebSocket Secure(WSS)

WSS는 WebSocket Frame을 TLS 연결 안에서 전송하는 방식이다. `ws://`와 `wss://`의 차이는 단순한 Scheme이 아니다. WSS는 Server 인증, 전송 구간 암호화, Message 무결성을 제공한다. 다만 사용자가 누구인지 확인하는 Application 인증과 Message 권한 검사는 별도로 구현해야 한다.

## 먼저 구분할 보안 계층

| 계층 | 해결하는 문제 | 대표 수단 |
| --- | --- | --- |
| TLS | 도청·전송 중 변조·가짜 Server | CA 인증서, TLS 1.2 이상, `wss://` |
| Handshake 인증 | Connection을 연 사용자가 누구인가 | Session Cookie, 단기 Access Token |
| Origin 검사 | 악성 Site가 사용자의 Cookie로 연결하는가 | 정확한 Allow List |
| Message 인가 | 이 사용자가 이 Vehicle을 구독할 수 있는가 | Resource별 권한 검사 |
| 운영 보안 | 탈취·남용·장애를 탐지하는가 | Rate Limit, Audit, Rotation, Metric |

TLS가 성공했다고 구독 권한까지 생기는 것은 아니다. Handshake 시 한 번 인증하고, `subscribe` Message마다 Tenant와 Resource 권한을 다시 검사한다.

## Production 배치 구조

```text
Browser
  -- wss://realtime.example.com/ws --> Load Balancer(TLS 종료)
  -- 내부 TLS 또는 신뢰 Network --> Spring WebSocket Server
                                  --> Authentication Provider
                                  --> Authorization Service
```

TLS를 Load Balancer에서 종료하면 Certificate 교체와 Cipher 정책을 중앙화할 수 있다. Load Balancer 뒤 구간의 위협 모델에 따라 내부 TLS도 활성화한다. Proxy의 HTTP/1.1 Upgrade, Connection Header, Idle Timeout 설정을 함께 확인해야 한다.

## 설정값과 Secret 분리

```yaml
application:
  websocket:
    allowed-origins:
      - https://console.example.com
      - https://operations.example.com
    maximum-message-bytes: 65536

server:
  forward-headers-strategy: framework
```

Application에 TLS를 직접 설정해야 한다면 Key Store 암호를 Repository의 YAML에 넣지 않고 Secret Manager 또는 환경 변수에서 주입한다.

```yaml
server:
  port: 8443
  ssl:
    enabled: true
    key-store: ${TLS_KEY_STORE}
    key-store-password: ${TLS_KEY_STORE_PASSWORD}
    key-store-type: PKCS12
    enabled-protocols: TLSv1.3,TLSv1.2
```

## Handshake 인증

Browser의 표준 WebSocket API는 임의 Authorization Header를 넣기 어렵다. 이미 인증된 Same-Site, Secure, HttpOnly Session Cookie를 쓰거나, HTTPS API로 1회용 단기 Ticket을 발급받아 연결할 수 있다. 장기 JWT를 Query String에 넣으면 Proxy와 Access Log에 노출될 수 있으므로 피한다.

```java
@Component
@RequiredArgsConstructor
public class AuthenticatedHandshakeInterceptor implements HandshakeInterceptor {

    private final WebSocketTicketVerifier ticketVerifier;

    @Override
    public boolean beforeHandshake(
        ServerHttpRequest request,
        ServerHttpResponse response,
        WebSocketHandler handler,
        Map<String, Object> attributes
    ) {
        return extractTicket(request)
            .flatMap(ticketVerifier::verifyAndConsume)
            .map(principal -> {
                attributes.put(SessionPrincipal.ATTRIBUTE_NAME, principal);
                return true;
            })
            .getOrElse(false);
    }

    @Override
    public void afterHandshake(
        ServerHttpRequest request,
        ServerHttpResponse response,
        WebSocketHandler handler,
        Exception exception
    ) {
        // Handshake 이후 정리할 자원이 없으므로 비워 둔다.
    }

    private Optional<String> extractTicket(ServerHttpRequest request) {
        return UriComponentsBuilder.fromUri(request.getURI())
            .build()
            .getQueryParams()
            .getOrDefault("ticket", List.of())
            .stream()
            .findFirst();
    }
}
```

Ticket은 짧은 만료 시간, 한 번만 소비되는 식별자, User/Tenant 정보와 발급 목적을 가져야 한다. 검증 성공 후 즉시 사용 처리해야 Replay 공격을 줄일 수 있다.

## Message 단위 인가

```java
@Service
@RequiredArgsConstructor
public class VehicleSubscriptionService {

    private final SessionRegistry sessionRegistry;
    private final VehicleAccessPolicy vehicleAccessPolicy;
    private final WebSocketExceptionMapper exceptionMapper;

    public ServerWebSocketMessage subscribe(
        String sessionId,
        SubscribeVehicle command
    ) {
        return sessionRegistry.find(sessionId)
            .toEither(() -> new WebSocketError.UnknownSession(sessionId))
            .filterOrElse(
                session -> vehicleAccessPolicy.canRead(
                    session.principal().tenantId(),
                    session.principal().userId(),
                    command.vehicleId()
                ),
                session -> new WebSocketError.Forbidden(command.vehicleId())
            )
            .map(session -> session.subscribe(command.vehicleId()))
            .map(updated -> new ServerWebSocketMessage.SubscriptionAccepted(
                command.vehicleId(),
                updated.lastSequence()
            ))
            .getOrElseThrow(exceptionMapper::toException);
    }
}
```

Client가 보낸 Tenant ID를 신뢰하지 않고 인증된 Principal의 Tenant를 사용한다. 권한 실패 이유에 내부 Resource 존재 여부가 노출되지 않도록 Error 응답도 설계한다.

## Browser 재연결

```javascript
const connect = async ({ afterSequence = 0, attempt = 0 } = {}) => {
  const { ticket } = await fetch("/api/websocket-tickets", {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRF-TOKEN": readCsrfToken() }
  }).then(requireSuccessfulJson);

  const socket = new WebSocket(
    `wss://realtime.example.com/ws/vehicle-locations?ticket=${encodeURIComponent(ticket)}`
  );

  socket.addEventListener("open", () => {
    socket.send(JSON.stringify({
      messageId: crypto.randomUUID(),
      type: "SUBSCRIBE_VEHICLE",
      schemaVersion: 1,
      payload: { vehicleId: selectedVehicleId(), afterSequence }
    }));
  });

  socket.addEventListener("message", event => {
    const envelope = JSON.parse(event.data);
    persistLastSequence(envelope.sequence);
    renderVehicleLocation(envelope.payload);
  });

  socket.addEventListener("close", event => {
    if (!event.wasClean) {
      const delay = Math.min(30_000, 500 * 2 ** attempt) * (0.5 + Math.random());
      window.setTimeout(
        () => connect({ afterSequence: readLastSequence(), attempt: attempt + 1 }),
        delay
      );
    }
  });
};
```

Ticket을 재사용하지 않고 재연결마다 새로 발급한다. 무제한 즉시 재시도 대신 Exponential Backoff와 Jitter를 사용한다.

## 운영 점검표

- Certificate 만료를 사전에 Alert하고 자동 Rotation을 검증한다.
- HSTS를 적용하고 Plain `ws://` 연결을 제공하지 않는다.
- Origin은 정확한 HTTPS Host Allow List로 제한한다.
- Handshake와 Message Rate Limit을 별도로 둔다.
- 최대 Message 크기, Session별 Pending Byte, Idle Timeout을 제한한다.
- Token, Ticket, Cookie와 Message 본문을 Log에 남기지 않는다.
- 비정상 종료율, 인증 실패율, Forbidden 수와 Slow Consumer 수를 관측한다.
- 배포 전 TLS 종료 지점부터 Application까지 실제 Upgrade 통합 Test를 수행한다.

## 기억할 점

WSS는 WebSocket의 전송 구간을 안전하게 만들 뿐이다. 실제 운영 보안은 TLS, 안전한 Credential 전달, Origin 검사, Resource별 인가, Rate Limit과 Credential Rotation이 모두 있어야 완성된다.

# Reference

- [RFC 6455 - The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [Spring WebSocket](https://docs.spring.io/spring-framework/reference/web/websocket.html)
