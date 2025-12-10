---
id: DB 클러스터링
started: 2025-05-08
tags:
  - ✅DONE
  - DB
group:
  - "[[DBMS]]"
---
# DB 클러스터링 (Database Clustering)

## 1. 개요 (Overview)
**DB 클러스터링(Database Clustering)**은 여러 대의 데이터베이스 서버(Node)를 하나의 시스템처럼 동작하게 묶어서 **고가용성(High Availability, HA)** 과 **성능(Performance)**, **확장성(Scalability)** 을 확보하는 기술입니다.

단일 서버(Single Point Failure)의 한계를 극복하기 위해, 하나의 서버가 죽어도 다른 서버가 서비스를 지속(Failover)하거나, 트래픽을 분산 처리(Load Balancing)하여 처리량을 늘리는 것을 목표로 합니다.
하지만 "모든 것을 만족하는 마법"은 아니며, 데이터 동기화 비용, 관리 복잡도, 트랜잭션 관리 등의 **Trade-off**가 존재합니다.

---

## 2. 클러스터링 아키텍처 유형 (Architecture Types)

데이터(스토리지)를 어떻게 공유하느냐에 따라 크게 두 가지로 나뉩니다.

### 2.1 Shared Disk Architecture (공유 디스크)
- **개요**: 모든 DB 노드가 **하나의 중앙 스토리지(SAN/NAS)** 를 공유합니다.
- **특징**:
    - 데이터는 한 곳에만 존재하므로 동기화(Replication) 이슈가 없습니다.
    - 모든 노드는 Active 상태로 읽기/쓰기가 가능합니다.
    - **Scalability**: 노드 추가 시 CPU/RAM 확장은 쉽지만, 스토리지 I/O 락(Lock) 경합으로 인해 확장에 한계가 있습니다.
- **대표 사례**: **Oracle RAC (Real Application Clusters)**.
    - Oracle은 `Cache Fusion` 기술을 통해 네트워크로 메모리 데이터를 교환하며 성능 저하를 최소화합니다.

### 2.2 Shared Nothing Architecture (무공유)
- **개요**: 각 DB 노드가 **자신만의 스토리지(CPU, RAM, Disk)** 를 가집니다.
- **특징**:
    - 노드 간 데이터 공유가 없으므로 네트워크를 통해 데이터를 복제(Replication)해야 합니다.
    - 물리적으로 완전히 분리되어 있어 이론적으로 무한 확장이 가능합니다 (Sharding 등).
    - **단점**: 데이터 동기화(Replication lag) 문제, 정합성 유지 복잡성.
- **대표 사례**: **MySQL Cluster (NDB)**, **Galera Cluster**, **Sharding**.

---

## 3. 운영 모드에 따른 분류 (Operation Modes)

### 3.1 Active-Standby (HA 중점)
- **구성**:
    - **Active**: 실제 서비스를 처리하는 주 서버.
    - **Standby**: Active 서버의 데이터를 실시간/비동기로 복제받으며 대기하는 서버.
- **동작**: Active 서버 장애 시, Heartbeat 감지를 통해 Standby 서버가 Active로 승격(Failover)됩니다.
- **장점**: 구성이 단순하고 데이터 정합성 관리가 쉽습니다.
- **단점**: Standby 장비는 평소에 놀고 있어 자원 낭비가 발생합니다.
- **예시**: Oracle Data Guard, AWS RDS Multi-AZ.

### 3.2 Active-Active (성능 분산 중점)
- **구성**: 두 대 이상의 서버가 동시에 서비스를 처리합니다.
- **동작**: L4/L7 스위치가 트래픽을 분산해줍니다. 한 노드가 죽어도 다른 노드가 살아있으므로 서비스 중단이 없습니다.
- **장점**: 자원 효율성 극대화, 처리량 증대.
- **단점**:
    - **데이터 동기화 이슈**: A노드에서 쓴 데이터를 B노드에서 즉시 못 읽을 수도 있음.
    - **동시성 제어 복잡**: 양쪽에서 같은 Row를 동시에 수정할 때 충돌(Conflict) 해결 필요.
- **예시**: Oracle RAC, MySQL Galera Cluster (Multi-Master).

---

## 4. 상세 기술 및 솔루션 비교 (Comparison)

| 구분 | Oracle RAC | MySQL Replication | MySQL Galera / PXC |
| :--- | :--- | :--- | :--- |
| **아키텍처** | Shared Disk | Shared Nothing | Shared Nothing |
| **복제 방식** | 스토리지 공유 (복제X) | Async / Semi-Sync | Synchronous (다중 마스터) |
| **일관성** | 강력한 일관성 (Strong Consistency) | 최종 일관성 (Eventual) | 사실상 Strong |
| **쓰기 확장** | 가능 (하지만 Lock 경합 있음) | 불가능 (Master만 쓰기 가능) | 가능 (단, 가장 느린 노드에 맞춰짐) |
| **관리 난이도** | 상 (전문 엔지니어 필요) | 하 (널리 쓰임) | 중상 |
| **비용** | 매우 높음 (라이선스) | 오픈소스 (무료) | 오픈소스 |

---

## 5. CAP 이론 관점 (CAP Theorem Context)
클러스터링은 분산 시스템이므로 CAP 이론의 제약을 받습니다.
- **C (Consistency)**: 모든 노드가 같은 시간에 같은 데이터를 보여주는가.
- **A (Availability)**: 일부 노드가 죽어도 응답하는가.
- **P (Partition Tolerance)**: 네트워크 단절 시에도 시스템이 동작하는가.

- **Oracle RAC**: **CP** 또는 **CA** 에 가깝습니다 (스토리지 공유로 P를 어느 정도 극복하지만 네트워크 중요).
- **MySQL Async Replication**: **AP** 시스템 (일관성 포기, 가용성 우선).
- **Galera Cluster**: **CP** 시스템 (일관성을 위해 쓰기 성능 일부 희생).

---

## 6. 예제 설정 (Configuration Example)

### MySQL Galera Cluster 설정 (mariadb.cnf)
3대 노드(192.168.0.1~3)를 Active-Active로 묶는 설정 예시입니다.

```ini
[galera]
# Galera Provider 라이브러리 경로
wsrep_provider=/usr/lib/galera/libgalera_smm.so

# 클러스터 멤버 IP 목록 (3대 모두 기입)
wsrep_cluster_address="gcomm://192.168.0.1,192.168.0.2,192.168.0.3"

# 노드 별 설정 (Node 1)
wsrep_node_address="192.168.0.1"
wsrep_node_name="node1"

# 동기화 방식 (SST: 스냅샷 전송)
wsrep_sst_method=rsync

# 리플리케이션 자동 켜기
binlog_format=row
default_storage_engine=InnoDB
innodb_autoinc_lock_mode=2
```

---

## 7. 운영 시 고려사항 (Operational Considerations)

### 7.1 Split Brain (스플릿 브레인)
- 네트워크 단절로 인해 노드들이 서로 죽었다고 판단하고, 각각 자신이 Master라고 주장하며 데이터를 독자적으로 쓰기 시작하는 현상.
- **해결**:
    - **Quorum(정족수)**: 노드 수가 과반수(N/2 + 1) 이상 살아있는 그룹만 정상으로 인정.
    - **Fencing**: 문제가 생긴 노드의 전원을 차단하거나 스토리지 접근을 강제로 끊음 (STONITH).

### 7.2 성능 저하 (Latency)
- Active-Active, 특히 동기식 복제(Synchronous Replication)를 사용하는 클러스터(Galera 등)는 **모든 노드에 데이터가 써져야 커밋이 완료**되므로, 가장 느린 노드나 네트워크 지연에 전체 쓰기 성능이 하향 평준화됩니다.
- 쓰기 작업이 많은 시스템에서는 Active-Active가 오히려 독이 될 수 있습니다. (Sharding이 더 적합할 수 있음)

### 7.3 Cache Coherency (캐시 일관성)
- 각 노드의 메모리(Buffer Pool)에 있는 캐시 데이터가 일치해야 합니다.
- Oracle RAC는 Cache Fusion으로 이를 해결하지만, 네트워크 트래픽이 엄청나게 발생하므로 **Interconnect 네트워크 대역폭** 확보가 필수입니다.

# Reference
- [Oracle 19c RAC Administration Guide](https://docs.oracle.com/en/database/oracle/oracle-database/19/racad/index.html)
- [Galera Cluster Documentation](https://galeracluster.com/library/documentation/)
- [High Performance MySQL](https://www.oreilly.com/library/view/high-performance-mysql/9780596101718/)