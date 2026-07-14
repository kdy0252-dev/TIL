---
id: Rsocket
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---

# RSocket

RSocket은 Reactive Streams의 요청량 신호를 Protocol 수준에 반영하는 Binary Messaging Protocol이다. 하나의 Connection에서 여러 Stream을 Multiplexing하고 Request/Response, Request/Stream, Fire-and-Forget, Channel 네 가지 상호작용을 제공한다.

## 먼저 알아야 할 Backpressure

생산자가 초당 10,000개를 만들지만 소비자가 1,000개만 처리할 수 있다면 무제한 Queue는 결국 Memory를 소진한다. Reactive Streams에서 소비자는 `request(n)`으로 지금 처리할 수 있는 개수를 알린다. RSocket의 Request/Stream과 Channel은 이 Demand를 Network 반대편까지 전달한다.

Backpressure가 데이터 유실을 자동으로 해결하지는 않는다. Connection 장애 후 반드시 처리해야 하는 업무 Event는 Kafka 같은 Durable Broker와 Idempotency 설계가 필요하다.

## 네 가지 상호작용

| 모델 | 입·출력 | 실제 예 |
| --- | --- | --- |
| Request/Response | 1 → 1 | 차량 현재 상태 조회 |
| Request/Stream | 1 → N | 관제 화면의 위치 Stream |
| Fire-and-Forget | 1 → 0 | 유실 허용 Telemetry 전송 |
| Channel | N ↔ N | Device Command와 Ack의 양방향 흐름 |

## Typed Contract

```java
public record VehicleStatusRequest(long vehicleId) {
}

public record VehicleStatusResponse(
    long vehicleId,
    VehicleOperatingStatus status,
    Instant observedAt
) {
}

public record LocationSubscriptionRequest(long vehicleId, long afterSequence) {
}

public record VehicleLocationResponse(
    long sequence,
    long vehicleId,
    BigDecimal latitude,
    BigDecimal longitude,
    Instant observedAt
) {
}
```

문자열 하나를 주고받는 예제와 달리 Schema Versioning이 가능한 DTO를 사용한다. Domain Model을 Wire에 그대로 노출하지 않는다.

## 인증 Metadata

RSocket Connection Setup 단계에 Authentication Metadata를 보내고 Server에서 Principal로 변환한다. 장기 Connection 중 권한이 바뀔 수 있으므로 민감한 Route는 요청 시점에도 권한을 확인한다.

```java
@Configuration
public class RSocketSecurityConfiguration {

    @Bean
    PayloadSocketAcceptorInterceptor rsocketInterceptor(RSocketSecurity security) {
        return security
            .authorizePayload(authorize -> authorize
                .setup().authenticated()
                .route("vehicle.status").hasAuthority("VEHICLE_READ")
                .route("vehicle.locations").hasAuthority("VEHICLE_READ")
                .anyRequest().denyAll()
            )
            .simpleAuthentication(Customizer.withDefaults())
            .build();
    }
}
```

예제는 이해를 위해 Simple Authentication을 보이지만 Production에서는 TLS를 적용하고 조직의 Token/OAuth2 정책에 맞는 Authentication Metadata를 사용한다.

## Application Port

```java
public interface VehicleRealtimeQuery {

    Mono<VehicleStatus> findStatus(long tenantId, long vehicleId);

    Flux<VehicleLocation> streamLocations(
        long tenantId,
        long vehicleId,
        long afterSequence
    );
}
```

Port는 RSocket Annotation을 알지 않는다. Transport Adapter가 인증 Principal과 Wire DTO를 Application 입력으로 변환한다.

## Server Adapter

```java
@Controller
@RequiredArgsConstructor
public class VehicleRSocketController {

    private final VehicleRealtimeQuery realtimeQuery;
    private final VehicleAccessPolicy accessPolicy;

    @MessageMapping("vehicle.status")
    public Mono<VehicleStatusResponse> status(
        VehicleStatusRequest request,
        Principal principal
    ) {
        return authenticated(principal)
            .filterWhen(user -> accessPolicy.canRead(user, request.vehicleId()))
            .switchIfEmpty(Mono.error(new AccessDeniedException("vehicle access denied")))
            .flatMap(user -> realtimeQuery.findStatus(user.tenantId(), request.vehicleId()))
            .map(VehicleStatusResponse::from);
    }

    @MessageMapping("vehicle.locations")
    public Flux<VehicleLocationResponse> locations(
        LocationSubscriptionRequest request,
        Principal principal
    ) {
        return authenticated(principal)
            .filterWhen(user -> accessPolicy.canRead(user, request.vehicleId()))
            .switchIfEmpty(Mono.error(new AccessDeniedException("vehicle access denied")))
            .flatMapMany(user -> realtimeQuery.streamLocations(
                user.tenantId(),
                request.vehicleId(),
                request.afterSequence()
            ))
            .map(VehicleLocationResponse::from);
    }

    private Mono<AuthenticatedUser> authenticated(Principal principal) {
        return Mono.justOrEmpty(principal)
            .ofType(AuthenticatedUser.class)
            .switchIfEmpty(Mono.error(new AccessDeniedException("authentication required")));
    }
}
```

Controller 내부에서 `subscribe()`하지 않는다. 반환한 `Mono`와 `Flux`를 Framework가 구독해야 Cancellation, Error와 Demand가 Connection 수명에 연결된다.

## Client Adapter

```java
@Component
@RequiredArgsConstructor
public class VehicleRSocketClient {

    private final RSocketRequester requester;

    public Mono<VehicleStatusResponse> findStatus(long vehicleId) {
        return requester
            .route("vehicle.status")
            .data(new VehicleStatusRequest(vehicleId))
            .retrieveMono(VehicleStatusResponse.class)
            .timeout(Duration.ofSeconds(2))
            .retryWhen(Retry.backoff(2, Duration.ofMillis(100))
                .filter(this::isTransient));
    }

    public Flux<VehicleLocationResponse> streamLocations(
        long vehicleId,
        long afterSequence
    ) {
        return requester
            .route("vehicle.locations")
            .data(new LocationSubscriptionRequest(vehicleId, afterSequence))
            .retrieveFlux(VehicleLocationResponse.class)
            .limitRate(64)
            .name("vehicle-location-rsocket")
            .tap(Micrometer.observation(registry));
    }

    private boolean isTransient(Throwable cause) {
        return cause instanceof TimeoutException
            || cause instanceof ApplicationErrorException error
                && error.getErrorCode() == ErrorFrameCodec.CONNECTION_ERROR;
    }
}
```

Retry는 멱등인 조회에만 제한한다. Fire-and-Forget Command를 무조건 Retry하면 중복 실행될 수 있으므로 Idempotency Key가 필요하다.

## Resumption을 오해하지 않기

RSocket Resumption은 짧은 전송 단절에서 Frame을 이어 보내기 위한 기능이다. Server Process 재시작, Resume Buffer 초과, 장기 Network Partition까지 보장하는 영속 Message Queue가 아니다. 중요한 Event는 마지막 처리 Sequence와 Durable Replay 경로를 둔다.

## 운영 설계

- TLS와 Setup Authentication을 적용한다.
- Route별 권한과 Payload 최대 크기를 제한한다.
- Keepalive 간격, Lifetime, Resume Buffer와 최대 Fragment 크기를 부하 특성에 맞춘다.
- Client별 Stream 수와 Request Rate를 제한한다.
- Connection 수, Request N, Cancellation, Reject, Error Code와 처리 지연을 측정한다.
- Server 종료 시 새 Setup을 거절하고 기존 Stream을 Drain한다.
- Timeout, Retry와 Circuit Breaker는 Route의 멱등성에 따라 다르게 적용한다.

## Test 순서

1. Setup Authentication 실패가 Connection을 거절하는지 검증한다.
2. Tenant가 다른 Vehicle Route를 호출할 때 거절되는지 검증한다.
3. StepVerifier로 Request/Response의 성공·Not Found·Timeout을 검증한다.
4. Request/Stream에서 소비 Demand보다 Server가 앞서지 않는지 검증한다.
5. Cancellation 시 DB Cursor와 Broker Subscription이 정리되는지 검증한다.
6. Network 단절, Resume Buffer 초과와 Server 재시작을 각각 검증한다.

## 기억할 점

RSocket의 장점은 문자열을 빠르게 보내는 데 있지 않다. Typed Route, Reactive Demand, Multiplexing과 양방향 모델을 명확한 운영 한도 안에서 사용할 때 가치가 있다. 영속성이나 Exactly-Once를 대신하지는 않는다.

# Reference

- [Spring Framework RSocket](https://docs.spring.io/spring-framework/reference/rsocket.html)
- [RSocket Protocol](https://rsocket.io/about/protocol/)
