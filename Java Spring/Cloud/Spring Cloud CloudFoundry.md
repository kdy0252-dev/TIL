---
id: Spring Cloud CloudFoundry
started: 2025-09-24
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud CloudFoundry

## 1. 개요 (Overview)
**Spring Cloud CloudFoundry**는 Spring Boot 애플리케이션을 **PaaS(Platform as a Service)** 의 대표 주자인 Cloud Foundry(CF) 환경에 자연스럽게 통합(Cloud Native)시킬 수 있도록 돕는 라이브러리 모음입니다.
과거에는 `Spring Cloud Connectors`를 통해 서비스 바인딩(DB, Redis 연결 등)을 처리했으나, 현재는 **Java CFEnv** 라이브러리가 그 역할을 대신하며, Spring Cloud CloudFoundry는 주로 **Discovery(서비스 검색)**와 **SSO(인증)** 같은 상위 레벨 기능을 제공합니다.

---

## 2. 핵심 기능 (Key Features)

### 2.1 Service Binding (Java CFEnv)
Cloud Foundry는 애플리케이션에 바인딩된 서비스(DB, Message Queue 등)의 접속 정보를 `VCAP_SERVICES`라는 환경 변수(JSON 형식)로 주입합니다.
Spring Boot 앱이 이를 수동으로 파싱하는 것은 번거롭기 때문에, `Java CFEnv`가 이를 대신 파싱하여 Spring Boot의 `DataSource`나 `RedisConnectionFactory` 등으로 자동 매핑(Auto-Configuration)해줍니다.

### 2.2 Service Discovery
Eureka 같은 별도의 디스커버리 서버 없이, Cloud Foundry의 내부 라우팅 테이블(GoRouter)을 이용하여 서비스를 찾을 수 있게 해줍니다.
`@EnableDiscoveryClient`를 사용하면 CF에 배포된 다른 앱의 호스트명과 포트를 조회할 수 있습니다.

### 2.3 SSO (Single Sign-On)
Cloud Foundry UAA(User Account and Authentication) 서버와 연동하여, 애플리케이션에 OAuth2 기반의 로그인을 쉽게 구현할 수 있습니다. `@EnableOAuth2Sso` (Legacy) 또는 Spring Security 5의 OAuth2 Client 기능을 활용합니다.

---

## 3. 작동 원리 (Mechanism)

### VCAP_SERVICES 구조
CF에 `cf bind-service my-app my-db` 명령을 내리면, 앱 컨테이너 재시작 시 다음과 같은 환경 변수가 주입됩니다.
```json
{
  "VCAP_SERVICES": {
    "mysql": [
      {
        "name": "my-db",
        "label": "mysql",
        "credentials": {
          "jdbcUrl": "jdbc:mysql://10.0.0.1:3306/db",
          "username": "user",
          "password": "password"
        }
      }
    ]
  }
}
```
**Java CFEnv**는 부팅 시 이 JSON을 읽어 `spring.datasource.url` 등의 프로퍼티 소스로 변환합니다.

---

## 4. 구현 및 설정 예제

### 4.1 의존성 추가 (Gradle)
```groovy
// 1. 서비스 바인딩 (DB 연결 등)
implementation 'io.pivotal.cfenv:java-cfenv-boot:2.4.1'

// 2. 디스커버리 (선택 사항)
implementation 'org.springframework.cloud:spring-cloud-cloudfoundry-discovery'
```

### 4.2 매니페스트 (manifest.yml) 설정
배포 시 어떤 서비스를 사용할지 정의합니다.
```yaml
applications:
  - name: trade-service
    memory: 1024M
    path: build/libs/trade-service.jar
    services:
      - trade-db      # MySQL Service
      - trade-message # RabbitMQ Service
    env:
      SPRING_PROFILES_ACTIVE: cloud
```

### 4.3 수동으로 서비스 정보 읽기 (Java)
자동 설정 외에 직접 VCAP 값을 읽어야 할 때 사용합니다.

```java
@Configuration
public class CloudConfig {

    @Bean
    public CfEnv cfEnv() {
        return new CfEnv();
    }

    @Bean
    public String myCustomUri(CfEnv cfEnv) {
        // 'custom-service'라는 태그를 가진 서비스를 찾아서 uri 값을 리턴
        return cfEnv.findServiceByTag("custom-service")
                    .getCredentials()
                    .getString("uri");
    }
}
```

---

## 5. 운영 시 고려사항 (Operational Considerations)

### 5.1 로컬 개발 환경 (Local Development)
로컬(IntelliJ/Eclipse)에서는 `VCAP_SERVICES` 환경 변수가 없습니다. 따라서 로컬과 클라우드 환경을 분리해야 합니다.
- **Local**: `application-default.yml` 또는 `application-local.yml`에 `localhost` DB 정보 기입.
- **Cloud**: 클라우드에 배포되면 `java-cfenv`가 활성화되어 로컬 설정을 덮어씀 (프로파일 분리 권장).

### 5.2 보안 (Security)
`VCAP_SERVICES`에는 DB 비밀번호 같은 민감 정보가 평문으로 들어있습니다. 
로그에 환경 변수를 전체 출력하는 실수(`System.getenv().forEach(...)`)를 하지 않도록 주의해야 합니다.

### 5.3 커넥션 풀
CF 라우터를 거칠 때 유휴 커넥션(Idle Connection)이 끊길 수 있습니다. `validationQuery`나 `testOnBorrow` 설정을 통해 끊진 연결을 감지하고 재연결하도록 설정해야 합니다.

# Reference
- [Java CFEnv GitHub](https://github.com/pivotal-cf/java-cfenv)
- [Spring Cloud Cloud Foundry Documentation](https://docs.spring.io/spring-cloud-cloudfoundry/docs/current/reference/html/)
- [Cloud Foundry Concepts](https://docs.cloudfoundry.org/concepts/)