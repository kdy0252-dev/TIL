---
id: Server-Sent-Event(SSE)
started: 2025-05-08
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---

# Server-Sent Events(SSE)

SSE는 하나의 HTTP Response를 닫지 않고 Server가 Client로 Event를 계속 보내는 표준이다. Browser는 `text/event-stream` 응답을 읽고 연결이 끊기면 재연결한다. Client에서 Server로 명령도 보내야 한다면 일반 HTTP API를 함께 사용한다.

## SSE Event 형식

```text
id: 18421
event: vehicle-location-updated
retry: 3000
data: {"vehicleId":9102,"latitude":37.501,"longitude":127.039}

```

빈 줄 하나가 Event의 끝이다.

- `id`: Client가 마지막으로 처리한 Event 위치다.
- `event`: Client가 구독할 Event Type이다.
- `data`: 실제 Payload다. 여러 줄도 가능하다.
- `retry`: 재연결 대기 시간을 Millisecond로 제안한다.

Browser는 재연결할 때 마지막 `id`를 `Last-Event-ID` Header로 보낸다. 따라서 업무상 유실이 허용되지 않으면 Server가 해당 ID 이후 Event를 Durable Store에서 Replay해야 한다.

## 언제 선택하는가

| 요구사항 | 적합한 방식 |
| --- | --- |
| Server → Browser 알림·상태 갱신 | SSE |
| 빈번한 양방향 Message | WebSocket |
| Reactive Backpressure를 포함한 Service 간 Stream | RSocket 또는 Broker |
| 드물게 바뀌는 상태 | Conditional GET 또는 Polling |

SSE는 “항상 WebSocket보다 가볍다”가 아니라 단방향 HTTP Stream이라는 단순성이 요구사항과 맞을 때 선택한다.

## Production Architecture

```text
Domain Transaction -> Outbox -> Event Relay -> Durable Event Store
                                          \-> Live Event Hub
Browser -- Last-Event-ID --> SSE Controller -> Replay + Live Stream
```

Process Memory의 Sink만 사용하면 재시작 순간 Event가 사라지고 여러 Instance 사이에 Event가 공유되지 않는다. 실시간 전달과 복구 경로를 분리한다.

## Typed Event

```java
public record VehicleLocationEvent(
    long sequence,
    long tenantId,
    long vehicleId,
    BigDecimal latitude,
    BigDecimal longitude,
    Instant occurredAt
) {
}

public interface VehicleLocationEventQuery {

    Flux<VehicleLocationEvent> findAfter(long tenantId, long sequenceExclusive);

    Flux<VehicleLocationEvent> live(long tenantId);
}
```

Application Service는 연결 방식이 아니라 “어떤 Tenant가 어느 Sequence 이후 Event를 읽는가”만 표현한다.

## Replay와 Live Stream 연결

```java
@Service
@RequiredArgsConstructor
public class VehicleLocationStreamService {

    private static final Duration HEARTBEAT_INTERVAL = Duration.ofSeconds(15);

    private final VehicleLocationEventQuery eventQuery;

    public Flux<ServerSentEvent<VehicleLocationResponse>> stream(
        long tenantId,
        long afterSequence
    ) {
        Flux<ServerSentEvent<VehicleLocationResponse>> events = Flux.concat(
                eventQuery.findAfter(tenantId, afterSequence),
                eventQuery.live(tenantId)
            )
            .distinct(VehicleLocationEvent::sequence)
            .map(VehicleLocationResponse::from)
            .map(this::toServerSentEvent);

        Flux<ServerSentEvent<VehicleLocationResponse>> heartbeats = Flux
            .interval(HEARTBEAT_INTERVAL)
            .map(ignored -> ServerSentEvent.<VehicleLocationResponse>builder()
                .comment("heartbeat")
                .build());

        return Flux.merge(events, heartbeats);
    }

    private ServerSentEvent<VehicleLocationResponse> toServerSentEvent(
        VehicleLocationResponse response
    ) {
        return ServerSentEvent.<VehicleLocationResponse>builder(response)
            .id(Long.toString(response.sequence()))
            .event("vehicle-location-updated")
            .retry(Duration.ofSeconds(3))
            .build();
    }
}
```

`distinct`는 Replay를 읽는 사이 Live Stream에 같은 Sequence가 도착하는 경계 중복을 제거한다. 실제 대규모 Stream에서는 무제한 중복 기억을 피하도록 Sequence 경계를 저장해 필터링하거나 Broker Offset으로 연결한다.

## 인증된 Controller

```java
@RestController
@RequestMapping("/api/vehicle-locations")
@RequiredArgsConstructor
public class VehicleLocationSseController {

    private final VehicleLocationStreamService streamService;

    @GetMapping(produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<VehicleLocationResponse>> stream(
        @AuthenticationPrincipal AuthenticatedUser user,
        @RequestHeader(name = "Last-Event-ID", defaultValue = "0") long afterSequence
    ) {
        return streamService.stream(user.tenantId(), afterSequence);
    }
}
```

Tenant ID를 Query Parameter로 받지 않고 인증 Principal에서 가져온다. Browser `EventSource`는 임의 Authorization Header를 넣기 어려우므로 Same-Origin Session Cookie를 쓰거나 Header를 지원하는 Client를 선택한다.

## Browser Client

```javascript
const source = new EventSource("/api/vehicle-locations", { withCredentials: true });

source.addEventListener("vehicle-location-updated", event => {
  const location = JSON.parse(event.data);
  persistLastProcessedSequence(Number(event.lastEventId));
  updateVehicleMarker(location);
});

source.onerror = () => {
  showRealtimeConnectionState("reconnecting");
  // EventSource가 retry 값과 Last-Event-ID를 사용해 자동 재연결한다.
};

window.addEventListener("beforeunload", () => source.close());
```

## Backpressure와 느린 Client

HTTP Socket에 쓸 수 있는 속도보다 Event가 빠르면 Memory가 계속 늘 수 있다.

- 위치 정보처럼 최신 상태가 중요한 Stream은 Vehicle별 최신 값으로 합친다.
- 모든 Event 보존이 필요하면 Browser Connection을 Queue로 사용하지 말고 Durable Store에서 Replay한다.
- Connection별 Pending Byte와 최대 수명을 제한한다.
- Proxy Buffering을 끄고 Idle Timeout보다 짧은 Heartbeat를 보낸다.
- Active Connection, 전송 지연, Replay 수, Disconnect 원인과 Slow Consumer를 측정한다.

## Test 순서

1. `Last-Event-ID=0`에서 저장 Event가 Sequence 순서대로 내려오는지 검증한다.
2. 중간 Sequence로 재연결했을 때 이후 Event만 Replay되는지 검증한다.
3. Replay와 Live 경계의 중복이 제거되는지 검증한다.
4. 다른 Tenant Event가 섞이지 않는지 검증한다.
5. 느린 Client의 Buffer 한도와 Disconnect 정책을 부하 Test로 검증한다.
6. Load Balancer를 통과한 Heartbeat와 Proxy Buffering 설정을 검증한다.

## 기억할 점

SSE의 핵심은 `Flux.interval()`로 문자열을 보내는 것이 아니다. Event ID, 재연결 Replay, 인증된 Tenant 경계, 느린 Client 정책과 Proxy 설정까지 포함해야 운영 가능한 Stream이 된다.

# Reference

- [Spring WebFlux](https://docs.spring.io/spring-framework/reference/web/webflux.html)
- [HTML Living Standard - Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
