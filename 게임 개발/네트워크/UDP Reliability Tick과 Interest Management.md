---
id: UDP Reliability Tick과 Interest Management
started: 2026-06-11
tags:
  - ✅DONE
  - Game-Development
  - UDP
  - Networking
group: "[[게임 개발]]"
---

# UDP Reliability, Tick, Delta Compression과 Interest Management

게임이 UDP를 사용한다는 말은 신뢰성이 필요 없다는 뜻이 아니다. 모든 Message에 TCP의 순서·재전송 정책을 강제하지 않고 Message 종류에 맞게 보장 수준을 선택한다는 뜻에 가깝다.

## Message별 전달 정책

| Message | 일반적인 정책 | 이유 |
|---|---|---|
| Player Input | Unreliable + 최근 Input 중복 | 새 Input이 오래된 Input보다 중요 |
| Transform Snapshot | Unreliable Sequenced | 늦은 State는 폐기 |
| Inventory 변경 | Reliable Ordered | 누락·순서 변경이 허용되지 않음 |
| Chat | Reliable Ordered | 모든 Message 보존 |
| Spawn·Despawn | Reliable 또는 반복 전송 | World 존재 여부에 중요 |

하나의 Reliable Packet이 유실됐다고 모든 최신 Snapshot을 막으면 Head-of-line Blocking이 발생한다. Channel을 분리하거나 Message별 Sequence Space를 둔다.

## Sequence와 ACK Bitfield

16-bit Sequence 번호와 최근 32개 Packet 수신 여부를 Bitfield로 보낼 수 있다.

```text
sequence = 100
ack = 95
ack_bits = 000...1011
```

`ack=95`는 95번을 받았고 각 Bit는 94, 93, 92 순서의 수신 여부를 나타낸다. 송신자는 ACK되지 않은 Reliable Message만 재전송한다. Sequence가 최대값에서 0으로 돌아가는 Wrap-around 비교를 일반 정수 비교로 처리하면 오류가 난다.

## Tick Rate와 Snapshot Rate

Simulation Tick과 Network Send Rate는 같을 필요가 없다. Server가 60 Hz로 Physics를 계산하면서 20 Hz로 Snapshot을 보낼 수 있다.

Tick Rate를 높이면 입력 반영 Granularity가 좋아지지만 CPU와 Bandwidth가 증가한다. 실제 End-to-end Latency에는 Client Input Sampling, Uplink, Server Queue, Tick 대기, Downlink, Render Buffer와 Display가 모두 포함된다.

```text
latency ≠ ping만의 값
```

Server가 한 Tick을 제시간에 끝내지 못하면 Tick Drift가 누적된다. Tick Duration Histogram과 Overrun 횟수를 운영 Metric으로 수집한다.

## Delta Compression

Client가 확인한 Baseline Snapshot과 현재 State의 차이만 보낸다.

```text
baseline 120: position=(10,20), health=100
snapshot 125: position=(11,20)만 전송
```

Packet Loss로 Baseline을 받지 못했다면 Delta를 복원할 수 없다. Packet에 Baseline ID를 포함하고 Client가 보유한 Snapshot을 ACK하도록 한다. 주기적인 Full Snapshot이나 새 Baseline 전환도 필요하다.

Float Position을 World 범위와 필요한 정밀도에 맞춰 Quantization하면 크기를 줄일 수 있다. 예를 들어 방 하나의 Local 좌표를 16-bit로 표현할 수 있지만 Open World 절대 좌표에는 부족할 수 있다.

## Interest Management

모든 Client에 모든 Entity를 보내면 Player 수와 Entity 수가 늘 때 `O(P×E)`가 된다. Client가 관측할 가능성이 있는 객체만 Replicate한다.

```text
Spatial Grid / Quadtree / BVH
Party·Team·Instance
Line of Sight
Gameplay Subscription
```

단순 거리만 사용하면 빠른 Vehicle이 경계에서 갑자기 나타난다. 이동 속도와 Network 지연을 고려한 Prefetch Radius, Hysteresis와 중요도 우선순위가 필요하다.

Bandwidth Budget이 부족하면 모든 객체를 같은 빈도로 갱신하지 않는다.

```text
가까운 적: 20 Hz
먼 Player: 5 Hz
정적 Object: 변경 시에만
Cosmetic Object: 혼잡 시 Drop
```

## Congestion과 MTU

UDP도 Network Capacity를 넘겨 보내면 Queue와 Loss가 증가한다. 전송량을 제어하지 않으면 Packet Loss를 재전송이 더 키우는 Collapse가 생긴다. RTT, Loss와 ACK 속도를 이용해 Send Rate를 조절한다.

IP Fragmentation은 일부 Fragment만 유실돼도 전체 Datagram이 사라지고 NAT·Firewall 호환성도 나빠질 수 있다. Path MTU보다 작은 Packet을 만들고 큰 Message는 Application 수준에서 Fragment와 재조립을 관리한다.

## 보안

UDP Source Address는 위조될 수 있다. Session Token, Packet Authentication, Replay Window와 Rate Limit이 필요하다. Client가 보낸 Position이나 Damage 결과를 신뢰하지 않고 Input과 의도만 검증한다.

Packet Parser는 공격 표면이다. Length, Entity ID, Compression 값과 Fragment 수를 사용하기 전에 범위를 확인한다. 암호화 여부와 별개로 Server CPU를 소모시키는 Amplification과 Handshake Flood도 제한한다.

## 기억할 점

게임 Network Protocol은 “UDP 위에 TCP를 다시 만드는 것”이 아니다. 각 데이터가 늦게 도착했을 때 가치가 남아 있는지를 기준으로 Reliability, Ordering, Frequency와 Priority를 설계하는 일이다.

# Reference

- [Unreal Engine Networking and Multiplayer](https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-and-multiplayer-in-unreal-engine)
- [[Authoritative Game Server와 Session Architecture]]
