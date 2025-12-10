---
id: Rsocket
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# RSocket
## RSocket이란?
RSocket은 Facebook에서 개발한 Reactive Streams 기반의 바이너리 메시징 프로토콜이다. TCP, WebSocket, Aeron 등 다양한 전송 프로토콜 위에서 동작하며, 클라이언트와 서버 간의 효율적인 양방향 통신을 지원한다.
### RSocket의 특징
*   **양방향 통신**: 클라이언트와 서버가 동등한 역할을 수행하며, 양방향으로 메시지를 주고받을 수 있다.
*   **Reactive Streams 기반**: Reactive Streams의 Backpressure를 지원하여 데이터 처리 흐름을 제어할 수 있다.
*   **다양한 통신 모델**: Request/Response, Request/Stream, Fire-and-Forget, Channel 등 다양한 통신 모델을 지원한다.
*   **재개 (Resumption)**: 연결이 끊어졌을 때 세션을 재개하여 데이터를 다시 전송할 필요 없이 이어서 통신할 수 있다.
*   **다중화 (Multiplexing)**: 하나의 연결에서 여러 개의 스트림을 동시에 처리할 수 있다.
### RSocket은 왜 사용할까?
RSocket은 실시간 통신, 마이크로서비스 아키텍처, IoT 등 다양한 분야에서 활용될 수 있다. 특히 다음과 같은 장점 때문에 많은 관심을 받고 있다.
*   **높은 처리량**: Reactive Streams 기반으로 Backpressure를 지원하여 높은 처리량을 유지할 수 있다.
*   **낮은 지연 시간**: 양방향 통신과 다중화를 통해 지연 시간을 줄일 수 있다.
*   **유연한 통신 모델**: 다양한 통신 모델을 지원하여 다양한 요구사항을 충족할 수 있다.
*   **안정적인 연결**: 재개 기능을 통해 연결이 끊어졌을 때 데이터를 잃지 않고 이어서 통신할 수 있다.
### RSocket의 장점과 단점
**장점:**
*   **높은 성능**: Reactive Streams 기반의 Backpressure, 양방향 통신, 다중화를 통해 높은 성능을 제공한다.
*   **유연성**: 다양한 통신 모델을 지원하여 다양한 요구사항을 충족할 수 있다.
*   **안정성**: 재개 기능을 통해 연결이 끊어졌을 때 데이터를 잃지 않고 이어서 통신할 수 있다.
*   **다양한 플랫폼 지원**: Java, JavaScript, Python, Go 등 다양한 플랫폼에서 사용할 수 있다.
**단점:**
*   **러닝 커브**: 기존 HTTP 프로토콜에 비해 복잡한 개념이 많아 러닝 커브가 높을 수 있다.
*   **도구 부족**: WebSocket에 비해 개발 도구나 커뮤니티가 부족할 수 있다.
### Java Spring RSocket 구현 예시
**1. 의존성 추가**
Spring Boot 프로젝트에 `spring-boot-starter-rsocket` 의존성을 추가해야 한다.
```kotlin title="build.gradle.kts"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-rsocket")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```
**2. 서버 구현**
```java title="RSocketController.java"
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.stereotype.Controller;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;

@Controller
public class RSocketController {

    @MessageMapping("request-response")
    Mono<String> requestResponse(String request) {
        System.out.println("Received request: " + request);
        return Mono.just("Response to " + request);
    }

    @MessageMapping("request-stream")
    Flux<String> requestStream(String request) {
        System.out.println("Received stream request: " + request);
        return Flux.interval(Duration.ofSeconds(1))
                .map(i -> "Stream response " + i + " to " + request)
                .take(5);
    }

    @MessageMapping("fire-and-forget")
    Mono<Void> fireAndForget(String request) {
        System.out.println("Received fire-and-forget request: " + request);
        return Mono.empty();
    }

    @MessageMapping("channel")
    Flux<String> channel(Flux<String> request) {
        return request.map(s -> "Channel response to " + s);
    }
}
```
*   `@MessageMapping` 어노테이션을 사용하여 RSocket 요청을 처리할 메서드를 정의한다.
*   `requestResponse` 메서드는 Request/Response 모델을 처리한다.
*   `requestStream` 메서드는 Request/Stream 모델을 처리한다.
*   `fireAndForget` 메서드는 Fire-and-Forget 모델을 처리한다.
*   `channel` 메서드는 Channel 모델을 처리한다.
**3. 클라이언트 구현**
```java title="RSocketClient.java"
import io.rsocket.RSocketRequester;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Flux;

@Component
public class RSocketClient {

    @Bean
    CommandLineRunner rsocket(RSocketRequester.Builder builder) {
        RSocketRequester requester = builder.tcp("localhost", 7000);

        return args -> {
            requester.route("request-response")
                    .data("Hello RSocket!")
                    .retrieveMono(String.class)
                    .subscribe(response -> System.out.println("Response: " + response));

            requester.route("request-stream")
                    .data("Hello Stream!")
                    .retrieveFlux(String.class)
                    .subscribe(response -> System.out.println("Stream Response: " + response));

            requester.route("fire-and-forget")
                    .data("Hello Fire-and-Forget!")
                    .send()
                    .subscribe();

            Flux<String> channelData = Flux.just("Message 1", "Message 2", "Message 3");
            requester.route("channel")
                    .data(channelData)
                    .retrieveFlux(String.class)
                    .subscribe(response -> System.out.println("Channel Response: " + response));
        };
    }
}
```
*   `RSocketRequester`를 사용하여 서버에 RSocket 요청을 보낸다.
*   `route()` 메서드를 사용하여 요청의 라우팅 키를 지정한다.
*   `data()` 메서드를 사용하여 요청 데이터를 설정한다.
*   `retrieveMono()` 메서드를 사용하여 단일 응답을 받는다.
*   `retrieveFlux()` 메서드를 사용하여 스트림 응답을 받는다.
*   `send()` 메서드를 사용하여 Fire-and-Forget 요청을 보낸다.
### Java Spring WebSocket과 비교

| 기능              | WebSocket            | RSocket                                                         |
| --------------- | -------------------- | --------------------------------------------------------------- |
| 통신 모델           | 양방향                  | 양방향, Request/Response, Request/Stream, Fire-and-Forget, Channel |
| 프로토콜            | TCP 기반, HTTP Upgrade | TCP, WebSocket, Aeron 등 다양한 프로토콜 지원                             |
| Backpressure 지원 | 없음                   | Reactive Streams 기반으로 Backpressure 지원                           |
| 재개              | 지원 안 함               | 지원                                                              |
| 다중화             | 지원 안 함               | 지원                                                              |
| 사용 사례           | 실시간 채팅, 게임           | 마이크로서비스, IoT, 실시간 데이터 스트리밍                                      |
RSocket은 WebSocket에 비해 더 다양한 통신 모델과 높은 성능, 안정성을 제공하는 차세대 메시징 프로토콜이다. 하지만 러닝 커브가 높고 도구가 부족할 수 있으므로, 프로젝트의 요구사항에 따라 적절한 기술을 선택해야 한다.

# Reference
[Rsocket for spring 공식 문서](https://docs.spring.io/spring-framework/reference/rsocket.html)
[Rsocket](https://brunch.co.kr/@springboot/271)