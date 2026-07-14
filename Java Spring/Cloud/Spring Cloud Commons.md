---
id: Spring Cloud Commons
started: 2026-05-28
tags:
  - ✅DONE
  - Java
  - Spring-Cloud
  - Discovery
  - LoadBalancer
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Commons

## 1. Spring Cloud 구현체가 공유하는 추상화

Spring Cloud Commons는 Eureka, Consul 같은 특정 제품의 사용법보다 한 단계 아래에서 공통 계약을 제공한다. Application은 Service Discovery 구현이 달라져도 `DiscoveryClient`, Service Registration과 LoadBalancer라는 같은 추상화를 사용할 수 있다.

```text
Application
  -> Spring Cloud Commons API
       -> Eureka / Consul / Kubernetes 등 구현체
```

공통 추상화의 목적은 모든 Registry의 차이를 숨기는 것이 아니다. Application이 필요한 최소 계약을 안정적으로 사용하고 제품별 기능은 Adapter 경계에 가두는 것이다.

## 2. Service Discovery

Service Discovery는 논리적인 Service ID로 현재 실행 중인 Instance의 Host, Port와 Metadata를 찾는 과정이다. Pod나 VM의 IP가 바뀌어도 Client는 `inventory-service` 같은 이름을 사용한다.

```java
List<ServiceInstance> instances = discoveryClient
        .getInstances("inventory-service");
```

`DiscoveryClient`를 직접 사용하면 Instance 선택, Retry와 오류 처리를 Application이 맡게 된다. 일반적인 HTTP 호출에는 Spring Cloud LoadBalancer와 Client 통합을 사용하고, Registry 진단이나 특별한 Routing이 필요할 때 직접 조회한다.

## 3. Service Registration

Auto-registration이 활성화된 구현체는 Application 시작 시 자기 Host, Port와 Metadata를 Registry에 등록하고 종료 시 해제한다. 등록 성공과 Traffic 수신 가능 시점은 같지 않을 수 있다.

Application이 초기화되기 전에 Registry에 노출되면 준비되지 않은 Instance로 요청이 갈 수 있다. Health Check, Readiness와 Registration Lifecycle을 함께 설계해야 한다. Kubernetes에서는 Service와 EndpointSlice가 이 역할을 담당하므로 외부 Registry를 중복 도입할 필요가 있는지 먼저 검토한다.

## 4. Client-side Load Balancing

Spring Cloud LoadBalancer는 Service ID에 해당하는 Instance 목록에서 호출 대상을 선택한다.

```text
http://inventory-service/items/1
       |
       +-> instance-a:8080
       +-> instance-b:8080
```

기본적인 Round Robin 외에도 구현과 설정에 따라 Random, Zone·Metadata 기반 선택을 구성할 수 있다. Load Balancing은 Instance 선택만 해결한다. Timeout, Retry, Circuit Breaker와 Connection Pool은 별도 정책이다.

## 5. Retry와 부하 증폭

Instance 호출 실패를 다른 Instance에 Retry하면 일시 장애를 숨길 수 있지만, 느린 하위 서비스에 중복 요청을 보내 부하를 키울 수도 있다. 모든 요청을 동일하게 Retry하지 않는다.

- 조회처럼 멱등적인 요청인지 확인한다.
- Connect Timeout과 Read Timeout을 분리한다.
- 최대 시도 횟수와 전체 Deadline을 둔다.
- POST에는 Idempotency Key 같은 중복 방지 수단을 사용한다.
- Retry Metric을 원래 요청과 구분해 관측한다.

## 6. Spring Cloud Context와 Bootstrap

Spring Cloud Context는 부모·자식 ApplicationContext, 외부 설정과 Environment 변경을 지원하는 기반 기능을 제공한다. 외부 Config Server를 사용할 때 어떤 PropertySource가 우선하는지 이해하지 못하면 Local 설정이 무시되거나 운영 값이 예상과 다르게 덮어써질 수 있다.

설정의 출처와 우선순위를 Actuator `env`로 진단할 수 있지만 Secret 값은 반드시 마스킹한다.

## 7. Refresh Scope

`@RefreshScope` Bean은 설정 갱신 Event 뒤 기존 Instance를 폐기하고 다음 접근 시 새 설정으로 다시 생성될 수 있다. 이미 생성된 일반 Singleton의 Field가 자동으로 모두 바뀌는 기능은 아니다.

```java
@RefreshScope
@Component
class RemoteClientSettings {
    // 외부 설정을 사용하는 Bean
}
```

Connection Pool, Thread Pool처럼 상태와 Resource를 가진 Bean을 갱신하면 기존 연결의 종료와 새 연결 생성이 동시에 발생한다. 설정 변경을 무중단으로 처리할 수 있는지 검증하고, 안전하지 않은 값은 재배포로 변경한다.

## 8. Health Indicator

Discovery Client Health Indicator는 Registry 조회 가능 여부나 등록된 Service를 Health 정보로 노출할 수 있다. Registry가 잠깐 느리다고 Application Process를 재시작하면 장애를 증폭할 수 있다.

Registry 상태는 Liveness보다 Readiness와 운영 Alert에 가깝다. 이미 Cache한 Instance로 요청할 수 있는지, 새 Instance 발견이 반드시 필요한지에 따라 Traffic 수신 판단을 설계한다.

## 9. Kubernetes 환경에서의 선택

Kubernetes 안에서는 DNS, Service와 EndpointSlice가 기본 Service Discovery를 제공한다. 단순한 Pod 간 HTTP 통신에 별도 Discovery Client를 추가하면 Registry, DNS와 Client Cache라는 여러 진실의 원천이 생길 수 있다.

Spring Cloud Commons는 VM과 Kubernetes가 섞인 환경, 제품 독립적인 Client 추상화, Metadata 기반 Routing이 필요할 때 가치가 있다. Platform의 기본 Discovery로 충분하면 Kubernetes Service를 직접 사용하는 편이 단순하다.

## 10. 흔한 장애

- Registry에는 Instance가 있지만 Readiness가 끝나지 않아 초기 요청이 실패한다.
- 종료된 Instance가 Cache에 남아 간헐적인 Connection Refused가 발생한다.
- Retry가 장애 Instance로 반복되어 Latency와 부하가 증가한다.
- 설정 Refresh 뒤 Connection Pool이 동시에 재생성되어 Connection Storm이 생긴다.
- Kubernetes DNS와 외부 Registry가 서로 다른 Instance 목록을 제공한다.

## 11. 기억할 점

Spring Cloud Commons는 Service Discovery 제품 자체가 아니라 Discovery, Registration, Load Balancing과 설정 Context의 공통 계약이다. 추상화를 도입할 때는 Registry가 무엇인지보다 Instance 목록의 최신성, 준비 상태, Retry와 설정 갱신이 어떤 시간축으로 상호작용하는지 이해해야 한다.

# Reference
- [Spring Cloud Commons Reference](https://docs.spring.io/spring-cloud-commons/reference/spring-cloud-commons.html)
- [Spring Cloud LoadBalancer](https://docs.spring.io/spring-cloud-commons/reference/spring-cloud-commons/loadbalancer.html)
