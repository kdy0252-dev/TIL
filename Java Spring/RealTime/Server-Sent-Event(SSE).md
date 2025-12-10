---
id: Server-Sent-Event(SSE)
started: 2025-05-08
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# Server-Sent Events (SSE)
## SSE란?
Server-Sent Events (SSE)는 서버에서 클라이언트로 단방향으로 실시간 데이터 스트림을 전송하는 기술이다. HTTP 프로토콜을 기반으로 하며, 클라이언트는 SSE 엔드포인트에 연결을 유지하면서 서버에서 보내는 데이터를 실시간으로 수신한다.
### SSE의 특징
*   **단방향 통신**: 서버에서 클라이언트로만 데이터를 전송한다.
*   **HTTP 기반**: 기존 HTTP 프로토콜을 사용하므로 별도의 프로토콜 설정이 필요 없다.
*   **텍스트 기반**: 텍스트 형식으로 데이터를 전송하므로, 복잡한 데이터 구조를 표현하기 어렵다.
*   **간단한 구현**: WebSocket에 비해 구현이 간단하다.
### SSE는 언제 사용하면 좋을까?
*   **실시간 데이터 스트리밍**: 서버에서 클라이언트로 실시간으로 업데이트되는 데이터를 전송해야 할 때 (예: 주식 시세, 뉴스 피드).
*   **단방향 통신**: 서버에서 클라이언트로 데이터를 전송하는 것이 주 목적인 경우.
*   **간단한 구현**: WebSocket과 같은 복잡한 기술이 필요하지 않은 경우.
### Polling, Long Polling과 비교

| 기능     | Polling                  | Long Polling          | SSE                     | WebSocket       |
| ------ | ------------------------ | --------------------- | ----------------------- | --------------- |
| 통신 방향  | 단방향 (클라이언트 -> 서버)        | 단방향 (클라이언트 -> 서버)     | 단방향 (서버 -> 클라이언트)       | 양방향             |
| 실시간성   | 낮음 (주기적인 요청 필요)          | 중간 (이벤트 발생 시 응답)      | 높음 (실시간 데이터 스트리밍)       | 매우 높음           |
| 서버 부하  | 높음 (주기적인 요청 처리)          | 낮음 (이벤트 발생 시에만 응답)    | 낮음 (HTTP 기반 효율적인 연결)    | 높음 (지속적인 연결 유지) |
| 연결 유지  | 연결 없음 (매번 새로운 요청)        | 연결 유지 (Timeout 시 재연결) | 연결 유지 (HTTP 기반 지속적인 연결) | 연결 유지 (지속적인 연결) |
| 구현 복잡도 | 낮음                       | 중간                    | 중간                      | 높음              |
| 사용 사례  | 간단한 상태 확인, 주기적인 데이터 업데이트 | 채팅, 알림                | 실시간 데이터 스트리밍, 뉴스 피드     | 실시간 게임, 채팅      |
### SSE 구현 시 주의사항
*   **Connection 제한**: SSE는 HTTP 기반이므로, 브라우저의 Connection 제한에 영향을 받을 수 있다.
*   **오류 처리**: 연결이 끊어질 경우, 클라이언트가 재연결을 시도하도록 해야 한다.
*   **보안**: 인증 및 권한 부여를 통해 SSE 엔드포인트에 대한 접근을 제어해야 한다.
*   **메시지 형식**: SSE는 텍스트 기반이므로, 복잡한 데이터 구조를 표현하기 어렵다.
## Spring Boot SSE 구현 예시
### 1. 의존성 추가
Spring Boot 프로젝트에 `spring-boot-starter-webflux` 의존성이 추가되어 있어야 한다.
```kotlin title="build.gradle.kts"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```
### 2. Controller 구현
#### WebFlux
```java title="SseController.java(WebFlux)"
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.publisher.Sinks;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Controller;
import java.time.Duration;

@RestController
public class SseController {
	
    private final Sinks.Many<String> eventSink = Sinks.many().multicast().onBackpressureBuffer();
	
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> streamEvents() {
        return eventSink.asFlux().timeout(Duration.ofSeconds(30)); // 30초 Timeout
    }
	
    @PostMapping("/events")
    public Mono<Void> publishEvent(@RequestBody String event) {
        eventSink.emitNext(event, Sinks.EmitFailureHandler.FAIL_FAST);
        return Mono.empty();
    }
	
    @Scheduled(fixedRate = 5000)
    public void scheduledEvent() {
        String event = "Scheduled Event: " + System.currentTimeMillis();
        publishEvent(event).subscribe();
    }
}
```
#### Virtual Thread
```java title="SseController.java(Virtual Thread)"
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Controller;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@RestController
public class SseController {
	
    private final ExecutorService virtualThreadExecutor = Executors.newVirtualThreadPerTaskExecutor();
	
    @GetMapping("/stream")
    public SseEmitter streamEvents() {
        SseEmitter emitter = new SseEmitter(30000L); // 30초 Timeout
		
        virtualThreadExecutor.execute(() -> {
            try {
                for (int i = 0; i < 10; i++) {
                    emitter.send("Event " + i, MediaType.TEXT_PLAIN);
                    Thread.sleep(1000); // 1초 간격으로 이벤트 전송
                }
                emitter.complete();
            } catch (IOException | InterruptedException e) {
                emitter.completeWithError(e);
            }
        });
		
        return emitter;
    }
	
    @PostMapping("/events")
    public ResponseEntity<Void> publishEvent(@RequestBody String event) {
        emitters.forEach(emitter -> {
            virtualThreadExecutor.execute(() -> {
                try {
                    emitter.send(event, MediaType.TEXT_PLAIN);
                } catch (IOException e) {
                    emitter.completeWithError(e);
                    emitters.remove(emitter);
                }
            });
        });
        return ResponseEntity.ok().build();
    }
	
    @Scheduled(fixedRate = 5000)
    public void scheduledEvent() {
        String event = "Scheduled Event: " + System.currentTimeMillis();
        // 필요한 경우, 이벤트를 SseEmitter를 통해 전송
    }
}
```
*   `Sinks.Many`를 사용하여 이벤트를 발행하고, `Flux`를 통해 클라이언트에게 이벤트를 스트리밍한다.
*   `@GetMapping`의 `produces` 속성을 `MediaType.TEXT_EVENT_STREAM_VALUE`로 설정하여 Server-Sent Events (SSE) 형태로 데이터를 전송한다.
*   `timeout` 메서드를 사용하여 30초 Timeout을 설정한다.
*   `@Scheduled` 어노테이션을 사용하여 5초마다 이벤트를 발생시키는 예시를 추가했다.
### 3. Client 구현 (JavaScript)
```javascript title="client.js"
const eventSource = new EventSource('/stream');

eventSource.onmessage = (event) => {
    console.log('Received event:', event.data);
};

eventSource.onerror = (error) => {
    console.error('Error:', error);
};
```
*   `EventSource` 객체를 사용하여 SSE 엔드포인트에 연결한다.
*   `onmessage` 이벤트 핸들러를 통해 서버에서 보내는 데이터를 수신한다.
*   `onerror` 이벤트 핸들러를 통해 오류를 처리한다.

# Reference
https://velog.io/@black_han26/SSE-Server-Sent-Events