---
id: Quartz
started: 2025-05-02
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# Quartz
## Quartz란?
Quartz는 오픈 소스 작업 스케줄러 라이브러리로서, Java 애플리케이션 내에서 작업을 예약하고 실행하는 데 사용된다. Quartz를 사용하면 특정 시간 또는 간격으로 반복되는 작업을 정의하고 관리할 수 있다.
### Quartz는 왜 사용할까?
Quartz는 다양한 스케줄링 요구 사항을 충족할 수 있는 강력하고 유연한 스케줄링 메커니즘을 제공한다. Quartz를 사용하면 다음과 같은 작업을 수행할 수 있다.
*   **정기적인 작업 실행**: 매일, 매주, 매월 등 특정 시간에 반복되는 작업을 실행한다.
*   **특정 이벤트 발생 시 작업 실행**: 특정 이벤트가 발생했을 때 작업을 실행한다.
*   **복잡한 스케줄링 규칙 정의**: cron 표현식을 사용하여 복잡한 스케줄링 규칙을 정의한다.
*   **작업 상태 관리**: 작업의 실행 상태, 실행 시간 등을 관리한다.
*   **분산 환경 지원**: 클러스터링 기능을 통해 분산 환경에서 작업을 실행한다.
### Quartz의 장점과 단점
**장점:**
*   **강력하고 유연한 스케줄링**: 다양한 스케줄링 요구 사항을 충족할 수 있다.
*   **다양한 기능 제공**: 작업 상태 관리, 분산 환경 지원 등 다양한 기능을 제공한다.
*   **오픈 소스**: 자유롭게 사용하고 수정할 수 있다.
*   **활발한 커뮤니티**: 많은 사용자와 개발자가 있어 지원을 받기 쉽다.
**단점:**
*   **설정 복잡성**: 초기 설정 및 구성이 복잡할 수 있다.
*   **학습 곡선**: Quartz API 및 개념을 이해하는 데 시간이 걸릴 수 있다.
*   **무거운 라이브러리**: 다른 경량 스케줄러에 비해 라이브러리 크기가 크다.
### Quartz 사용 예시
*   **데이터베이스 백업**: 매일 특정 시간에 데이터베이스를 백업한다.
*   **이메일 발송**: 매주 월요일 아침에 뉴스레터를 발송한다.
*   **보고서 생성**: 매월 말에 보고서를 생성한다.
*   **주식 시세 업데이트**: 주기적으로 주식 시세를 업데이트한다.
*   **시스템 모니터링**: 주기적으로 시스템 상태를 모니터링하고 알림을 보낸다.
## Java Spring Quartz 구현 예시
### 1. 의존성 추가
Spring Boot 프로젝트에 `spring-boot-starter-quartz` 의존성을 추가해야 한다.
```kotlin title="build.gradle.kts"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-quartz")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```
### 2. Job 구현
```java title="SampleJob.java"
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.stereotype.Component;

@Component
public class SampleJob implements Job {

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        System.out.println("SampleJob executed at " + new java.util.Date());
    }
}
```
*   `Job` 인터페이스를 구현하여 작업을 정의한다.
*   `execute()` 메서드를 오버라이드하여 작업 내용을 구현한다.
### 3. JobDetail 설정
```java title="QuartzConfig.java"
import org.quartz.JobBuilder;
import org.quartz.JobDetail;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class QuartzConfig {

    @Bean
    public JobDetail sampleJobDetail() {
        return JobBuilder.newJob(SampleJob.class)
                .withIdentity("sampleJob")
                .storeDurably()
                .build();
    }
}
```
*   `JobDetail`은 작업의 메타데이터를 정의한다.
*   `JobBuilder`를 사용하여 `JobDetail`을 생성한다.
*   `withIdentity()` 메서드를 사용하여 작업의 이름을 지정한다.
*   `storeDurably()` 메서드를 사용하여 작업이 영구 저장되도록 설정한다.
### 4. Trigger 설정
```java title="QuartzConfig.java"
import org.quartz.CronScheduleBuilder;
import org.quartz.Trigger;
import org.quartz.TriggerBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class QuartzConfig {

    @Bean
    public Trigger sampleJobTrigger(JobDetail sampleJobDetail) {
        return TriggerBuilder.newTrigger()
                .forJob(sampleJobDetail)
                .withIdentity("sampleTrigger")
                .withSchedule(CronScheduleBuilder.cronSchedule("0/10 * * * * ?")) // 10초마다 실행
                .build();
    }
}
```
*   `Trigger`는 작업 실행 시점을 정의한다.
*   `TriggerBuilder`를 사용하여 `Trigger`를 생성한다.
*   `forJob()` 메서드를 사용하여 `Trigger`를 `JobDetail`과 연결한다.
*   `withIdentity()` 메서드를 사용하여 `Trigger`의 이름을 지정한다.
*   `withSchedule()` 메서드를 사용하여 스케줄링 규칙을 정의한다.
*   `CronScheduleBuilder`를 사용하여 cron 표현식을 기반으로 스케줄링 규칙을 정의한다.
## 다른 스케줄링 기술 비교

| 기능       | Quartz                      | Spring Scheduling            | ScheduledExecutorService    |
| -------- | --------------------------- | ---------------------------- | --------------------------- |
| 복잡한 스케줄링 | 지원 (Cron 표현식)               | 지원 (Cron 표현식)                | 제한적 (fixedRate, fixedDelay) |
| 작업 관리    | Job, JobDetail, Trigger     | @Scheduled 어노테이션             | Runnable, Callable          |
| 분산 환경 지원 | 지원 (Clustering)             | 지원 안 함                       | 지원 안 함                      |
| 영속성      | 지원 (JobStore)               | 지원 안 함                       | 지원 안 함                      |
| 유연성      | 높음                          | 중간                           | 낮음                          |
| 설정       | 복잡함                         | 간단함                          | 간단함                         |
| 사용 사례    | 복잡한 스케줄링, 분산 환경, 영속적인 작업 관리 | 간단한 스케줄링, Spring Boot 애플리케이션 | 간단한 스케줄링, 스레드 풀 기반 작업 실행    |
### 사용 시 주의사항
*   **설정 관리**: Quartz 설정 파일을 올바르게 관리해야 한다.
*   **스레드 풀 설정**: 작업 실행에 필요한 스레드 풀 크기를 적절하게 설정해야 한다.
*   **트랜잭션 관리**: 작업 실행 중 예외 발생 시 트랜잭션을 롤백해야 한다.
*   **클러스터링**: 클러스터링 환경에서 작업 실행 시 데이터베이스 연결 설정을 올바르게 해야 한다.

Quartz는 Java 애플리케이션에서 복잡한 스케줄링 요구 사항을 충족할 수 있는 강력한 스케줄러이다. 하지만 설정이 복잡하고 학습 곡선이 높을 수 있으므로, 프로젝트의 요구사항에 따라 적절한 스케줄링 기술을 선택해야 한다.

# Reference
[Quartz 공식 문서](https://www.quartz-scheduler.org/)
[Spring Boot Quartz](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.quartz)