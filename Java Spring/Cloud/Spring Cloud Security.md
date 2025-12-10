---
id: Spring Cloud Security
started: 2025-07-11
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Security

## 1. 개요 (Overview)
**Spring Cloud Security**는 Spring Cloud 기반의 MSA 환경에서 보안, 특히 **OAuth2**와 **OIDC(OpenID Connect)** 기반의 인증 및 인가를 쉽게 구현할 수 있도록 지원하는 라이브러리 모음입니다.
과거에는 독자적인 기능을 많이 제공했으나, 현재는 대부분의 기능이 **Spring Security 5+**의 OAuth2 Client 및 Resource Server 기능으로 통합되었으며, Spring Cloud Security는 이를 MSA 환경(Gateway, FeignClient 등)에 맞게 연결해주는 접착제 역할을 주로 수행합니다.

---

## 2. MSA 인증 아키텍처 패턴

### 2.1 API Gateway 패턴 (Token Relay)
가장 일반적인 패턴으로, 모든 요청은 Gateway를 통과합니다.
1.  클라이언트는 Gateway로 요청을 보냅니다.
2.  Gateway가 인증 서버(Identity Provider - Keycloak, Auth0 등)와 연동하여 로그인(OAuth2 Login)을 처리합니다.
3.  인증이 완료되면 Gateway는 세션을 맺고, 백엔드 마이크로서비스로 요청을 라우팅할 때 **Access Token(JWT)을 헤더에 실어서(Token Relay)** 보냅니다.
4.  각 마이크로서비스는 이 토큰을 검증(Resource Server)하여 호출자가 누구인지 식별합니다.

### 2.2 서비스 간 통신 (Client Credentials)
사람의 개입 없이 서비스 A가 서비스 B를 호출할 때는 **Client Credentials Grant** 흐름을 사용합니다.
- Feign ClientInterceptor 등을 통해 자동으로 토큰을 발급받아 요청 헤더에 삽입합니다.

---

## 3. 핵심 기능 및 구성 요소

### 3.1 Token Relay (Gateway)
Gateway에서 로그인한 사용자의 OAuth2 Access Token을 다운스트림 서비스로 전달해주는 필터입니다.
`spring-cloud-starter-gateway`와 `spring-boot-starter-oauth2-client`를 함께 사용하면 설정만으로 활성화됩니다.

### 3.2 SSO (Single Sign-On)
여러 마이크로서비스가 하나의 인증 서버(Authorization Server)를 신뢰하게 함으로써, 한 번의 로그인으로 모든 서비스를 이용할 수 있게 합니다.

---

## 4. 구현 예제

### 4.1 API Gateway 설정 (OAuth2 Client + Token Relay)

**1) 의존성 추가**
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-gateway'
implementation 'org.springframework.boot:spring-boot-starter-oauth2-client' // 로그인 처리
implementation 'org.springframework.cloud:spring-cloud-starter-security' // Token Relay 등
```

**2) application.yml**
```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          keycloak:
            provider: keycloak
            client-id: gateway-client
            client-secret: my-secret
            authorization-grant-type: authorization_code
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
            scope: openid, profile, email
        provider:
          keycloak:
            issuer-uri: http://localhost:8080/realms/myrealm # OIDC Discovery

  cloud:
    gateway:
      default-filters:
        - TokenRelay # 핵심: 받은 토큰을 다운스트림으로 전달
      routes:
        - id: order-service
          uri: lb://ORDER-SERVICE
          predicates:
            - Path=/orders/**
```
- **TokenRelay 필터**: 이 필터가 있으면 Gateway가 가지고 있는 Access Token을 자동으로 `Authorization: Bearer <token>` 헤더에 담아 `order-service`로 보냅니다.

### 4.2 Resource Server (Microservice) 설정
Gateway가 넘겨준 토큰을 검증하는 서비스입니다.

**1) 의존성 추가**
```groovy
implementation 'org.springframework.boot:spring-boot-starter-oauth2-resource-server'
```

**2) SecurityConfig**
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(Customizer.withDefaults()) // JWT 검증 활성화
            );
        return http.build();
    }
}
```

**3) application.yml**
```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: http://localhost:8080/realms/myrealm
          # 혹은 jwk-set-uri 직접 지정
```
이렇게 설정하면 서비스는 Issuer(Keycloak)의 공개키를 조회하여 서명을 검증하고, 유효한 토큰인 경우 `Authentication` 객체를 생성합니다.

---

## 5. Feign Client 연동 (Service to Service)

서비스 A가 서비스 B를 호출할 때도 토큰을 전달해야 합니다. `RequestInterceptor`를 사용합니다.

```java
@Configuration
public class FeignConfig {

    @Bean
    public RequestInterceptor requestInterceptor() {
        return requestTemplate -> {
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (authentication instanceof JwtAuthenticationToken) {
                JwtAuthenticationToken jwtToken = (JwtAuthenticationToken) authentication;
                // 현재 스레드의 토큰을 꺼내서 다음 요청 헤더에 주입
                requestTemplate.header("Authorization", "Bearer " + jwtToken.getToken().getTokenValue());
            }
        };
    }
}
```

# Reference
- [Spring Cloud Security Project](https://spring.io/projects/spring-cloud-security)
- [Spring Security OAuth2 Client](https://docs.spring.io/spring-security/reference/servlet/oauth2/client/index.html)
- [Spring Cloud Gateway Token Relay](https://docs.spring.io/spring-cloud-gateway/docs/current/reference/html/#the-tokenrelay-gatewayfilter-factory)