---
id: Spring Cloud Gateway 보안 라우팅
started: 2026-05-28
tags:
  - ✅DONE
  - Java-Spring
  - Gateway
  - Security
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Gateway: 라우팅, Load Balancing, OAuth2 Resource Server

## 1. 개요 (Overview)
**Spring Cloud Gateway**는 서비스 앞단에서 요청 경로를 판별하고 Filter를 적용한 뒤 적절한 Backend로 전달하는 API Gateway입니다. 이 사례에서는 단순 Reverse Proxy가 아니라 인증 경계, API Version Routing, Service Entry Point 역할을 수행합니다.

```text
Client
  -> Gateway
      ├─ JWT 검증
      ├─ Route Predicate
      ├─ Gateway Filter
      ├─ LoadBalancer
      └─ core application / metrics
```

---

## 2. Route 구성

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: members
          uri: ${app.base-url}
          predicates:
            - Path=/api/v3/members/**
          filters:
            - AuthHeaderFilter
```

- **Predicate**: Path, Method, Header, Host 등으로 Route 선택
- **Filter**: Header 변경, Prefix 제거, 인증 정보 전달, 로깅
- **URI**: 실제 서비스 또는 Load-balanced Service ID

Catch-all Route는 구체적인 Route 뒤에 배치해 우선순위 충돌을 피합니다.

---

## 3. OAuth2 Resource Server
Gateway는 Cognito가 발행한 JWT의 서명, 만료 시각, Issuer와 Claim을 검증하는 **Resource Server**입니다.

```java
@Bean
SecurityWebFilterChain security(ServerHttpSecurity http) {
    return http
            .authorizeExchange(exchange -> exchange
                    .pathMatchers("/actuator/health").permitAll()
                    .anyExchange().authenticated())
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .build();
}
```

JWT를 검증한 뒤 내부 서비스로 사용자 ID·역할·Tenant 정보를 전달할 때는 Client가 보낸 동일 Header를 먼저 제거하고 Gateway가 신뢰 가능한 값으로 다시 설정해야 합니다.

---

## 4. Spring Cloud LoadBalancer
**Spring Cloud LoadBalancer**는 논리적 Service ID에 연결된 여러 Instance 중 하나를 선택합니다. Kubernetes Service DNS나 Discovery Client와 결합할 수 있습니다.

Gateway에서 이미 Kubernetes Service가 Load Balancing한다면 Client-side LoadBalancer가 반드시 필요한지 확인해야 합니다. 이중 Load Balancing은 장애 Instance 제거 시점과 Retry 동작을 복잡하게 만들 수 있습니다.

---

## 5. 실무 사례 적용 관점
사례의 Gateway는 다음 경계를 갖습니다.

- `/api/v3/**`: Core Application Routing
- `/metrics/api/v3/**`: Metrics Routing과 Prefix 제거
- 서비스별 OpenAPI·Actuator Route
- 인증이 필요한 Route에 `AuthHeaderFilter` 적용
- Cognito JWT 검증 후 내부 인증 Context 전달
- 요청 Correlation ID 생성·전파

Gateway가 업무 권한까지 모두 판단하면 Domain 권한 규칙이 Gateway에 중복됩니다. Gateway는 인증과 거친 Route 권한을 담당하고, Resource 소유권과 세부 업무 권한은 Backend에서 재검증합니다.

---

## 6. 장애 대응
- Backend Timeout을 무한정 늘리지 않습니다.
- Retry는 멱등한 요청에만 제한하고 Jitter를 적용합니다.
- Gateway 자체에 Circuit Breaker를 둘 때 Backend의 정책과 중복되지 않게 합니다.
- Health·Readiness를 분리해 트래픽 수신 가능 여부를 표현합니다.
- Route별 응답 시간, 4xx·5xx, 연결 실패, 활성 연결 수를 관측합니다.

---

## 7. Reactive 실행 모델
Spring Cloud Gateway는 WebFlux·Netty 기반입니다. Filter에서 Blocking JDBC나 느린 동기 호출을 수행하면 적은 Event Loop Thread가 막혀 전체 Gateway가 지연됩니다.

```text
Event Loop
  -> Request A Filter가 Blocking
  -> 같은 Loop의 B, C 요청도 대기
```

Gateway Filter는 Header·Token·Routing처럼 짧은 비동기 작업에 집중합니다.

## 8. Route 우선순위
구체적인 Path와 Catch-all이 겹치면 Order에 따라 예상과 다른 Backend로 갈 수 있습니다. Route ID, Predicate와 적용 Filter를 Test Matrix로 관리합니다.

- `/api/v3/members/**`
- `/api/v3/**`
- `/metrics/api/v3/**`

OpenAPI·Actuator 같은 운영 경로가 일반 Catch-all 인증 정책을 우회하지 않는지 확인합니다.

## 9. Header 신뢰 경계
외부 Client가 `X-User-Id`, `X-Tenant-Id`, `X-Forwarded-*`를 위조할 수 있습니다.

1. 외부에서 들어온 내부 인증 Header를 제거합니다.
2. JWT를 검증합니다.
3. Claim을 검증된 내부 Header로 변환합니다.
4. Backend는 Gateway 경로와 Header 신뢰 조건을 제한합니다.

가능하면 mTLS·NetworkPolicy로 Backend 직접 접근도 막습니다.

## 10. JWT 검증
- Issuer와 Audience
- 서명 Algorithm
- 만료·Not-before와 Clock Skew
- JWK Rotation·Cache
- Role·Scope Mapping

JWT가 유효해도 해당 Tenant Resource 권한이 있다는 뜻은 아닙니다. 세부 Authorization은 Backend Domain에서 수행합니다.

## 11. Timeout 계층

```text
Client Deadline
  > Gateway Response Timeout
  > Backend 내부 외부호출 Timeout
```

안쪽 Timeout이 먼저 끝나야 바깥 계층이 의미 있는 오류를 반환하고 Resource를 정리할 수 있습니다.

## 12. Retry와 Body
Streaming Request Body는 Retry 시 다시 읽을 수 없을 수 있습니다. GET이라도 Backend 작업이 실제로 멱등한지 확인합니다. Gateway Retry와 Backend Retry가 곱해지지 않게 전체 Budget을 둡니다.

## 13. LoadBalancer 상태
Kubernetes Service DNS를 사용할지 Spring Cloud LoadBalancer Discovery를 사용할지 명확히 합니다. Health Check, Instance Cache와 Kubernetes Endpoint 제거의 지연이 서로 다를 수 있습니다.

## 14. Correlation과 관측
- Route ID별 요청 수·지연·상태
- Backend 연결 오류·Timeout
- JWT 검증 실패 유형
- Active Connection과 Event Loop 지연
- Request ID와 Trace ID 전파

사용자 Token이나 전체 Authorization Header는 Log에 남기지 않습니다.

## 15. 테스트
- Route별 Path·Method Matrix
- 위조 내부 Header 제거
- 만료·잘못된 Audience·JWK Rotation JWT
- Backend Timeout·Connection Refused
- 큰 Body와 Streaming
- Gateway 우회 Backend 접근 차단

---

## 16. 실무 사례 적용 진단과 개선 과제

Gateway는 JWT 검증, Route와 Actuator를 구성했지만 `ApiSecurityConfig`에 Actuator Role 기반 접근 제어 TODO가 남아 있습니다. 이는 운영 Endpoint가 Network 경계에만 의존할 수 있다는 명확한 보안 공백입니다.

즉시 `/actuator/health/liveness`처럼 Load Balancer에 필요한 최소 Endpoint만 공개하고 Prometheus는 전용 Network/ServiceAccount에서 접근하게 합니다. 나머지는 운영 Role을 요구하며 외부 Route에서 제거합니다. Route별 Timeout, Retry 가능 Method, Header Allowlist도 Contract Test로 고정합니다.

완료 기준은 비인가 사용자의 관리 Endpoint 접근이 차단되고, 공개 Endpoint Inventory와 Route 우선순위 Test가 있으며, Gateway 장애·Upstream Timeout이 서비스별 Metric으로 분리되는 상태입니다.

---

# Reference
- [Spring Cloud Gateway](https://docs.spring.io/spring-cloud-gateway/reference/)
- [Spring Security OAuth2 Resource Server](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/index.html)
- [Spring Cloud LoadBalancer](https://docs.spring.io/spring-cloud-commons/reference/spring-cloud-commons/loadbalancer.html)
- [[OAuth 2.0]]
- [[AWS Cognito]]
