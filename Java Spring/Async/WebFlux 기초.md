---
id: WebFlux 기초
started: 2025-04-26

tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# WebFlux 기초 (Spring WebFlux Basics)

## 1. 개요 (Overview)
**Spring WebFlux**는 Spring 5.0부터 도입된 **완전한 비동기(Asynchronous) 논블로킹(Non-blocking)** 리액티브 웹 프레임워크입니다.
기존의 Spring MVC는 Servlet API를 기반으로 한 **Thread-per-Request** 모델을 사용했습니다. 이 모델은 요청당 하나의 스레드를 할당하므로, I/O 작업(DB 조회, API 호출 등)이 발생하면 해당 스레드는 응답이 올 때까지 아무 일도 하지 못하고 대기(Blocking)해야 합니다.

반면, WebFlux는 **Event Loop** 기반의 리액티브 스트림(Reactive Streams)을 지원하여, 적은 수의 스레드로도 대량의 동시성 트래픽을 효율적으로 처리할 수 있습니다. Node.js의 비동기 모델과 유사하지만, Java의 강력한 타입 시스템과 Reactor 라이브러리의 풍부한 연산자를 활용할 수 있다는 장점이 있습니다.

---

## 2. 핵심 아키텍처 (Core Architecture)

### 2.1 Spring MVC vs WebFlux
| Feature | Spring MVC | Spring WebFlux |
| :--- | :--- | :--- |
| **I/O Model** | Blocking I/O (Synchronous) | Non-blocking I/O (Asynchronous) |
| **Server** | Servlet Container (Tomcat, Jetty) | Netty, Servlet 3.1+ Container |
| **Concurrency** | Thread-per-Request | Event Loop (Node.js style) |
| **Return Type** | Object, ResponseEntity | Mono<T>, Flux<T> |
| **Use Case** | CPU Intensive, Legacy, CRUD | High Concurrency, Streaming, Gateway |

### 2.2 리액티브 스트림즈 (Reactive Streams)
WebFlux는 **Reactive Streams** 표준 사양(Java 9 Flow API)을 구현한 **Project Reactor**를 기반으로 동작합니다.
- **Publisher**: 데이터를 생성하고 발행하는 주체 (`Mono`, `Flux`).
- **Subscriber**: 데이터를 구독하고 소비하는 주체.
- **Subscription**: Publisher와 Subscriber 간의 연결 고리. 데이터 요청(`request`)과 취소(`cancel`)를 관리.
- **Processor**: Publisher와 Subscriber의 역할을 동시에 수행 (데이터 가공).

### 2.3 백프레셔 (Backpressure)
리액티브 프로그래밍의 핵심 개념 중 하나입니다.
- **문제**: Publisher가 배출하는 속도가 Subscriber가 처리하는 속도보다 빠르면, Subscriber의 버퍼가 넘쳐서 **OOM(Out Of Memory)**이 발생할 수 있습니다 (Push 방식의 한계).
- **해결**: Subscriber가 자신이 처리할 수 있는 만큼만 Publisher에게 요청(`request(n)`)합니다 (Pull 방식 도입). 이를 통해 시스템의 안정성을 보장합니다.

---

## 3. Project Reactor 핵심 (Mono & Flux)

### 3.1 Mono<T>
- **0 또는 1개**의 데이터를 발행하는 Publisher입니다.
- `Optional<T>`의 리액티브 버전이라고 볼 수 있습니다.
- 주로 단건 조회(`findById`), HTTP 요청 결과 등에 사용됩니다.

### 3.2 Flux<T>
- **0개에서 N개**의 데이터를 발행하는 Publisher입니다.
- `List<T>`나 `Stream<T>`의 리액티브 버전입니다.
- 다건 조회(`findAll`), 무한 데이터 스트림(SSE, WebSocket) 등에 사용됩니다.

### 3.3 Cold vs Hot Sequence
- **Cold Publisher**: 구독(Subscribe)할 때마다 데이터가 처음부터 다시 생성됩니다. (대부분의 API 호출, DB 조회). CD 플레이어와 같습니다.
- **Hot Publisher**: 구독 여부와 상관없이 데이터가 계속 흐릅니다. 늦게 구독하면 이전 데이터는 놓칩니다. (실시간 방송, 센서 데이터). 라디오와 같습니다.

---

## 4. 스레드 모델과 스케줄러 (Threading & Schedulers)
WebFlux는 기본적으로 서버 시작 시 CPU 코어 수만큼의 스레드만 생성하여 운영합니다. 블로킹 코드를 넣으면 전체 서버가 멈출 수 있으므로 주의해야 합니다.

### 4.1 publishOn vs subscribeOn
- **`publishOn`**: 이 연산자 **이후**의 파이프라인 실행을 지정한 스레드 풀로 옮깁니다. (Downstream 영향)
- **`subscribeOn`**: 구독이 발생하는 시점, 즉 **소스(Source) 데이터 생성** 과정을 지정한 스레드 풀에서 실행합니다. (Upstream 영향)

### 4.2 Schedulers
- `Schedulers.immediate()`: 현재 스레드에서 실행.
- `Schedulers.single()`: 단일 스레드 재사용.
- `Schedulers.parallel()`: CPU 코어 수만큼의 스레드 풀 (CPU 집약적 작업용).
- `Schedulers.boundedElastic()`: I/O Blocking 작업(레거시 JDBC, 파일 읽기 등)을 감싸기 위한 유동적 스레드 풀. **블로킹 코드를 불가피하게 써야 할 때 필수.**

---

## 5. 예제 코드 (Implementation)

### 5.1 Annotated Controller (`@RestController`)
기존 MVC 스타일과 유사하여 러닝 커브가 낮습니다.

```java
@RestController
@RequestMapping("/products")
@RequiredArgsConstructor
public class ProductController {
    
    private final ProductRepository productRepository;

    // 단건 조회: Mono 반환
    @GetMapping("/{id}")
    public Mono<Product> getOne(@PathVariable String id) {
        return productRepository.findById(id)
                .switchIfEmpty(Mono.error(new NotFoundException("Product not found")));
    }

    // 다건 조회: Flux 반환 (Content-Type: application/json)
    @GetMapping
    public Flux<Product> getAll() {
        return productRepository.findAll()
                .filter(p -> p.getPrice() > 1000) // 1000원 이상 필터링
                .map(p -> {
                    p.setName(p.getName().toUpperCase()); // 이름 대문자로 변환
                    return p;
                });
    }

    // Server-Sent Events (SSE) 스트리밍
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<Product> streamProducts() {
        return productRepository.findAll()
                .delayElements(Duration.ofMillis(100)); // 0.1초 간격으로 전송 시뮬레이션
    }
}
```

### 5.2 Functional Endpoints (RouterFunction)
Spring MVC의 Controller 대신 함수형 스타일로 라우팅을 정의합니다.

```java
@Configuration
public class RouterConfig {

    @Bean
    public RouterFunction<ServerResponse> routes(ProductHandler handler) {
        return RouterFunctions.route()
                .GET("/products/{id}", handler::getOne)
                .GET("/products", handler::getAll)
                .build();
    }
}

@Component
@RequiredArgsConstructor
public class ProductHandler {
    private final ProductRepository repo;

    public Mono<ServerResponse> getOne(ServerRequest req) {
        String id = req.pathVariable("id");
        return repo.findById(id)
                .flatMap(p -> ServerResponse.ok().bodyValue(p))
                .switchIfEmpty(ServerResponse.notFound().build());
    }

    public Mono<ServerResponse> getAll(ServerRequest req) {
        return ServerResponse.ok().body(repo.findAll(), Product.class);
    }
}
```

### 5.3 WebClient (Non-blocking HTTP Client)
RestTemplate의 대안입니다.

```java
@Service
public class ExternalService {
    private final WebClient webClient;

    public ExternalService(WebClient.Builder builder) {
        this.webClient = builder.baseUrl("https://api.example.com").build();
    }

    public Mono<UserDto> getUser(String id) {
        return webClient.get()
                .uri("/users/{id}", id)
                .retrieve()
                .onStatus(HttpStatus::is4xxClientError, res -> Mono.error(new RuntimeException("Client Error")))
                .bodyToMono(UserDto.class)
                .timeout(Duration.ofSeconds(3)) // 3초 타임아웃
                .retryBackoff(3, Duration.ofSeconds(1)); // 실패 시 지수 백오프로 3회 재시도
    }
}
```

---

## 6. 주의사항: R2DBC vs JDBC
WebFlux를 도입하고도 **Blocking JDBC 드라이버(MySQL Connector/J 등)**를 사용하면, DB 쿼리를 수행하는 동안 Event Loop 스레드가 차단되어 WebFlux의 모든 장점이 사라집니다.

- **R2DBC (Reactive Relational Database Connectivity)**: 리액티브 프로그래밍을 지원하는 완전한 Non-blocking DB 드라이버입니다. (MySQL, PostgreSQL, H2 등 지원)
- **Spring Data R2DBC**: JPA와 유사한 Repository 패턴을 제공하지만, **Lazy Loading, Dirty Checking, 1차 캐시** 같은 JPA의 고급 영속성 컨텍스트 기능은 제공하지 않습니다. 이 점을 반드시 고려해야 합니다.

# Reference
- [Spring WebFlux Framework](https://docs.spring.io/spring-framework/reference/web/webflux.html)
- [Project Reactor](https://projectreactor.io/docs/core/release/reference/)
- [R2DBC](https://r2dbc.io/)