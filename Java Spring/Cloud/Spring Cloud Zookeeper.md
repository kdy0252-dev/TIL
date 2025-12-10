---
id: Spring Cloud Zookeeper
started: 2025-10-08
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Zookeeper

## 1. 개요 (Overview)
**Spring Cloud Zookeeper**는 Apache Zookeeper를 이용하여 분산 시스템의 **서비스 디스커버리(Service Discovery)**와 **분산 설정(Distributed Configuration)** 기능을 제공하는 프로젝트입니다.
Eureka나 Consul의 대안으로 사용될 수 있으며, 이미 하둡(Hadoop)이나 카프카(Kafka) 생태계를 구축하여 주키퍼를 운영 중인 조직에서 도입하기 유리합니다.

---

## 2. 주요 기능 (Key Features)

### 2.1 Service Discovery
- **원리**: 애플리케이션이 시작될 때 Zookeeper의 특정 경로(예: `/services/my-service/instance-id`)에 **임시 노드(Ephemeral Node)**를 생성합니다.
- **Health Check**: 애플리케이션과 주키퍼 간의 세션이 끊어지면(장애 발생 시) 임시 노드가 자동으로 삭제되므로, 자연스럽게 목록에서 제외됩니다.
- **Ribbon/LoadBalancer 연동**: `DiscoveryClient` 구현체를 제공하므로 Spring Cloud LoadBalancer와 투명하게 연동됩니다.

### 2.2 Distributed Configuration
- **원리**: Spring Cloud Config와 유사하게, 주키퍼의 ZNode에 저장된 데이터를 설정 값으로 불러옵니다.
- **Watcher**: 주키퍼의 강력한 Watch 매커니즘을 활용하여, 설정 값이 변경되면 즉시 클라이언트에게 알림(Notification)이 가고, Spring 환경 변수가 갱신(`RefreshScope`)됩니다.

### 2.3 Leader Election (리더 선출)
- 여러 인스턴스 중 하나만 배치를 돌려야 하거나 마스터 역할을 해야 할 때 유용합니다.
- Spring Integration Zookeeper 등을 통해 쉽게 구현할 수 있습니다.

---

## 3. 아키텍처 및 데이터 구조

### 3.1 ZNode 계층 구조
Spring Cloud Zookeeper는 기본적으로 다음과 같은 구조를 사용합니다.
- **/services**: 모든 서비스의 루트
    - **/services/order-service**: 서비스별 디렉토리
        - **/id-1**: 인스턴스 1 (IP, Port, Metadata) - Ephemeral
        - **/id-2**: 인스턴스 2 (IP, Port, Metadata) - Ephemeral

### 3.2 의존성 관리
Netflix Eureka가 2.x에서 유지보수 모드로 전환되면서, 대안으로 Zookeeper나 Consul이 권장되기도 했습니다. 하지만 Zookeeper는 운영 복잡도가 높기 때문에(CP 시스템), 단순 서비스 디스커버리 용도로는 Consul이나 Eureka가 더 선호되기도 합니다.

---

## 4. 구현 및 설정 예제

### 4.1 의존성 추가 (Gradle)
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-zookeeper-discovery'
implementation 'org.springframework.cloud:spring-cloud-starter-zookeeper-config' // 설정 관리 필요 시
```

### 4.2 application.yml 설정

```yaml
spring:
  application:
    name: user-service
  cloud:
    zookeeper:
      connect-string: localhost:2181
      
      # 1. Service Discovery 설정
      discovery:
        enabled: true
        root: /services
        instance-host: localhost # 생략 시 자동 감지
        
      # 2. Config 설정
      config:
        enabled: true
        root: /config
        defaultContext: application
        profileSeparator: '::' # default
```

### 4.3 리더 선출 사용 예제 (with Spring Integration)

```java
@Configuration
public class LeaderConfig {

    @Bean
    public LeaderInitiator leaderInitiator(CuratorFramework client) {
        return new LeaderInitiator(client, new Candidate() {
            @Override
            public String getRole() {
                return "master";
            }

            @Override
            public String getId() {
                return UUID.randomUUID().toString();
            }

            @Override
            public void onGranted(Context ctx) {
                System.out.println("I am leader now!");
                startBatchJob();
            }

            @Override
            public void onRevoked(Context ctx) {
                System.out.println("I lost leadership.");
                stopBatchJob();
            }
        });
    }
}
```

# Reference