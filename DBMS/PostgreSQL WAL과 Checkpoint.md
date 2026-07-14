---
id: PostgreSQL WAL과 Checkpoint
started: 2026-05-18
tags:
  - ✅DONE
  - PostgreSQL
  - WAL
group:
  - "[[DBMS]]"
---
# PostgreSQL WAL과 Checkpoint

## 1. WAL이 필요한 이유

PostgreSQL은 변경된 Data Page보다 Write-Ahead Log(WAL)를 먼저 영구 저장합니다. 장애 뒤 WAL을 재생하면 마지막 Checkpoint 이후 변경을 복구할 수 있습니다.

```text
Transaction 변경
  -> WAL Buffer
  -> WAL Flush
  -> Commit 응답
  -> Dirty Page는 나중에 Data File로 기록
```

모든 Page를 Commit마다 쓰는 것보다 순차적인 WAL을 먼저 쓰는 편이 빠릅니다.

---

## 2. LSN과 복구

WAL Record는 Log Sequence Number(LSN)로 위치를 식별합니다. Data Page에도 마지막 반영 LSN이 있어 복구 과정은 필요한 Record만 재생합니다. Replica는 Primary WAL을 받아 재생하므로 Replication Lag도 LSN 차이로 설명할 수 있습니다.

---

## 3. Checkpoint

Checkpoint는 특정 시점까지의 Dirty Page를 Data File에 반영하고 복구 시작점을 앞으로 이동합니다.

- 너무 잦음: Disk Write Spike와 WAL 증가
- 너무 드묾: Crash Recovery 시간과 WAL 보관량 증가
- 짧은 시간에 몰림: Application I/O Latency 증가

`checkpoint_completion_target`은 Write를 주기 안에 분산하는 데 사용합니다.

---

## 4. Full Page Write

Checkpoint 뒤 Page를 처음 변경할 때 Torn Page 복구를 위해 전체 Page Image가 WAL에 기록될 수 있습니다. Checkpoint가 잦으면 Full Page Write도 늘어 Write Amplification이 커집니다.

WAL 양 증가는 업무 Row 변경량뿐 아니라 Checkpoint, Index, Vacuum, Bulk Load와도 관련됩니다.

---

## 5. Commit 내구성

`synchronous_commit`은 Commit 응답 전에 WAL Flush 또는 Replica 확인을 얼마나 기다릴지 결정합니다. 끄면 Latency를 줄일 수 있지만 OS·Instance 장애에서 최근 Commit을 잃을 수 있습니다.

업무 중요도 없이 전역으로 변경하지 않습니다. 유실 가능한 Telemetry와 금전·운행 상태는 같은 정책을 사용할 이유가 없습니다.

---

## 6. Archiving과 PITR

Base Backup과 연속 WAL Archive를 결합하면 특정 시점까지 복구할 수 있습니다.

```text
Base Backup
  + 이후 WAL Segment
  -> 목표 시점까지 Replay
```

Archive 성공 Metric만 믿지 말고 별도 Instance에 Restore하여 RPO·RTO를 측정합니다. Archive Gap 하나가 전체 복구 구간을 끊을 수 있습니다.

---

## 7. 관측 지표

- Checkpoint 요청·예약 횟수
- Checkpoint Write·Sync 시간
- WAL Bytes와 Segment 생성률
- WAL Archive 실패와 지연
- Replica Replay Lag
- Disk Queue와 Write Latency
- Recovery 예상 시간

WAL 증가 시 해당 시간의 배포, Index 생성, Batch와 Transaction을 함께 봅니다.

---

## 8. 실무 장애 양상

| 증상 | 원인 후보 |
|---|---|
| 주기적 Latency Spike | Checkpoint Write 집중 |
| WAL Disk 고갈 | Archive 실패, Replica Slot 지연 |
| Replica Lag 증가 | WAL 생성 급증, Replica I/O 부족 |
| 복구 시간 증가 | 긴 Checkpoint 간격, 많은 WAL |
| WAL 폭증 | Full Page Write, Index, Bulk Update |

Replication Slot이 오래된 WAL을 붙잡아 Disk를 채우는 상황을 반드시 경보합니다.

---

## 9. 학습 실습

1. `pg_stat_wal`, `pg_stat_bgwriter`, Checkpoint Log를 수집합니다.
2. 동일 쓰기 부하에서 Checkpoint 설정별 WAL과 P99를 비교합니다.
3. Replica를 멈춰 Slot과 Disk 증가를 관찰합니다.
4. Base Backup과 WAL로 목표 시점 Restore를 수행합니다.
5. 복구 결과의 Row와 업무 정합성을 검증합니다.

---

## 10. 완료 기준

- [ ] Commit 응답과 WAL Flush 관계를 설명할 수 있습니다.
- [ ] Checkpoint Spike와 일반 Query 병목을 구분합니다.
- [ ] WAL Archive Gap·Slot Disk 위험을 경보합니다.
- [ ] PITR을 실제 수행해 RPO·RTO를 측정했습니다.
- [ ] 설정 변경을 k6와 Disk Metric으로 검증합니다.

# Reference

- [PostgreSQL WAL](https://www.postgresql.org/docs/current/wal-intro.html)
- [PostgreSQL Checkpoints](https://www.postgresql.org/docs/current/wal-configuration.html)
- [[PostgreSQL MVCC]]
- [[PostgreSQL Vaccum]]
