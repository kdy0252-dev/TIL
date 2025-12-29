---
id: Spring Cloud Kafka KRaft
started: 2025-08-19
tags:
  - ✅DONE
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Kafka KRaft (Kafka Raft Metadata mode)

## 1. 개요 (Overview)
**KRaft (Kafka Raft)** 는 Apache Kafka 2.8 버전부터 도입된 새로운 합의 프로토콜(Consensus Protocol) 기반의 메타데이터 관리 모드입니다.
기존 Kafka는 Zookeeper에 메타데이터(브로커 정보, 토픽, 파티션 등)를 저장하고 관리했으나, KRaft 모드를 사용하면 **Zookeeper 의존성을 완전히 제거**할 수 있습니다.
이로 인해 Kafka 클러스터의 아키텍처가 단순해지고, 확장성(Scalability)과 안정성이 크게 향상됩니다. (3.3 버전부터 Production Ready)

---

## 2. 기존 Zookeeper 모드의 문제점
- **이중 관리(Dual Hub)**: Kafka와 Zookeeper 두 개의 시스템을 운영해야 하는 부담.
- **메타데이터 비동기화**: Controller와 Zookeeper 간의 상태 불일치 가능성.
- **확장성 한계**: Zookeeper의 쓰기 성능 한계로 인해 파티션 개수(수십만 개)에 제한이 있었음.
- **Controller Failover 속도**: Controller 장애 시 Zookeeper에서 모든 메타데이터를 다시 읽어와야 해서 시간이 오래 걸림.

---

## 3. KRaft 아키텍처 및 동작 원리

### 3.1 Quorum Controller
Zookeeper 대신 **Quorum Controller**가 메타데이터를 관리합니다.
Kafka 브로커들 중 일부가 Controller 역할을 수행하며, 이들은 Raft 알고리즘을 사용하여 메타데이터 로그를 복제하고 리더를 선출합니다.

### 3.2 Metadata as a Log (`__cluster_metadata`)
모든 메타데이터 변경 사항(토픽 생성, ACL 변경 등)은 내부 토픽인 `__cluster_metadata`에 이벤트로 기록됩니다.
브로커들은 이 토픽을 구독(Consume)하여 자신의 메모리(Metadata Cache)를 최신 상태로 유지합니다. 
장애 발생 시에도 이 로그만 읽으면(Replay) 되므로 복구 속도가 매우 빠릅니다.

---

## 4. 설치 및 실행 가이드

### 4.1 설정 파일 준비 (`server.properties`)
KRaft 모드에서는 `process.roles`, `node.id`, `controller.quorum.voters` 설정이 핵심입니다.

```properties
# 역할: 브로커이면서 동시에 컨트롤러 (소규모 클러스터용)
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@localhost:9093

# 리스너 설정 (Controller간 통신은 별도 포트 사용 권장)
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER
```

### 4.2 스토리지 포맷팅 (Storage Formatting)
KRaft는 클러스터 ID(Cluster ID)로 초기화가 필요합니다.

```bash
# 1. Cluster UUID 생성
./bin/kafka-storage.sh random-uuid
# 출력예시: J8xL353kS-2...

# 2. 로그 디렉토리 포맷팅
./bin/kafka-storage.sh format -t J8xL353kS-2... -c ./config/kraft/server.properties
```

### 4.3 서버 실행
```bash
./bin/kafka-server-start.sh ./config/kraft/server.properties
```

---

## 5. Spring Boot에서의 활용

Spring Boot 애플리케이션 입장에서는 Kafka가 Zookeeper 모드인지 KRaft 모드인지 알 필요가 거의 없습니다. `bootstrap-servers` 정보만 알면 됩니다. 즉, 클라이언트 코드는 변경되지 않습니다.

```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    consumer:
      group-id: my-group
      auto-offset-reset: earliest
```

### 운영 시 이점
- **배포 단순화**: K8s 배포 시 Zookeeper 파드를 띄울 필요 없이 Kafka 파드만 띄우면 됨.
- **성능**: 메타데이터 처리가 빨라져서 토픽 생성/삭제 등의 관리 작업 응답 속도 향상.

# Reference
- [Apache Kafka KRaft Documentation](https://kafka.apache.org/documentation/#kraft)
- [Confluent: Why ZooKeeper was Replaced](https://www.confluent.io/blog/why-replace-zookeeper-with-kafka-raft-the-log-of-all-logs/)
- [KIP-500: Replace ZooKeeper with a Self-Managed Metadata Quorum](https://cwiki.apache.org/confluence/display/KAFKA/KIP-500%3A+Replace+ZooKeeper+with+a+Self-Managed+Metadata+Quorum)
