---
id: Virtual Thread와 Spring Boot
started: 2026-05-15
tags:
  - ✅DONE
  - Java
  - Concurrency
  - Spring-Boot
group:
  - "[[Java]]"
---
# Virtual Thread와 Spring Boot

## 1. 개요 (Overview)
**Virtual Thread**는 JVM이 관리하는 경량 Thread입니다. 요청마다 Thread를 사용하는 직관적인 Blocking Programming Model을 유지하면서, I/O 대기 중 Platform Thread 점유 비용을 줄여 높은 동시성을 처리할 수 있습니다.

Virtual Thread는 한 요청의 실행 시간을 줄이는 기술이 아닙니다. 동일한 Hardware에서 I/O 대기 작업을 더 많이 **동시에** 유지하는 기술입니다.

---

## 2. Platform Thread와 차이

| 항목 | Platform Thread | Virtual Thread |
|---|---|---|
| Scheduling | OS | JVM |
| 생성 비용 | 큼 | 작음 |
| 적합한 작업 | CPU·I/O 일반 | 대량 I/O 대기 |
| Pooling | 제한된 Pool 필수 | 작업별 생성 권장 |

```java
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    Future<String> result = executor.submit(externalClient::load);
    return result.get();
}
```

---

## 3. Spring Boot 적용

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

지원되는 Spring Boot 구성에서는 Web 요청과 Task Execution 등에 Virtual Thread가 적용됩니다. 실제 적용 범위는 사용하는 Servlet Container와 Executor Bean을 확인해야 합니다.

---

## 4. 성능 병목은 사라지지 않는다
Virtual Thread를 사용해도 다음 자원은 유한합니다.

- DB Connection Pool
- 외부 API Connection Pool
- CPU Core
- Memory
- 하위 서비스 처리량

동시 요청 수가 늘어 DB Connection을 기다리는 Virtual Thread가 수만 개 쌓일 수 있습니다. Semaphore, Bulkhead, Timeout, Backpressure가 여전히 필요합니다.

---

## 5. Pinning과 ThreadLocal
`synchronized` 블록 안의 Blocking I/O나 Native 호출은 Carrier Thread를 장시간 점유할 수 있습니다. JDK와 Library 버전에 따라 Pinning 동작이 다르므로 JFR과 부하 테스트로 확인합니다.

Virtual Thread 수가 많아지면 ThreadLocal에 큰 객체를 저장하는 비용도 커집니다. Request Context는 작게 유지하고 반드시 정리합니다.

---

## 6. 실무 사례 적용 관점
이 사례의 핵심 업무 애플리케이션, `gateway`, `metrics`는 Spring Virtual Thread를 활성화합니다. Blocking JPA, JDBC, Redis, 외부 HTTP 호출을 직관적인 방식으로 유지하면서 동시 요청을 처리합니다.

다만 Metrics Batch의 제한된 병렬성, DB Backpressure, Resilience4j Bulkhead는 Virtual Thread와 별도로 유지합니다. 이는 Thread 비용과 하위 자원 용량이 다른 문제이기 때문입니다.

---

## 7. JVM Scheduling 모델
Virtual Thread가 Blocking I/O를 만나면 JVM은 작업을 중단하고 Carrier Platform Thread를 다른 Virtual Thread에 사용합니다. I/O가 준비되면 다시 Scheduling합니다.

```text
Virtual Thread A -> JDBC 대기 -> Unmount
Carrier Thread   -> Virtual Thread B 실행
I/O 완료         -> A가 사용 가능한 Carrier에 Mount
```

CPU-bound 코드는 대기 중 Unmount할 기회가 없으므로 CPU Core 수 이상의 병렬 처리 이점을 얻지 못합니다.

## 8. Concurrency와 Parallelism
- **Concurrency**: 여러 작업이 진행 중인 상태
- **Parallelism**: 여러 작업이 같은 순간 실제 CPU에서 실행되는 상태

Virtual Thread는 Concurrency를 저렴하게 만들지만 Parallelism 상한은 CPU Core입니다. 대규모 JSON 변환·암호화·경로 계산은 별도 제한된 Executor가 필요할 수 있습니다.

## 9. Structured Concurrency
하나의 요청이 여러 하위 조회를 병렬로 수행할 때 작업의 수명 주기를 부모 Scope에 묶는 Structured Concurrency 개념이 유용합니다.

```text
Request Scope
  ├─ Member 조회
  ├─ Vehicle 조회
  └─ Policy 조회

하나 실패 또는 Deadline 초과
  -> 나머지 작업 취소
```

단순히 `CompletableFuture`를 흩뿌리면 요청이 끝난 뒤에도 작업이 남기 쉽습니다. 사용 중인 JDK의 Structured Concurrency 지원 상태와 Preview 여부를 확인합니다.

## 10. Pinning 진단
긴 `synchronized` 블록 안에서 I/O를 수행하지 않습니다. JFR의 Virtual Thread Pin 이벤트와 다음 JVM 진단 옵션을 개발 환경에서 활용할 수 있습니다.

```text
-Djdk.tracePinnedThreads=short
```

Pinning이 보이면 Lock 범위를 줄이거나 `ReentrantLock`, 비동기 API, Library Upgrade를 검토합니다. 짧은 Pinning까지 모두 제거할 필요는 없습니다.

## 11. ThreadLocal과 Context
Logging MDC, Security Context, Tenant Context가 ThreadLocal에 의존할 수 있습니다. Virtual Thread는 요청별 Thread를 제공하므로 단순하지만 다음을 지켜야 합니다.

- Context 설정과 정리를 `try/finally`로 묶습니다.
- 큰 객체를 ThreadLocal에 저장하지 않습니다.
- 별도 Executor로 넘길 때 Context 전파 정책을 확인합니다.
- InheritableThreadLocal에 암묵적으로 의존하지 않습니다.

## 12. DB Connection Pool과 Little's Law
Virtual Thread 수가 늘어도 DB Connection은 제한됩니다.

```text
동시 작업 수 ≈ 처리량 × 평균 체류 시간
```

DB Query가 느려지면 Connection 대기 Virtual Thread가 급증합니다. Connection Pool Pending 수, Query Timeout과 전체 Request Deadline을 관측해야 합니다.

## 13. 부하 테스트
Platform Thread와 Virtual Thread를 같은 조건에서 비교합니다.

- 처리량과 P95·P99 지연
- Platform Thread 수와 Context Switch
- Heap·Native Memory
- DB Pool Pending·Timeout
- CPU 사용률과 Pinning Event
- 장애 시 대기 작업 증가 속도

정상 상태 성능뿐 아니라 DB 지연과 외부 API Timeout 상황을 포함합니다.

---

## 14. 실무 사례 적용 진단과 개선 과제

Virtual Thread 사용 가능성은 있지만 DB Pool과 외부 API 동시성 한도는 그대로입니다. Thread 수 증가가 Hikari Connection 대기와 Provider Rate Limit을 가려 더 큰 Tail Latency를 만들 수 있습니다.

먼저 Platform Thread 대비 Load Test로 Throughput, P99, DB Pool Wait, Pinning Event를 비교합니다. `synchronized` I/O, ThreadLocal Tenant·Security Context, MDC 전파를 점검하고 Semaphore/Bulkhead로 하위 자원 동시성을 제한합니다.

완료 기준은 목표 부하에서 Pinning과 Queue가 허용 범위이고 Context 누수 Test가 통과하며, Virtual Thread 활성화 여부를 되돌릴 수 있는 운영 설정과 수치 근거가 있는 상태입니다.

---

# Reference
- [[k6 부하 테스트와 성능 검증]]
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
- [Spring Boot Virtual Threads](https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html#features.task-execution-and-scheduling.virtual-threads)
- [[Backpressure와 Load Shedding]]
