---
id: ShedLock
started: 2025-05-02
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# ShedLock
## ShedLock이란?
ShedLock은 분산 환경에서 스케줄러의 동시 실행을 방지하는 데 사용되는 라이브러리이다. Spring Scheduler 또는 Quartz와 같은 스케줄러와 함께 사용하여 여러 인스턴스에서 동일한 작업이 동시에 실행되는 것을 방지한다.
### ShedLock은 왜 사용할까?
분산 환경에서 여러 서버 인스턴스가 동일한 스케줄링 작업을 실행하면 데이터 불일치, 중복 처리 등의 문제가 발생할 수 있다. ShedLock은 이러한 문제를 해결하기 위해 스케줄링 작업 실행 전에 Lock을 획득하고, 작업이 완료되면 Lock을 해제하여 동시 실행을 방지한다.
### ShedLock의 장점과 단점
**장점:**
*   **동시 실행 방지**: 분산 환경에서 스케줄링 작업의 동시 실행을 확실하게 방지한다.
*   **간단한 설정**: Spring Scheduler 또는 Quartz와 함께 사용하기 쉽다.
*   **다양한 Lock 저장소 지원**: 데이터베이스, Redis, Hazelcast 등 다양한 Lock 저장소를 지원한다.
*   **유연한 Lock 설정**: Lock 획득 시간, Lock 유지 시간 등을 유연하게 설정할 수 있다.
**단점:**
*   **추가 의존성**: ShedLock 라이브러리를 추가해야 한다.
*   **Lock 저장소 설정**: Lock 저장소를 설정하고 관리해야 한다.
*   **성능 오버헤드**: Lock 획득 및 해제 과정에서 약간의 성능 오버헤드가 발생할 수 있다.
### ShedLock 사용 예시
*   **데이터베이스 백업**: 여러 서버에서 동시에 데이터베이스 백업 작업을 실행하는 것을 방지한다.
*   **이메일 발송**: 여러 서버에서 동시에 동일한 이메일을 발송하는 것을 방지한다.
*   **보고서 생성**: 여러 서버에서 동시에 동일한 보고서를 생성하는 것을 방지한다.
*   **주식 시세 업데이트**: 여러 서버에서 동시에 주식 시세를 업데이트하는 것을 방지한다.
## Spring Scheduler + ShedLock 구현
### 1. 의존성 추가
Spring Boot 프로젝트에 `shedlock-spring` 및 Lock 저장소에 해당하는 의존성을 추가해야 한다.
```kotlin title="build.gradle.kts"
dependencies {
    implementation("net.javacrumbs.shedlock:shedlock-spring:4.0.0")
    implementation("net.javacrumbs.shedlock:shedlock-provider-jdbc-template:4.0.0") // JDBC (Database)
    runtimeOnly("com.h2database:h2") // H2 Database (테스트용)
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```
### 2. LockProvider 설정
Lock 저장소에 대한 설정을 정의한다.
```java title="ShedLockConfig.java"
import net.javacrumbs.shedlock.core.LockProvider;
import net.javacrumbs.shedlock.provider.jdbctemplate.JdbcTemplateLockProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;

@Configuration
public class ShedLockConfig {

    @Bean
    public LockProvider lockProvider(DataSource dataSource) {
        return new JdbcTemplateLockProvider(
            JdbcTemplateLockProvider.Configuration.builder()
                .withJdbcTemplate(new JdbcTemplate(dataSource))
                .usingDbTime() // DB 시간을 기준으로 Lock 만료 시간을 설정
                .build()
        );
    }
}
```
### 3. ShedLock 설정
`@SchedulerLock` 어노테이션을 사용하여 스케줄링 작업에 Lock을 적용한다.
```java
import lombok.extern.slf4j.Slf4j;
import net.javacrumbs.shedlock.annotation.SchedulerLock;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class SampleScheduler {

    @Scheduled(fixedRate = 5000)
    @SchedulerLock(name = "sampleSchedulerLock", lockAtLeastFor = "3s", lockAtMostFor = "10s")
    public void run() {
        log.info("SampleScheduler executed at " + new java.util.Date());
    }
}
```
*   `@SchedulerLock` 어노테이션을 사용하여 Lock을 적용한다.
    *   `name`: Lock의 이름을 지정한다.
    *   `lockAtLeastFor`: Lock을 최소 유지 시간을 지정한다. (작업이 완료되기 전에 Lock이 해제되는 것을 방지)
    *   `lockAtMostFor`: Lock을 최대 유지 시간을 지정한다. (작업이 실패하거나 멈춘 경우 Lock이 영원히 유지되는 것을 방지)
## Quartz vs Spring Scheduler + ShedLock

| 기능       | Quartz                  | Spring Scheduler + ShedLock |
| -------- | ----------------------- | --------------------------- |
| 복잡한 스케줄링 | 지원 (Cron 표현식)           | 지원 (Cron 표현식)               |
| 작업 관리    | Job, JobDetail, Trigger | @Scheduled 어노테이션            |
| 분산 환경 지원 | 지원 (Clustering)         | 지원 (ShedLock)               |
| 영속성      | 지원 (JobStore)           | 지원 안 함                      |
| 유연성      | 높음                      | 중간                          |
| 설정       | 복잡함                     | 간단함                         |
| 동시 실행 방지 | Clustering 설정 필요        | ShedLock 설정 필요              |
| 학습 곡선    | 높음                      | 낮음                          |
### Quartz Clustering vs ShedLock
*   **Quartz Clustering**: Quartz 자체에서 제공하는 분산 환경 지원 기능이다. 데이터베이스를 사용하여 작업 상태를 공유하고, Lock을 관리한다.
*   **ShedLock**: Spring Scheduler와 함께 사용하여 분산 환경에서 작업의 동시 실행을 방지하는 라이브러리이다. 데이터베이스, Redis, Hazelcast 등 다양한 Lock 저장소를 지원한다.

Quartz와 Spring Scheduler + ShedLock을 병행하여 사용하는 경우는 드물다. 일반적으로 둘 중 하나의 기술을 선택하여 사용한다. 하지만 다음과 같은 경우에는 병행 사용을 고려할 수 있다.
*   **기존 Quartz 프로젝트에 Spring Scheduler를 추가하는 경우**: 기존 Quartz 프로젝트에 새로운 기능을 추가하면서 Spring의 편리한 기능을 활용하고 싶을 때 Spring Scheduler를 함께 사용할 수 있다.
*   **Spring Scheduler에서 Quartz의 고급 기능을 사용하고 싶은 경우**: Spring Scheduler의 간단한 설정과 Quartz의 복잡한 스케줄링 기능을 함께 사용하고 싶을 때 병행 사용을 고려할 수 있다.
### 최근 추이
현업에서는 프로젝트의 요구사항과 팀의 숙련도에 따라 Quartz 또는 Spring Scheduler + ShedLock을 선택한다.
*   **Quartz**: 복잡한 스케줄링, 분산 환경 지원, 영속적인 작업 관리 등 고급 기능이 필요한 경우에 선호된다.
*   **Spring Scheduler + ShedLock**: 간단한 스케줄링, 분산 환경에서의 동시 실행 방지 기능이 필요한 경우에 선호된다. Spring Boot의 편리한 기능과 ShedLock의 간단한 설정을 통해 빠르게 개발할 수 있다.
최근에는 Spring Boot의 인기가 높아지면서 Spring Scheduler + ShedLock을 사용하는 프로젝트가 증가하는 추세이다.
### 사용 시 주의사항
*   **Lock 저장소 설정**: Lock 저장소를 올바르게 설정하고 관리해야 한다.
*   **Lock 획득 시간**: Lock 획득 시간을 너무 짧게 설정하면 작업이 제대로 실행되지 않을 수 있다.
*   **Lock 유지 시간**: Lock 유지 시간을 너무 길게 설정하면 다른 서버에서 작업을 실행할 수 없을 수 있다.
*   **예외 처리**: 작업 실행 중 예외 발생 시 Lock을 해제해야 한다.

ShedLock은 분산 환경에서 스케줄링 작업의 동시 실행을 방지하는 데 유용한 라이브러리이다. Spring Scheduler 또는 Quartz와 함께 사용하여 안정적인 스케줄링 시스템을 구축할 수 있다. 프로젝트의 요구사항과 팀의 숙련도에 따라 적절한 기술을 선택해야 한다.

# Reference
[ShedLock 공식 문서](https://www.shedlock.io/)
[ShedLock GitHub](https://github.com/lukas-krecan/ShedLock)