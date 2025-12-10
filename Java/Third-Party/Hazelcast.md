---
id: Hazelcast
started: 2025-07-28
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Hazelcast (In-Memory Data Grid)

## 1. 개요 (Overview)
**Hazelcast**는 오픈 소스 **인메모리 데이터 그리드 (IMDG, In-Memory Data Grid)** 솔루션입니다.
Redis가 '구조화된 저장소(Structure Store)'라면, Hazelcast는 'Java 컬렉션의 분산 확장판'에 가깝습니다. 여러 서버의 RAM을 합쳐서 하나의 거대한 공유 메모리처럼 사용하게 해주며, Java의 `Map`, `List`, `Queue`, `Set` 등을 분산 환경에서 투명하게 사용할 수 있도록 지원합니다.

일반적인 캐시(Cache) 역할뿐만 아니라, 분산 컴퓨팅(Distributed Computing), 글로벌 락(Lock), 메시징(Pub/Sub) 등 다양한 기능을 제공합니다.

---

## 2. 핵심 아키텍처 (Architecture)

### 2.1 클러스터링과 파티셔닝 (Clustering & Partitioning)
- **P2P(Peer-to-Peer) 구조**: Hazelcast 클러스터의 모든 멤버(노드)는 동등한 지위를 갖습니다. 마스터-슬레이브 구조가 아니라서 단일 장애 지점(SPOF)이 없습니다.
- **데이터 파티셔닝**: 기본적으로 데이터를 271개(설정 가능)의 파티션으로 쪼갭니다. 이 파티션들은 클러스터 멤버들에게 균등하게 분배됩니다.
    - 예: 노드가 2개면 각각 135개씩 담당. 노드가 하나 추가되면 자동으로 파티션을 재분배(Rebalancing)하여 90개씩 담당.
- **백업(Backup)**: 각 파티션은 지정된 횟수만큼 다른 노드에 복제본(Replica)을 가집니다. 노드 하나가 죽으면, 다른 노드에 있던 백업 데이터가 즉시 활성화되어 데이터 손실을 막습니다.

### 2.2 Client-Server vs Embedded Mode
두 가지 배포 모드를 지원합니다.
1.  **Embedded Mode**: 애플리케이션(Spring Boot) 내부에 라이브러리 형태로 Hazelcast 노드가 뜹니다. 앱 서버 자체가 데이터 노드가 되므로 데이터 접근 속도(Latency)가 가장 빠르지만, 힙 메모리를 공유하므로 GC 영향을 받습니다.
2.  **Client-Server Mode**: Hazelcast를 별도의 서버군으로 띄우고, 앱은 클라이언트로 접속합니다. 아키텍처적으로 분리되어 있어 독립적인 확장이 가능하며, 가장 권장되는 방식입니다.

### 2.3 Near Cache
클라이언트(앱) 쪽에 자주 쓰는 데이터를 로컬 캐시로 한 번 더 저장하는 기능입니다. 네트워크를 탈 필요가 없어 조회 속도가 나노초(ns) 단위로 줄어듭니다. 하지만 데이터 일관성(Invalidation) 관리에 주의해야 합니다.

---

## 3. 주요 기능 (Features)

### 3.1 Distributed Map (`IMap`)
Java의 `ConcurrentMap`을 확장한 분산 맵입니다.
- `put`, `get` 외에도 `lock`, `entryProcessor`(데이터가 있는 노드로 로직을 보내서 실행) 등을 지원합니다.

### 3.2 CP Subsystem (Strong Consistency)
Hazelcast의 기본 Map은 AP(Availability, Partition Tolerance) 모델을 따르지만, Raft 알고리즘 기반의 **CP Subsystem**을 사용하면 강력한 일관성을 보장하는 기능(`FencedLock`, `AtomicLong`)을 사용할 수 있습니다. (Redis 분산 락보다 안전함).

---

## 4. Spring Boot 구현 예제

### 4.1 의존성 추가
```groovy
implementation 'com.hazelcast:hazelcast-spring'
```

**설정 파일 (`hazelcast.yaml`)**
```yaml
hazelcast:
  network:
    join:
      multicast:
        enabled: false
      tcp-ip:
        enabled: true
        member-list:
          - 127.0.0.1
  map:
    my-cache:
      backup-count: 1 # 동기 백업 1개
      time-to-live-seconds: 60 # 60초 후 만료
```

### Java 코드 사용 (JCache / Map)
```java
@Service
@RequiredArgsConstructor
public class CacheService {

    private final HazelcastInstance hazelcastInstance;

    public void useDistributedMap() {
        // 분산 맵 가져오기 (모든 노드에서 공유됨)
        IMap<String, String> map = hazelcastInstance.getMap("my-cache");

        // Put: 네트워크를 통해 저장되거나(내 파티션이면) 로컬에 저장
        map.put("key1", "value1"); 

        // Get: 데이터가 있는 노드에서 가져옴 (Near Cache 설정 시 로컬 캐싱 가능)
        String value = map.get("key1");
        
        // Locking: 분산 락 지원
        map.lock("key1");
        try {
            // 임계 영역 (Critical Section)
        } finally {
            map.unlock("key1");
        }
    }
}
```

## 5. 운영 시 고려사항 (Operational Considerations)
- **Split Brain**: 네트워크 단절로 클러스터가 두 개로 쪼개지면 데이터 불일치가 발생할 수 있습니다. `Quorum(최소 노드 수)` 설정으로 방지해야 합니다.
- **Heap OOM**: 데이터가 JVM Heap에 저장되므로, 과도한 데이터 적재 시 GC 부하가 커집니다. (엔터프라이즈 버전은 Off-heap 지원)

# Reference