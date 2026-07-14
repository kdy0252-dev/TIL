---
id: Spring Cloud Consul
started: 2025-09-16
tags:
  - ✅DONE
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Consul로 Service Discovery 구성하기

Application Instance의 주소가 고정되어 있다면 다른 Service가 `10.0.1.12:8080`처럼 직접 호출할 수 있다. 하지만 Auto Scaling, 장애 복구와 Rolling 배포가 시작되면 Instance의 IP와 수가 계속 바뀐다. 호출자가 이 변화를 직접 추적하는 방식은 곧 한계에 도달한다.

Service Discovery는 “현재 주문 Service의 건강한 Instance는 어디에 있는가?”라는 질문에 답하는 Registry를 둔다. Consul은 Service Catalog, Health Check, DNS와 HTTP API, KV 저장소와 Service Mesh 기능을 제공한다. Spring Cloud Consul은 Spring Boot Application을 이 기능들과 연결한다.

## 등록과 조회의 기본 흐름

```text
1. order-service 시작
2. Consul에 이름, IP, Port, Health Check 등록
3. Consul이 주기적으로 상태 확인
4. caller가 order-service의 건강한 Instance 조회
5. 선택한 Instance로 요청
6. 종료되거나 Check 실패한 Instance는 후보에서 제외
```

Service Discovery는 Load Balancer와 같은 말이 아니다. Discovery는 후보 주소를 찾고, Load Balancer는 후보 중 하나를 선택한다. Spring Cloud LoadBalancer를 사용하면 Application이 Consul에서 Instance 목록을 얻어 Client-side로 선택할 수 있다. Consul DNS를 사용하는 Proxy나 Gateway가 대신 선택할 수도 있다.

## Consul의 Control Plane

Consul Agent는 Server Mode와 Client Mode로 실행할 수 있다.

- **Server Agent**는 Service Catalog와 Consul State를 보관하고 Raft Consensus로 복제한다. 일반적으로 장애 허용을 위해 홀수 개 Server를 배치한다.
- **Client Agent**는 Node의 Service와 Check를 등록하고 Server 요청을 중계한다. Raft 투표에는 참여하지 않는다.

Raft는 Catalog와 설정처럼 순서가 중요한 상태를 Server 사이에 합의하는 데 사용한다. Agent Membership과 장애 감지는 Serf 기반 Gossip을 사용한다. 즉 “Consul은 Raft만 사용한다”가 아니라 목적이 다른 두 분산 Protocol을 함께 사용한다.

Application이 Consul Server HTTP Port에 직접 연결할 수도 있지만, VM 환경에서는 Local Client Agent를 두면 Agent가 Server 발견과 장애 전환을 담당한다. Kubernetes에서는 이미 Service와 Endpoint 기반 Discovery가 있으므로 Consul을 추가할 목적이 Service Mesh, Multi-runtime 연결 또는 일관된 Service Networking인지 먼저 확인한다.

## Service Registration과 Health Check

Registry에 주소가 있다는 사실만으로 요청 가능한 것은 아니다. Process는 살아 있어도 Database Connection Pool이 고갈되거나 시작 작업이 끝나지 않았을 수 있다. Health Check는 Instance를 Routing 후보에 포함할지 결정하는 신호다.

Consul은 HTTP, TCP, gRPC, TTL 등 여러 Check를 지원한다. Spring Boot에서는 Actuator Endpoint를 HTTP로 확인하는 구성이 흔하다.

```groovy title="build.gradle"
implementation 'org.springframework.cloud:spring-cloud-starter-consul-discovery'
implementation 'org.springframework.boot:spring-boot-starter-actuator'
```

Spring Cloud Dependency Version은 Spring Boot Version과 호환되는 Release Train의 BOM으로 관리한다. 개별 Library Version을 임의로 섞으면 Auto Configuration API가 맞지 않을 수 있다.

```yaml title="application.yml"
spring:
  application:
    name: order-service
  cloud:
    consul:
      host: localhost
      port: 8500
      discovery:
        register: true
        health-check-path: /actuator/health
        health-check-interval: 10s
        instance-id: ${spring.application.name}:${HOSTNAME:${random.value}}
        prefer-ip-address: true
        metadata:
          version: v1
          region: ap-northeast-2

management:
  endpoints:
    web:
      exposure:
        include: health,info
```

Instance ID는 동시에 실행되는 Instance마다 고유해야 한다. 이름만 사용하면 새 Instance가 기존 등록을 덮어쓸 수 있다. 반대로 매 시작마다 무작위 ID만 사용하고 정상 Deregistration이 안 되면 죽은 등록이 쌓일 수 있으므로 종료 처리와 Check 정책을 함께 설계한다.

## Liveness와 Readiness를 구분하기

Health Endpoint 하나에 모든 의존성을 넣으면 Database의 짧은 장애가 모든 Application Instance를 동시에 Discovery에서 제거하는 연쇄 장애가 될 수 있다.

- **Liveness**는 Process를 재시작해야 할 정도로 회복 불가능한지 본다.
- **Readiness**는 지금 새 요청을 받을 준비가 되었는지 본다.

Discovery Check에는 Routing 가능성을 나타내는 Readiness 성격의 Endpoint가 적합하다. 외부 Dependency를 포함할 때는 그 장애로 Traffic을 제거하는 것이 실제 복구에 도움이 되는지 판단한다. Check Interval과 Timeout도 너무 공격적으로 잡으면 일시적 Network 지연에 Instance가 흔들리는 Flapping이 생긴다.

## HTTP API와 DNS 조회

Consul Catalog는 HTTP API와 DNS로 조회할 수 있다.

```shell
curl 'http://localhost:8500/v1/health/service/order-service?passing=true'
```

`passing=true`를 사용해야 실패한 Check의 Instance를 제외한다. Catalog API와 Health API는 반환 의미가 다르므로 “등록된 모든 Instance”와 “건강한 Instance”를 혼동하지 않는다.

DNS에서는 기본 Domain 아래의 Service 이름을 조회한다.

```shell
dig @127.0.0.1 -p 8600 order-service.service.consul
```

DNS TTL, Client Cache와 Load Balancing 방식에 따라 장애 Instance가 얼마나 빨리 제외되는지가 달라진다. Discovery 시스템의 상태가 즉시 모든 Client에 반영된다고 가정하면 안 된다.

## Consul KV와 Spring Config

Spring Cloud Consul Config는 Consul KV의 값을 Spring `Environment` Property Source로 읽는다.

```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-consul-config'
```

최근 Spring Boot에서는 Config Data Import 방식으로 Consul 설정 위치를 선언한다.

```yaml
spring:
  config:
    import: optional:consul:localhost:8500
  cloud:
    consul:
      config:
        enabled: true
        watch:
          enabled: true
```

`optional:`을 붙이면 Consul이 없어도 시작할 수 있다. 설정 없이는 안전하게 실행하면 안 되는 운영 Application이라면 이를 제거해 Fail-fast로 시작을 막는 편이 맞을 수 있다.

Config Watch는 Consul의 Blocking Query를 이용해 변경을 감지할 수 있지만, 값이 바뀌었다고 모든 Bean이 자동으로 새 값을 사용하는 것은 아니다. Refresh Scope, Configuration Properties 재결합과 변경 중 요청의 일관성을 검토해야 한다. Database Schema나 업무 규칙처럼 Instance 간 동시 변경이 위험한 값은 단순 Dynamic Config로 다루기보다 Versioned 배포가 안전하다.

> [!Warning] Secret 저장
> Consul KV는 설정 저장소이지 그 자체로 Secret 암호화와 접근 통제를 자동 완성하는 Vault가 아니다. ACL, TLS와 저장 데이터 보호를 구성하고, 민감 정보는 Vault나 Cloud Secret Manager 같은 전용 시스템을 검토한다.

## 운영에서 반드시 구성할 보안

Consul의 기본 개발 설정을 그대로 운영에 노출하면 Catalog와 KV가 공격 표면이 된다.

- ACL을 활성화하고 Service별 최소 권한 Token을 발급한다.
- Agent와 Server 사이 TLS로 신원과 전송 구간을 보호한다.
- Gossip Encryption Key를 안전하게 배포하고 Rotation 절차를 마련한다.
- HTTP, DNS, Serf, Server RPC Port의 Network 접근 범위를 제한한다.
- Consul Snapshot을 만들고 실제 복원 절차를 검증한다.
- Raft Leader, Peer 수, Failed Check, Catalog 등록 잔존과 Request 지연을 관측한다.

ACL Token을 `application.yml`이나 Image 안에 직접 넣지 않는다. Runtime Secret 주입을 사용하고 Log와 Actuator Environment Endpoint에 노출되지 않는지 확인한다.

## 장애 상황을 어떻게 생각할까?

Consul이 잠시 응답하지 않아도 이미 얻은 Instance로 호출을 계속할지, 새 요청을 실패시킬지는 Client Cache와 Library 정책에 따라 다르다. Discovery 장애가 곧 전체 Service 장애가 되지 않도록 다음 상황을 Test한다.

1. Consul Leader 교체 중 등록과 조회가 어떻게 동작하는가?
2. Network Partition으로 Client Agent가 Server와 단절되면 오래된 Catalog를 사용하는가?
3. Application이 비정상 종료될 때 몇 초 뒤 Routing에서 제외되는가?
4. Consul 복구 뒤 중복 또는 유령 Instance가 남는가?
5. 모든 Instance가 Unhealthy일 때 호출자는 어떤 오류와 Retry 정책을 사용하는가?

Retry는 Discovery 오류를 감출 수 있지만 동시에 복구 중인 Consul에 부하를 집중시킬 수 있다. 지수 Backoff, Jitter, 상한과 Circuit Breaker를 함께 고려한다.

## 언제 Consul을 선택할까?

VM, Bare Metal, Kubernetes처럼 여러 Runtime을 하나의 Service Catalog와 Mesh로 연결하거나 DNS 기반 Discovery가 필요한 환경에서 강점이 있다. 반면 단일 Kubernetes Cluster 안의 단순 Discovery만 필요하다면 Kubernetes Service와 CoreDNS로 충분할 수 있다. 별도 Consul Cluster는 Raft 운영, Upgrade, Backup, ACL과 인증서 관리라는 비용을 추가한다.

도구의 기능 수보다 중요한 것은 문제의 범위다. **동적 주소 발견, 건강 상태, Traffic 선택, 설정 배포와 Secret 관리 중 어떤 문제를 해결하려는지 분리한 뒤**, Consul이 그 책임을 맡을 이유가 명확할 때 도입한다.

# Reference
[Spring Cloud Consul Reference](https://docs.spring.io/spring-cloud-consul/reference/)
[HashiCorp Consul - Architecture](https://developer.hashicorp.com/consul/docs/architecture)
[HashiCorp Consul - Service Discovery](https://developer.hashicorp.com/consul/docs/discover)
[HashiCorp Consul - Security Architecture](https://developer.hashicorp.com/consul/docs/architecture/security)
