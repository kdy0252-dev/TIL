---
id: Spring Cloud Consul
started: 2025-09-0-16
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Consul

## 1. 개요 (Overview)
**Spring Cloud Consul**은 HashiCorp사의 **Consul**을 사용하여 **서비스 디스커버리(Service Discovery)**와 **분산 설정(Configuration)**을 제공하는 프로젝트입니다.
Zookeeper보다 설치 및 운영이 쉽고, Eureka보다 기능이 다양(Service Mesh, DNS 인터페이스 등)하여 최근 MSA 환경에서 가장 널리 쓰이는 솔루션 중 하나입니다.

---

## 2. 주요 아키텍처 (Architecture)

### 2.1 Consul Agent (Server & Client)
Consul은 모든 노드에 에이전트를 설치하는 것을 권장합니다.
- **Server Agent**: 상태를 저장하고 클러스터(Raft 합의 알고리즘)를 유지하며 리더를 선출합니다. (보통 3~5대 운영)
- **Client Agent**: 애플리케이션 서버에 뜨며, 상태를 저장하지 않고 Server로 요청을 포워딩(RPC)합니다. 로컬 헬스 체크를 담당합니다.
- **Spring Cloud 연동**: Spring Boot 앱이 `localhost:8500`(로컬 Client Agent)에 붙거나, 바로 Server Agent에 Http로 붙을 수 있습니다.

### 2.2 Service Discovery (HTTP & DNS)
Consul은 독특하게 DNS 인터페이스를 제공합니다.
- **HTTP API**: `/v1/catalog/service/my-service`
- **DNS**: `my-service.service.consul` 도메인 질의 시 IP 반환. (Legacy 시스템 연동에 유리)

---

## 3. 핵심 기능 (Key Features)

### 3.1 Health Check (헬스 체크)
Eureka는 Heartbeat(단순 생존 신호)만 보내지만, Consul은 더 정교한 체크 방식을 지원합니다.
1.  **HTTP Check**: Consul이 주기적으로 앱의 `/actuator/health`를 찌릅니다.
2.  **Script Check**: 내부 스크립트 실행 결과를 확인합니다.
3.  **TTL Check**: 앱이 주기적으로 "나 살아있어"라고 신호를 보냅니다. (Spring Cloud Consul 기본값)

### 3.2 Key/Value Store (Configuration)
`application.yml` 설정을 대체할 수 있습니다. 디렉토리 구조(`/config/app/data`)를 가지며, 값이 바뀌면 Long Polling 방식으로 즉시 클라이언트에 반영됩니다.

---

## 4. 구현 및 설정 예제

### 4.1 의존성 추가 (Gradle)
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-consul-discovery'
implementation 'org.springframework.cloud:spring-cloud-starter-consul-config'
implementation 'org.springframework.boot:spring-boot-starter-actuator' // 헬스 체크용
```

### 4.2 application.yml 설정

```yaml
spring:
  application:
    name: order-service
  cloud:
    consul:
      host: localhost
      port: 8500
      
      # 1. 디스커버리 설정
      discovery:
        health-check-path: /actuator/health
        health-check-interval: 10s
        instance-id: ${spring.application.name}:${random.value}
        prefer-ip-address: true # 호스트명 대신 IP로 등록
        tags: # 메타데이터 (Canary 배포 등에 활용)
          - "version=v1"
          - "region=ap-northeast-2"
          
      # 2. 설정(Config) 관리
      config:
        enabled: true
# Reference