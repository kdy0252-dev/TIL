---
id: Bucket4j
started: 2025-06-25
tags:
  - ✅DONE
group: []
---
# Bucket4j-RateLimiter
### 1단계: 프로젝트 의존성 추가
먼저 `pom.xml` (Maven) 또는 `build.gradle` (Gradle)에 Bucket4j 의존성을 추가합니다.
**Maven (`pom.xml`)**
```xml
<dependency>
    <groupId>com.bucket4j</groupId>
    <artifactId>bucket4j-core</artifactId>
    <version>8.10.0</version> </dependency>
```
### 2단계: Rate Limiting 로직을 담을 Interceptor 생성
Spring의 `HandlerInterceptor`를 구현하여 모든 요청이 컨트롤러에 도달하기 전에 Rate Limit을 검사하는 인터셉터를 만듭니다.
- **핵심 로직**:
    1. 요청마다 고유한 식별자(예: 클라이언트 IP 주소)를 기준으로 버킷(Bucket)을 관리합니다.
    2. 요청이 들어오면 해당 버킷에서 토큰을 1개 소모해봅니다.
    3. 소모에 성공하면 요청을 통과시키고, 실패하면(토큰 부족) HTTP 429 Too Many Requests 응답을 보냅니다.
```java
import com.bucket4j.Bandwidth;
import com.bucket4j.Bucket;
import com.bucket4j.Refill;
import io.github.bucket4j.ConsumptionProbe;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    // 각 IP 주소별로 Bucket을 저장하는 맵 (In-Memory 방식)
    private final Map<String, Bucket> cache = new ConcurrentHashMap<>();

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        
        // 클라이언트의 IP 주소를 식별자로 사용
        String ip = getClientIp(request);

        // 해당 IP에 대한 버킷을 찾거나, 없으면 새로 생성
        Bucket bucket = cache.computeIfAbsent(ip, this::createNewBucket);

        // 1개의 토큰을 소모 시도
        ConsumptionProbe probe = bucket.tryConsumeAndReturnRemaining(1);

        if (probe.isConsumed()) {
            // 토큰 소모 성공: 요청 허용
            // 남은 토큰 수를 헤더에 추가하여 클라이언트에게 알려줄 수 있음
            response.addHeader("X-Rate-Limit-Remaining", String.valueOf(probe.getRemainingTokens()));
            return true;
        } else {
            // 토큰 소모 실패: 요청 거부 (HTTP 429)
            long waitForRefillSeconds = Duration.ofNanos(probe.getNanosToWaitForRefill()).toSeconds();
            
            response.addHeader("X-Rate-Limit-Retry-After-Seconds", String.valueOf(waitForRefillSeconds));
            response.sendError(HttpStatus.TOO_MANY_REQUESTS.value(), "You have exhausted your API Request Quota");
            return false;
        }
    }

    private Bucket createNewBucket(String ip) {
        // 예: 1분에 10개의 요청을 허용하는 버킷 생성
        Refill refill = Refill.intervally(10, Duration.ofMinutes(1));
        Bandwidth limit = Bandwidth.classic(10, refill);
        return Bucket.builder().addLimit(limit).build();
    }
    
    private String getClientIp(HttpServletRequest request) {
        // 간단한 IP 추출 로직. X-Forwarded-For 헤더 등을 확인하는 로직 추가 가능
        return request.getRemoteAddr();
    }
}
```
### 3단계: Interceptor 등록
생성한 인터셉터가 동작하도록 Spring MVC 설정에 등록합니다.
```java
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Autowired
    private RateLimitInterceptor rateLimitInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // 특정 경로에만 인터셉터를 적용
        registry.addInterceptor(rateLimitInterceptor)
                .addPathPatterns("/api/**"); // 예: /api/로 시작하는 모든 경로에 적용
    }
}
```
### 4단계: 컨트롤러 작성
이제 평소처럼 컨트롤러를 작성하면, `/api/` 경로 밑의 모든 엔드포인트는 위에서 설정한 Rate Limiting 정책의 적용을 받게 됩니다.
```java
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/greetings")
public class GreetingController {

    @GetMapping
    public String greet() {
        return "Hello, World!";
    }

    @GetMapping("/private")
    public String privateGreet() {
        return "Hello, from a private endpoint!";
    }
}
```

이제 애플리케이션을 실행하고 1분 안에 10번 이상 `/api/v1/greetings`에 요청을 보내면, 11번째 요청부터는 **HTTP 429 Too Many Requests** 응답을 받게 됩니다.

---
### 심화: 분산 환경을 위한 Rate Limiting (feat. Redis)
위의 In-Memory 방식은 Pod가 하나일 때는 잘 동작하지만, **Pod가 여러 개인 분산 환경에서는 Pod마다 Rate Limit이 따로 계산되는 문제**가 있습니다. 이를 해결하려면 모든 Pod가 공유하는 중앙 저장소(예: Redis)를 사용해야 합니다.
Bucket4j는 JCache(JSR-107) 표준을 지원하므로, Redis를 JCache와 연동하여 쉽게 분산 Rate Limiter를 구현할 수 있습니다.
**1. 추가 의존성 (Maven `pom.xml`)**
```kotlin
implementation("com.bucket4j:bucket4j_jdk17-redis-common:8.14.0")  
implementation("com.bucket4j:bucket4j_jdk17-redisson:8.14.0")
```
**2. `application.yml` 에 Redis 설정 추가**
```ymal
spring:
  data:
    redis:
      host: localhost
      port: 6379
```
**3. 분산 Bucket 로직**
인터셉터 로직을 수정하여 Redis를 바라보도록 변경합니다.
```java
import io.github.bucket4j.Bandwidth;  
import io.github.bucket4j.Bucket;  
import io.github.bucket4j.BucketConfiguration;  
import io.github.bucket4j.distributed.proxy.ProxyManager;  
import jakarta.servlet.http.HttpServletRequest;  
import jakarta.servlet.http.HttpServletResponse;  
import java.time.Duration;  
import lombok.NonNull;  
import lombok.RequiredArgsConstructor;  
import lombok.extern.slf4j.Slf4j;  
import org.springframework.http.HttpStatus;  
import org.springframework.stereotype.Component;  
import org.springframework.web.method.HandlerMethod;  
import org.springframework.web.servlet.HandlerInterceptor;  
  
@Slf4j  
@Component  
@RequiredArgsConstructor  
public class RateLimitInterceptor implements HandlerInterceptor {  
  
    private final ProxyManager<String> proxyManager;  
  
    @Override  
    public boolean preHandle(  
        @NonNull HttpServletRequest request,  
        @NonNull HttpServletResponse response,  
        @NonNull Object handler) throws Exception {  
  
        if (!(handler instanceof HandlerMethod method)) {  
            return true;  
        }  
  
        RateLimit rateLimit = method.getMethodAnnotation(RateLimit.class);  
        if (rateLimit == null) {  
            return true;  
        }  
  
        // 사용자 요청 제한 키 생성  
        String userKey = rateLimit.key().isBlank()  
                         ? request.getRemoteAddr() + ":" + request.getRequestURI()  
                         : rateLimit.key();  
  
        // 사용자 제한 설정  
        Bandwidth userBandwidth = Bandwidth.builder()  
                                           .capacity(rateLimit.capacity())  
                                           .refillIntervally(  
                                               rateLimit.refillTokens(),  
                                               Duration.ofSeconds(rateLimit.refillDurationSeconds()))  
                                           .build();  
  
        BucketConfiguration userConfig = BucketConfiguration.builder()  
                                                            .addLimit(userBandwidth)  
                                                            .build();  
  
        Bucket userBucket = proxyManager.builder().build(userKey, () -> userConfig);  
  
        // 글로벌 요청 제한 키: method + path 기반, 단 key() 값이 있으면 사용  
        String globalKey = rateLimit.key().isBlank()  
                           ? "[GLOBAL]:" + request.getMethod() + ":" + request.getRequestURI()  
                           : "[GLOBAL]:" + rateLimit.key();  
  
        Bandwidth globalBandwidth = Bandwidth.builder()  
                                             .capacity(rateLimit.globalCapacity())  
                                             .refillIntervally(  
                                                 rateLimit.globalRefillTokens(),  
                                                 Duration.ofSeconds(rateLimit.globalRefillDurationSeconds()))  
                                             .build();  
  
        BucketConfiguration globalConfig = BucketConfiguration.builder()  
                                                              .addLimit(globalBandwidth)  
                                                              .build();  
  
        Bucket globalBucket = proxyManager.builder().build(globalKey, () -> globalConfig);  
  
        // 둘 다 통과해야 요청 허용  
        if (userBucket.tryConsume(1) && globalBucket.tryConsume(1)) {  
            log.info("[RateLimit] Allowed. userKey='{}', globalKey='{}'", userKey, globalKey);  
            return true;  
        }  
  
        log.warn("[RateLimit] Rate limit exceeded. userKey='{}', globalKey='{}'", userKey, globalKey);  
  
        response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());  
        response.setContentType("application/json");  
        response.getWriter().write("""  
                                   {                                     "error": "Too Many Requests",                                     "message": "You have exceeded your request rate limit."                                   }                                   """);  
        return false;  
    }  
}
```

# Reference