---
id: Spring Scheduler
started: 2025-03-21
tags:
  - ✅DONE
group: "[[Java Spring]]"
---
# Spring Scheduler
## Spring Scheduler란?
Spring Scheduler는 Spring 프레임워크에서 제공하는 스케줄링 기능이다. `@Scheduled` 어노테이션을 사용하여 메서드를 특정 시간 또는 간격으로 실행되도록 설정할 수 있다.
### Spring Scheduler는 왜 사용할까?
Spring Scheduler는 간단하고 편리하게 스케줄링 기능을 구현할 수 있도록 해준다. 별도의 스케줄링 라이브러리 없이 Spring 프레임워크 내에서 작업을 예약하고 실행할 수 있다.
### Spring Scheduler의 장점과 단점
**장점:**
*   **간단한 설정**: `@Scheduled` 어노테이션을 사용하여 간단하게 스케줄링을 설정할 수 있다.
*   **Spring 통합**: Spring 프레임워크와 완벽하게 통합되어 있어 Spring의 다양한 기능을 활용할 수 있다.
*   **별도 라이브러리 불필요**: 별도의 스케줄링 라이브러리 없이 Spring 프레임워크 내에서 스케줄링을 구현할 수 있다.
**단점:**
*   **제한적인 기능**: Quartz와 같은 전문 스케줄러에 비해 기능이 제한적이다.
*   **분산 환경 지원 미흡**: 분산 환경에서의 스케줄링을 지원하지 않는다.
*   **복잡한 스케줄링 규칙**: 복잡한 스케줄링 규칙을 정의하기 어렵다.
### Spring Scheduler 사용 예시
*   **정기적인 데이터 동기화**: 매일 특정 시간에 데이터베이스를 동기화한다.
*   **캐시 갱신**: 주기적으로 캐시를 갱신한다.
*   **로그 정리**: 주기적으로 오래된 로그 파일을 삭제한다.
*   **알림 발송**: 특정 조건이 충족되면 알림을 발송한다.
## Spring Scheduler 구현
### 1. Application 설정
먼저, `@Scheduled` 어노테이션을 사용하기 위해서는 Application 클래스에서 `@EnableScheduling` 어노테이션을 설정해야 한다.
```java
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@EnableScheduling
@SpringBootApplication
public class SpringBootApplication {
	public static void main(String[] args) {
    	SpringApplication.run(SpringBootApplication.class, args);
	}
}
```
### 2. Scheduler 구현
Scheduler를 구현할 때 스프링 빈에 컴포넌트가 등록되어야 한다. 아래 코드는 60초마다 작업이 실행되는 예시이다.
```java
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class SchedulerConfiguration {
    @Scheduled(fixedDelay = 60000)
    public void run() {
	    ...
    }
}
```
### 3. @Scheduled 속성
*   `fixedRate`: 작업 수행 시간과 상관없이 일정 주기마다 메서드를 호출한다 (ms 단위).
*   `fixedDelay`: 작업을 마친 후부터 타이머가 실행되어 메서드를 호출한다 (ms 단위).
*   `initialDelay`: 초기 지연 시간을 설정한다 (ms 단위).
*   `cron`: Cron 표현식을 사용하여 작업을 예약한다.
### 4. Cron 표현식
![[Pasted image 20250321085900.png]]
#### Cron Field 값으로 올 수 있는 것들
![[Pasted image 20250321085912.png]]
#### 정규표현식
![[Pasted image 20250321085952.png]]
#### 사용 예시
*   `0 0/5 * * * ?`: 매 5분마다 실행
*   `0 0 0/1 * * ?`: 매 1시간마다 실행
*   `0 0 12 * * ?`: 매일 낮 12시에
*   `0 15 10 ? * *`: 매일 오전 10:15분에 실행
*   `0 15 10 * * ?`: 매일 오전 10:15분에 실행
*   `0 * 14 * * ?`: 매일 오후 2:00에 시작해서 매분마다 실행하고 2:59분에 종료
*   `0 0/5 14,18 * * ?`: 매일 오후 2:00에 시작해서 5분마다 실행되어 2:55에 끝나고, 6:00에 시작하여 5분마다 실행되어 6:55에 종료
*   `0 0-5 14 * * ?`: 매일 오후 2:00에 시작하여 매분마다 실행하고 오후 2:05분에 종료
*   `0 10,44 14 ? 3 WED`: 3월 동안 오후 2:10과 2:44 실행
*   `0 15 10 ? * MON-FRI`: 주중 오전 10:15분에
*   `0 15 10 15 * ?`: 매달 15일 오전 10:15에
*   `0 15 10 L * ?`: 매월 말일 오전 10:15에
*   `0 15 10 ? * 6L`: 매월 마지막 금요일 오전 10:15에
*   `0 15 10 ? * 6#3`: 매월 3째주 금요일 오전 10:15에
### 5. Example
class 단은 생략하였다.
```java
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;

@Slf4j
public class ExampleScheduler {
	@Scheduled(fixedRate = 5000, initialDelay = 3000)
	public void run() {
		log.info("Scheduler 실행");
	}
}
```
### 6. Application.yaml 설정
`application.yaml` 파일에서 설정을 통해 스케줄러를 동작시킬 수도 있다.
```yaml title=application.yaml
schedule:
  cron: 0 0 0 * * *
  use: true
```
#### Use Case
```java
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@Slf4j
@RequiredArgsConstructor
public class CronTable {
    private final JobService jobService;
    
    @Value("${schedule.use}")
    private boolean useSchedule;
    
    @Scheduled(cron = "${schedule.cron}")
    public void mainJob() {
        try {
            if (useSchedule) {
                jobService.run();
            }
        } catch (InterruptedException e) {
            log.info("* Thread가 강제 종료되었습니다. Message: {}", e.getMessage());
        } catch (Exception e) {
            log.info("* Batch 시스템이 예기치 않게 종료되었습니다. Message: {}", e.getMessage());
        }
    }
}
```
## Spring Scheduler와 다른 스케줄링 기술 비교

| 기능       | Spring Scheduler             | Quartz                      | ScheduledExecutorService    |
| -------- | ---------------------------- | --------------------------- | --------------------------- |
| 복잡한 스케줄링 | 지원 (Cron 표현식)                | 지원 (Cron 표현식)               | 제한적 (fixedRate, fixedDelay) |
| 작업 관리    | @Scheduled 어노테이션             | Job, JobDetail, Trigger     | Runnable, Callable          |
| 분산 환경 지원 | 지원 안 함                       | 지원 (Clustering)             | 지원 안 함                      |
| 영속성      | 지원 안 함                       | 지원 (JobStore)               | 지원 안 함                      |
| 유연성      | 중간                           | 높음                          | 낮음                          |
| 설정       | 간단함                          | 복잡함                         | 간단함                         |
| 사용 사례    | 간단한 스케줄링, Spring Boot 애플리케이션 | 복잡한 스케줄링, 분산 환경, 영속적인 작업 관리 | 간단한 스케줄링, 스레드 풀 기반 작업 실행    |
### 사용 시 주의사항
*   **스레드 풀 설정**: 스케줄러가 사용하는 스레드 풀 크기를 적절하게 설정해야 한다.
*   **예외 처리**: 작업 실행 중 예외가 발생하면 스케줄러가 멈추지 않도록 예외 처리를 해야 한다.
*   **정확성**: Spring Scheduler는 정확한 시간에 작업을 실행하는 것을 보장하지 않는다.

Spring Scheduler는 간단하고 편리하게 스케줄링 기능을 구현할 수 있는 기술이다. 하지만 Quartz와 같은 전문 스케줄러에 비해 기능이 제한적이므로, 프로젝트의 요구사항에 따라 적절한 기술을 선택해야 한다.

# Reference
[Spring Scheduling Tasks](https://spring.io/guides/gs/scheduling-tasks/)
[Spring @Scheduled Annotation](https://www.baeldung.com/spring-scheduled-tasks)