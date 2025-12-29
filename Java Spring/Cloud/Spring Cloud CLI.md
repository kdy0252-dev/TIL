---
id: Spring Cloud CLI
started: 2025-09-07
tags:
  - ✅DONE
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud CLI

## 1. 개요 (Overview)
**Spring Cloud CLI (Command Line Interface)** 는 Spring Boot CLI의 기능을 확장하여, 복잡한 빌드 스크립트(Gradle/Maven) 없이 **Groovy 스크립트**만으로 Spring Cloud 마이크로서비스 애플리케이션을 빠르게 작성, 실행, 배포할 수 있게 해주는 도구입니다.

초기 아이디어나 프로토타입을 검증할 때("Config Server가 정말 이렇게 동작하나?") 매우 유용하며, `launcher` 기능을 통해 Kafka, Redis 같은 인프라스트럭처 서비스도 쉽게 띄울 수 있습니다.

---

## 2. 설치 방법 (Installation)

### 2.1 SDKMAN (권장)
가장 간편한 방법입니다.
```bash
sdk install springboot
sdk install spring-cloud-cli
```

### 2.2 Homebrew (macOS)
```bash
brew tap spring-io/tap
brew install spring-boot
brew install spring-cloud-cli
```

### 2.3 설치 확인
```bash
spring cloud --version
# Spring Cloud CLI v3.x.x
```

---

## 3. 주요 기능 및 사용법

### 3.1 빠른 프로토타이핑 (Groovy)
`@Grab` 어노테이션을 통해 필요한 라이브러리를 자동으로 다운로드 받습니다. 복잡한 `pom.xml` 없이 단 몇 줄의 코드로 서버를 띄울 수 있습니다.

**config-server.groovy**
```groovy
@Grab('spring-cloud-config-server')
@EnableConfigServer
class ConfigServer {}
```

**실행**
```bash
spring run config-server.groovy
```

### 3.2 암호화 유틸리티 (Encrypt/Decrypt)
Spring Cloud Config의 `Cipher` 기능을 사용할 때, 설정 값(비밀번호 등)을 암호화해야 합니다. CLI가 이를 도와줍니다. (JCE Extension 설치 필요할 수 있음)

```bash
# 암호화
spring encrypt mySuperSecretPassword --key mySymmetricKey
# 출력: 9384593845...

# 복호화
spring decrypt 9384593845... --key mySymmetricKey
```

생성된 암호문을 `application.yml`에 `{cipher}93845...` 형태로 넣으면 됩니다.

### 3.3 Launcher (Microservice Infrastructure)
개발 환경에서 Eureka, Config Server, Hystrix Dashboard, Kafka, Zipkin 등을 한 번에 띄워주는 기능입니다. `docker-compose`와 비슷하지만, Java 프로세스로 실행됩니다.

**사용 가능한 서비스 목록 확인**
```bash
spring cloud launcher --list
```

**실행 (Eureka와 Config Server 실행)**
```bash
spring cloud launcher --deploy eureka,configserver
```
기본적으로 `http://localhost:8761`(Eureka)과 `http://localhost:8888`(Config)이 뜹니다.

---

## 4. 확장 기능 (Extensions)
Spring Cloud CLI는 플러그인 형태로 기능을 확장할 수 있습니다.
```bash
spring install org.springframework.cloud:spring-cloud-cli-launcher:1.0.0.RELEASE
```

---

## 5. 한계점 및 고려사항 (Considerations)
- **프로덕션 용도 아님**: CLI는 개발 및 테스트, 프로토타이핑 용도입니다. 실제 운영 서비스는 Gradle/Maven으로 빌드하여 CI/CD 파이프라인을 태워야 합니다.
- **Groovy 의존성**: Groovy 언어에 익숙하지 않다면 사용이 꺼려질 수 있으나, 문법이 Java와 거의 유사하므로 큰 장벽은 아닙니다.
- **의존성 충돌**: `@Grab`으로 여러 라이브러리를 땡겨올 때 버전 충돌이 발생할 수 있습니다. Spring Boot의 BOM(Bill of Materials)이 대부분 해결해주지만 주의가 필요합니다.

# Reference
- [Spring Cloud CLI Project Page](https://spring.io/projects/spring-cloud-cli)
- [Official Documentation](https://docs.spring.io/spring-cloud-cli/docs/current/reference/html/)
- [Spring Boot CLI](https://docs.spring.io/spring-boot/docs/current/reference/html/cli.html)