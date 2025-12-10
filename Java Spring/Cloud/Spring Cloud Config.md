---
id: Spring Cloud Config
started: 2025-09-24
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Config

## 1. 개요 (Overview)
**Spring Cloud Config**는 분산 시스템 환경에서 설정(Configuration) 정보를 중앙에서 통합 관리하고, 애플리케이션의 재배포 없이 설정을 동적으로 변경(Runtime Refresh)할 수 있게 해주는 서버-클라이언트 모델의 솔루션입니다.
MSA(Microservice Architecture)에서는 수십, 수백 개의 서비스가 존재하므로, 각 서비스의 `application.yml`을 개별적으로 관리하는 것은 불가능에 가깝습니다. 이를 해결하기 위해 설정을 Git, SVN, Vault, JDBC 등 외부 저장소에 분리하여 관리합니다.

---

## 2. 주요 아키텍처 (Architecture)

### 2.1 Config Server
- **역할**: 외부 저장소(Git 등)로부터 설정 파일을 읽어와서 REST API 형태로 제공합니다.
- **지원 저장소**: Git(기본, 추천), SVN, Vault(보안용), JDBC, Native(로컬 파일 시스템).
- **보안**: 설정 값의 암호화/복호화(Symmetric/Asymmetric)를 담당합니다.

### 2.2 Config Client
- **역할**: 애플리케이션 구동 시 Config Server에 접속하여 자신에게 필요한 설정을 받아와 Spring `Environment`에 바인딩합니다.
- **부트스트랩 컨텍스트 (bootstrap.yml)**: Config Client는 일반적인 로딩 시점보다 더 앞선 'Bootstrap Phase'에서 실행되어야 하므로, 서버 주소 등 필수 설정은 `application.yml`이 아닌 `bootstrap.yml`에 작성해야 합니다. (Spring Boot 2.4+부터는 `application.yml`로 통합 가능하지만, 레거시 호환성을 위해 알아두어야 함).

---

## 3. 핵심 기능 (Key Features)

### 3.1 동적 설정 반영 (@RefreshScope)
기본적으로 Spring Bean은 싱글톤으로 생성되며 초기화 시점에 프로퍼티 값이 주입됩니다. 따라서 설정 파일이 바뀌어도 이미 생성된 Bean에는 반영되지 않습니다.
`@RefreshScope` 애노테이션을 붙인 Bean은 `/actuator/refresh` 엔드포인트를 호출하거나 Spring Cloud Bus 이벤트를 수신했을 때, **Bean을 새로 생성(Proxy 재생성)**하여 변경된 설정 값을 반영합니다.

### 3.2 암호화 (Encryption)
DB 비밀번호, API 키 등 민감한 정보는 Git에 평문으로 저장하면 안 됩니다.
- **비대칭 키 (`rsa`)**: Private Key는 Config Server에, Public Key는 로컬에 저장. 값을 `{cipher}암호문` 형태로 저장하면 Config Server가 이를 해독해서 클라이언트에 전달합니다.
- **JASYPT**: Config Server의 기능이 아닌, 별도 라이브러리를 사용하여 애플리케이션 레벨에서 복호화하는 방식도 많이 쓰입니다. (`ENC(...)`)

---

## 4. 구현 및 설정 예제

### 4.1 Config Server 설정

**1) 의존성 추가 (build.gradle)**
```groovy
implementation 'org.springframework.cloud:spring-cloud-config-server'
```

**2) 애플리케이션 설정 (application.yml)**
```yaml
server:
  port: 8888

spring:
  application:
    name: config-server
  cloud:
    config:
      server:
        git:
          uri: https://github.com/my-org/config-repo.git
          default-label: main # 브랜치명
          # private repo인 경우
          username: my-username
          password: my-password 
```

**3) 메인 클래스**
```java
@EnableConfigServer
@SpringBootApplication
public class ConfigServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}
```

### 4.2 Config Client 설정

**1) 의존성 추가**
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-config'
implementation 'org.springframework.boot:spring-boot-starter-actuator' // Refresh용
```

**2) 클라이언트 설정 (bootstrap.yml)**
```yaml
spring:
  application:
    name: order-service # 저장소의 파일명 매핑 (order-service.yml)
  profiles:
    active: dev
  cloud:
    config:
      uri: http://localhost:8888
      fail-fast: true # 서버 연결 실패 시 앱 구동 중단
      
management:
  endpoints:
    web:
      exposure:
        include: refresh # /actuator/refresh 노출
```

**3) 동적 반영 테스트 Java Code**
```java
@RestController
@RefreshScope // 설정 변경 시 이 Bean을 Refresh 함
public class TestController {

    @Value("${custom.message:Default Message}")
    private String message;

    @GetMapping("/message")
    public String getMessage() {
        return message;
    }
}
```

---

## 5. 운영 전략 (Operational Strategies)

### 5.1 Spring Cloud Bus를 이용한 일괄 갱신
수십 개의 인스턴스가 떠 있는 상황에서 각각 `/actuator/refresh`를 호출하는 것은 비효율적입니다.
Spring Cloud Bus(Kafka/RabbitMQ)를 연동하면, Config Server에 `/actuator/bus-refresh`를 한 번만 호출해도 메시지 브로커를 통해 연결된 모든 클라이언트에게 "설정 갱신해!"라는 이벤트를 전파하여 **전체 인스턴스를 한 번에 갱신**할 수 있습니다.

### 5.2 고가용성 (High Availability)
Config Server가 다운되면 클라이언트가 기동되지 않을 수 있습니다.
- **Discovery Service 연동**: 클라이언트가 `uri`를 직접 박지 않고, Eureka 등을 통해 Config Server를 찾아가게 설정합니다. (`spring.cloud.config.discovery.enabled=true`)
- **로컬 캐시**: 클라이언트는 최초 기동 성공 시 설정을 로컬에 캐싱해두고, 서버 장애 시 이를 활용할 수 있습니다.

# Reference
- [Spring Cloud Config Official Doc](https://docs.spring.io/spring-cloud-config/docs/current/reference/html/)
- [Baeldung - Spring Cloud Config Guide](https://www.baeldung.com/spring-cloud-configuration)
- [Spring Cloud Bus Documentation](https://docs.spring.io/spring-cloud-bus/docs/current/reference/html/)
```