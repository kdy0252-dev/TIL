---
id: Spring Cloud DataFlow
started: 2025-10-15
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud DataFlow (SCDF)

## 1. 개요 (Overview)
**Spring Cloud DataFlow (SCDF)**는 마이크로서비스 기반의 **데이터 처리 파이프라인(Streaming & Batch)**을 구축하고 오케스트레이션하기 위한 통합 플랫폼입니다.
Spring Cloud Stream(실시간 스트리밍)과 Spring Cloud Task(단기 배치 작업)로 개발된 애플리케이션들을 시각적으로 정의하고, Kubernetes, Cloud Foundry 등의 플랫폼에 배포합니다.
과거의 **Spring XD**를 재설계하여, 모놀리식 런타임을 버리고 **Cloud Native** 아키텍처로 진화하였습니다.

---

## 2. 핵심 아키텍처 (Architecture)

### 2.1 구성 요소
1.  **SCDF Server**:
    - **Core**: 파이프라인 정의(DSL) 파싱, 유효성 검사, 상태 관리.
    - **Dashboard**: 웹 기반 UI. 드래그 앤 드롭으로 파이프라인 구성.
    - **REST API**: 모든 기능은 API로 노출됨 (`/jobs`, `/streams`).
2.  **Spring Cloud Skipper**:
    - **Continuous Deployment (CD)** 엔진.
    - SCDF Server의 요청을 받아 실제 플랫폼(Kubernetes, CF)에 애플리케이션을 배포, 업데이트, 롤백(Rollback) 합니다.
    - Blue/Green 배포 전략 등을 지원합니다. (※ SCDF 2.11부터는 Skipper가 옵션화되고 SCDF Server 내장 배포 기능이 강화되는 추세입니다.)
3.  **Target Platform**:
    - **Local**: 개발 테스트용.
    - **Kubernetes**: 프로덕션 표준.
    - **Cloud Foundry**: PaaS 환경.

### 2.2 Streaming vs Task
- **Stream**: 무한한 데이터 흐름 (`Running indefinitely`).
    - **Source** → **Processor** → **Sink** 구조.
    - 예: HTTP 요청 수신 → 데이터 변환 → Kafka로 전송.
- **Task**: 유한한 데이터 처리 (`Start -> End`).
    - 배치(Batch) 작업, DB 마이그레이션 등.
    - **Composed Task**: 여러 Task를 순차적(Directed Graph)으로 실행.

---

## 3. 기능 및 동작 방식 (Features & Mechanism)

### 3.1 DSL (Domain Specific Language)
Unix 파이프(`|`)와 유사한 직관적인 문법을 사용합니다.

**Stream DSL**
```bash
# HTTP로 데이터를 받아, Log로 출력
http | log

# 파일에서 읽어(transform), 필터링(process) 후, JDBC로 저장(sink)
file --dir=/tmp | filter --expression=payload.contains('error') | jdbc --tableName=ERRORS
```

**Task DSL**
```bash
# timestamp 앱 실행 후, 성공하면 myjob 앱 실행
timestamp && myjob
```

### 3.2 배포 메커니즘 (Deployment)
1.  사용자가 DSL로 스트림 정의 (`create stream`).
2.  배포 명령 수행 (`deploy stream`).
3.  SCDF가 Maven/Docker Registry에서 Artifact(Jar/Image)를 해결(Resolve).
4.  배포 정보를 Skipper(또는 Deployer)에게 전달.
5.  Skipper가 플랫폼 API(K8s API 등)를 호출하여 파드(Pod) 또는 앱 인스턴스 생성.
6.  각 앱은 Spring Cloud Bindings를 통해 메시지 브로커(Kafka/RabbitMQ) 정보를 주입받아 자동으로 연결됨.

---

## 4. 구현 및 사용 예제

### 4.1 Custom Processor 개발 (Java)
SCDF에서 사용할 수 있는 `Processor` 애플리케이션을 개발합니다.

**의존성 (Gradle)**
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-stream-rabbit' // Binder
```

**코드 (`Function` 기반)**
```java
@SpringBootApplication
public class TransformProcessorApplication {

    public static void main(String[] args) {
        SpringApplication.run(TransformProcessorApplication.class, args);
    }

    // String을 받아 대문자로 변환하는 Processor
    @Bean
    public Function<String, String> uppercase() {
        return message -> {
            System.out.println("Processing: " + message);
            return message.toUpperCase();
        };
    }
}
```

**앱 등록 (SCDF Shell or Dashboard)**
```bash
app register --name my-transform --type processor --uri docker://myuser/transform-processor:v1
```

**스트림 생성**
```bash
stream create --name uppercase-stream --definition "http | my-transform | log" --deploy
```

### 4.2 Application Properties 전달
배포 시점에 프로퍼티를 오버라이딩 할 수 있습니다.

```bash
stream deploy uppercase-stream --properties "app.my-transform.logging.level.root=DEBUG, deployer.http.kubernetes.limits.memory=1024Mi"
```

---

## 5. 운영 시 고려사항 (Operational Considerations)

### 5.1 Monitoring (Prometheus & Grafana)
SCDF로 배포되는 수많은 마이크로서비스들의 상태를 개별적으로 확인하는 것은 불가능합니다.
- **Micrometer**: Spring Boot 앱에 기본 내장.
- **Prometheus Service Discovery**: K8s 환경에서 파드들을 자동 감지하여 메트릭 수집.
- **SCDF Dashboard**: 시각화된 데이터 흐름과 실시간 처리량을 제공.

### 5.2 Resource Management
- **Partitioning**: Kafka 파티션과 연동하여 병렬 처리(Parallelism) 구성.
    - `producer.partitionKeyExpression=payload.id`
    - `consumer.concurrency=3` (인스턴스 3개 실행)
- **State Management**: 스테이트풀한 연산(Windowing 등)을 할 경우 Kafka Streams나 별도의 State Store(Redis) 고려 필요.

# Reference
- [Spring Cloud DataFlow Microsite](https://dataflow.spring.io/)
- [SCDF Reference Guide](https://docs.spring.io/spring-cloud-dataflow/docs/current/reference/htmlsingle/)
- [Spring Cloud Skipper](https://github.com/spring-cloud/spring-cloud-skipper)