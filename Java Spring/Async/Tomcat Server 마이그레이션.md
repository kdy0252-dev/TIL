---
id: Tomcat Server 마이그레이션
started: 2025-07-12

tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Tomcat Server 마이그레이션 (Performance Optimization: Tomcat to Undertow)

## 1. 개요 (Overview)
Spring Boot의 기본 내장 WAS(Web Application Server)는 **Apache Tomcat**입니다. Tomcat은 전 세계적으로 가장 많이 사용되는 서블릿 컨테이너로, 안정성과 풍부한 레퍼런스를 자랑합니다. 하지만 전통적인 Thread-per-Request 모델과 다소 무거운 메모리 풋프린트(Footprint)로 인해, 고성능/대용량 트래픽 처리가 필요한 현대적인 MSA(Microservices Architecture) 환경에서는 때때로 병목이 되기도 합니다.

이 문서는 Spring Boot의 내장 서블릿 컨테이너를 **JBoss Undertow**로 교체하여 성능(Throughput, Latency, Memory)을 최적화하는 이유와 방법, 그리고 튜닝 포인트를 깊이 있게 다룹니다.

---

## 2. 왜 Undertow 인가? (Architecture Review)

### 2.1 Tomcat vs Undertow vs Jetty
| Feature | Tomcat | Undertow | Jetty |
| :--- | :--- | :--- | :--- |
| **기반 기술** | Java NIO (New I/O) | **XNIO (NIO Wrapper)** | Java NIO |
| **아키텍처** | Blocking이 혼재된 구조 | **Non-blocking 아키텍처** | Scalability 중심 |
| **메모리 사용** | 다소 높음 (Heap) | **매우 낮음** (Direct Memory 활용) | 낮음 |
| **장점** | 압도적인 범용성, 안정성 | **높은 처리량(TPS), 빠른 시작** | 웹소켓에 강점 |
| **개발사** | Apache Foundation | JBoss (Red Hat) | Eclipse Foundation |

### 2.2 Undertow의 핵심 기술: XNIO
Undertow는 **XNIO**라는 경량 저수준 I/O 계층 위에서 동작합니다.
- **I/O Thread**: 네트워크 연결 수립, 데이터 읽기/쓰기 등 비동기 작업을 전담하는 소수의 스레드입니다. (Non-blocking)
- **Worker Thread**: 실제 비즈니스 로직(Servlet 요청 처리, DB 조회 등)을 수행하는 스레드 풀입니다. (Blocking Tasks)
- 이 두 가지를 명확히 분리함으로써, 네트워크 I/O 대기 시간 동안 스레드가 낭비되는 것을 최소화합니다.

---

## 3. 마이그레이션 가이드 (Implementation)

Spring Boot의 Starter 메커니즘을 활용하면 코드 수정 없이 의존성 설정만으로 서버를 교체할 수 있습니다.

### 3.1 Gradle (`build.gradle`)
`spring-boot-starter-web`은 기본적으로 `spring-boot-starter-tomcat`을 포함하고 있습니다. 이를 제외하고 `spring-boot-starter-undertow`를 넣어야 합니다.

```groovy
configurations {
    // 모든 configuration에서 tomcat 모듈을 전역적으로 제외 (권장)
    all {
        exclude group: 'org.springframework.boot', module: 'spring-boot-starter-tomcat'
    }
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    
    // Undertow 추가
    implementation 'org.springframework.boot:spring-boot-starter-undertow'
}
```

### 3.2 Maven (`pom.xml`)
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <exclusions>
        <!-- 기본 Tomcat 의존성 제거 -->
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-tomcat</artifactId>
        </exclusion>
    </exclusions>
</dependency>

<!-- Undertow 의존성 추가 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-undertow</artifactId>
</dependency>
```

---

## 4. 고급 튜닝 및 설정 (Configuration)

`application.yml`을 통해 Undertow의 세부 동작을 제어할 수 있습니다. 기본값만으로도 충분히 빠르지만, 고부하 환경에서는 튜닝이 필수적입니다.

### 4.1 핵심 파라미터 튜닝
```yaml
server:
  undertow:
    # 1. Thread 설정
    threads:
      io: 4        # I/O 스레드 수. 보통 CPU 코어 수와 동일하게 설정. (너무 많으면 Context Switch 비용 증가)
      worker: 200  # 비즈니스 로직 처리용 워커 스레드. DB 커넥션 풀 사이즈와 연관지어 산정 필요.
    
    # 2. 버퍼 설정 (Direct Buffer 활용)
    buffer-size: 1024  # 버퍼 크기 (Byte). 너무 작으면 시스템 콜 빈번 발생.
    direct-buffers: true # JVM Heap 대신 Native Memory(Off-heap) 사용. GC 부하를 줄임.
    
    # 3. Access Log (Tomcat과 패턴이 다름)
    accesslog:
      enabled: true
      dir: ./logs
      pattern: "%t %a %m %U %s %Dms" # 날짜 IP Method URL Status 소요시간
```

### 4.2 Graceful Shutdown
앱 종료 시 진행 중인 요청을 안전하게 마무리하기 위한 설정입니다. (Kubernetes 배포 시 필수)
```yaml
server:
  shutdown: graceful # 기본값은 immediate
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s # 최대 30초 대기
```

---

## 5. 검증 및 벤치마크 (Verification)

서버 교체 후에는 반드시 **부하 테스트(Load Test)**를 통해 실제 성능 향상폭을 측정해야 합니다. 막연한 기대로 교체하는 것은 금물입니다.

### 5.1 테스트 도구
- **nGrinder / JMeter**: 시나리오 기반의 부하 생성. 실제 유저 트래픽 시뮬레이션.
- **wrk / ab**: 단순 HTTP 엔드포인트에 대한 한계 성능(Throughput) 측정.

### 5.2 테스트 체크리스트 (검증 항목)
1. **RPS/TPS (Requests Per Second)**: 동일 하드웨어에서 초당 처리량이 증가했는가?
    - *기대효과*: Simple Keep-Alive 요청 기준 약 10~20% 향상 가능.
2. **Latency (P99, P95)**: 99%의 요청 처리에 걸리는 지연 시간이 감소했는가?
3. **Memory Usage**: 동시 접속자 1000명 유지 시 힙 메모리 사용량 변화.
    - *기대효과*: Connection 객체가 가벼워 힙 메모리 절약 효과 큼.

### 5.3 주의사항 (Tomcat으로 돌아가야 할 때)
- **JSP 사용 시**: Undertow의 JSP 지원은 제한적입니다. Legacy JSP 프로젝트라면 Tomcat을 유지하세요.
- **AJP 프로토콜**: Apache Web Server와 AJP로 연동해야 한다면 Tomcat이 유리합니다.
- **익숙함**: 운영 팀이 Tomcat 트러블슈팅에만 익숙하다면, 굳이 Undertow로 바꿔서 런닝 커브 비용을 치를 필요는 없습니다.

# Reference
- [Spring Boot: Use Another Web Server](https://docs.spring.io/spring-boot/docs/current/reference/html/howto.html#howto.webserver.use-another)
- [Undertow Documentation](https://undertow.io/)
- [Tomcat vs Undertow Benkmark](https://www.baeldung.com/spring-boot-tomcat-jetty-undertow)