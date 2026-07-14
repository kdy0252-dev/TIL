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

## UDP부터 이해하기

Internet에서 Application Data는 Packet으로 잘려 전달된다. IP는 목적지까지 Packet을 운반하지만 도착, 순서와 중복 제거를 보장하지 않는다. UDP는 그 위에 Port와 간단한 Checksum을 제공하는 Datagram 방식이다. 한 번의 `sendto`가 하나의 Message 경계를 이루지만 다음 상황이 모두 가능하다.

- Packet이 사라진다.
- 먼저 보낸 Packet이 나중에 도착한다.
- 같은 Packet이 두 번 도착한다.
- 지연이 갑자기 커진다.

TCP는 손실된 Byte를 재전송하고 원래 순서대로 Application에 넘긴다. 파일과 Login API에는 편리하지만, 오래된 이동 Snapshot 하나가 유실됐을 때 뒤의 최신 Snapshot까지 기다리는 Head-of-line Blocking은 실시간 게임에 불리하다. 그래서 UDP 위에서 Message 종류마다 필요한 보장만 구현한다.

## Packet은 어떤 모양인가

실무 Protocol은 역직렬화 전에 검증할 수 있는 고정 Header를 둔다. C++ `struct`의 Memory를 그대로 전송하면 Padding, Endianness와 Compiler 차이 때문에 깨질 수 있으므로 필드별 Serializer를 사용한다.

```cpp
struct PacketHeader {
    std::uint32_t protocolId;     // 다른 UDP Traffic을 빠르게 거부
    std::uint64_t sessionId;
    std::uint32_t sequence;
    std::uint32_t ack;
    std::uint32_t ackBits;
    std::uint16_t payloadBytes;
    std::uint8_t channel;
    std::uint8_t flags;
};

constexpr std::uint32_t kProtocolId = 0x47414D45; // "GAME"
constexpr std::size_t kMaxDatagramBytes = 1200;

bool decodeHeader(ByteReader& reader, PacketHeader& header) {
    if (!reader.readU32BE(header.protocolId) ||
        !reader.readU64BE(header.sessionId) ||
        !reader.readU32BE(header.sequence) ||
        !reader.readU32BE(header.ack) ||
        !reader.readU32BE(header.ackBits) ||
        !reader.readU16BE(header.payloadBytes) ||
        !reader.readU8(header.channel) ||
        !reader.readU8(header.flags)) {
        return false;
    }

    return header.protocolId == kProtocolId &&
           header.payloadBytes <= reader.remaining() &&
           header.payloadBytes <= kMaxDatagramBytes - reader.bytesRead() &&
           header.channel < kChannelCount;
}
```

`BE`는 Network Byte Order인 Big-endian으로 읽는다는 뜻이다. Header를 읽기 전에 Pointer Cast하지 않고, 남은 Byte 수를 매 필드 확인해야 조작된 Packet이 Out-of-bounds Read를 만들지 않는다.

## Message별 전달 정책

| Message | 일반적인 정책 | 이유 |
|---|---|---|
| Player Input | Unreliable + 최근 Input 중복 | 새 Input이 오래된 Input보다 중요 |
| Transform Snapshot | Unreliable Sequenced | 늦은 State는 폐기 |
| Inventory 변경 | Reliable Ordered | 누락·순서 변경이 허용되지 않음 |
| Chat | Reliable Ordered | 모든 Message 보존 |
| Spawn·Despawn | Reliable 또는 반복 전송 | World 존재 여부에 중요 |

하나의 Reliable Packet이 유실됐다고 모든 최신 Snapshot을 막으면 Head-of-line Blocking이 발생한다. Channel을 분리하거나 Message별 Sequence Space를 둔다.

Reliability는 보통 다음 네 가지를 조합한다.

| 정책 | 누락 | 중복 | 순서 | 용도 |
|---|---|---|---|---|
| Unreliable | 허용 | 제거 가능 | 무관 | 자주 오는 Snapshot |
| Unreliable Sequenced | 허용 | 제거 | 최신 번호만 수용 | Transform, Aim |
| Reliable Unordered | 재전송 | 제거 | 무관 | 독립적인 Asset Chunk |
| Reliable Ordered | 재전송 | 제거 | 보장 | Inventory Transaction |

Reliable Message를 Packet과 동일시하면 안 된다. 하나의 Message를 여러 Packet에서 재전송할 수 있고, 한 Packet에 여러 Message를 묶을 수도 있다. ACK는 “Packet을 받았다”는 뜻이지 그 안의 Gameplay Transaction이 Database까지 Commit됐다는 뜻은 아니다.

## Sequence와 ACK Bitfield

16-bit Sequence 번호와 최근 32개 Packet 수신 여부를 Bitfield로 보낼 수 있다.

```text
sequence = 100
ack = 95
ack_bits = 000...1011
```

`ack=95`는 95번을 받았고 각 Bit는 94, 93, 92 순서의 수신 여부를 나타낸다. 송신자는 ACK되지 않은 Reliable Message만 재전송한다. Sequence가 최대값에서 0으로 돌아가는 Wrap-around 비교를 일반 정수 비교로 처리하면 오류가 난다.

```cpp
constexpr bool sequenceMoreRecent(std::uint32_t a, std::uint32_t b) {
    return static_cast<std::int32_t>(a - b) > 0;
}

class ReceiveWindow {
public:
    bool record(std::uint32_t sequence) {
        if (!initialized_) {
            latest_ = sequence;
            receivedBits_ = 1;
            initialized_ = true;
            return true;
        }

        if (sequenceMoreRecent(sequence, latest_)) {
            const std::uint32_t distance = sequence - latest_;
            receivedBits_ = distance >= 32 ? 1U : (receivedBits_ << distance) | 1U;
            latest_ = sequence;
            return true;
        }

        const std::uint32_t distance = latest_ - sequence;
        if (distance >= 32 || (receivedBits_ & (1U << distance)) != 0) {
            return false; // Window 밖 또는 중복
        }
        receivedBits_ |= 1U << distance;
        return true;
    }

    std::uint32_t ack() const { return latest_; }
    std::uint32_t ackBits() const { return receivedBits_ >> 1; }

private:
    std::uint32_t latest_{};
    std::uint32_t receivedBits_{};
    bool initialized_{};
};
```

실제 구현에서는 16-bit와 32-bit 중 하나를 정하고 Wrap 주기보다 오래된 Packet을 Window 밖으로 버린다. ACK Spoofing을 막으려면 인증된 Session의 Packet만 ACK 처리해야 한다.

## Tick Rate와 Snapshot Rate

Simulation Tick과 Network Send Rate는 같을 필요가 없다. Server가 60 Hz로 Physics를 계산하면서 20 Hz로 Snapshot을 보낼 수 있다.

Tick Rate를 높이면 입력 반영 Granularity가 좋아지지만 CPU와 Bandwidth가 증가한다. 실제 End-to-end Latency에는 Client Input Sampling, Uplink, Server Queue, Tick 대기, Downlink, Render Buffer와 Display가 모두 포함된다.

```text
latency ≠ ping만의 값
```

Server가 한 Tick을 제시간에 끝내지 못하면 Tick Drift가 누적된다. Tick Duration Histogram과 Overrun 횟수를 운영 Metric으로 수집한다.

대략적인 Bandwidth Budget을 먼저 계산할 수 있다. Player 20명에게 각 400 Byte Snapshot을 초당 20번 보낸다면 Payload만 `20 × 400 × 20 = 160,000 Byte/s`, 약 1.28 Mbps다. 여기에 UDP/IP Header, 암호화 Tag, 재전송과 다른 Message가 더해진다. Server 100 Session이면 Egress가 선형으로 커진다.

Tick마다 무조건 전송하지 말고 별도 Network Scheduler가 누적 Budget 안에서 우선순위를 선택하게 한다.

```cpp
void ReplicationScheduler::buildPacket(Connection& connection, Tick tick) {
    PacketBuilder packet{kMaxDatagramBytes};
    packet.writeHeader(connection.makeHeader());

    const std::size_t byteBudget = connection.congestionWindow().availableBytes();
    auto candidates = relevance_.query(connection.viewer(), tick);
    std::ranges::sort(candidates, std::greater{}, &ReplicationCandidate::priority);

    for (const ReplicationCandidate& candidate : candidates) {
        if (packet.bytesWritten() >= byteBudget || !packet.canFit(candidate.maxBytes)) {
            break;
        }
        if (candidate.dueAt > tick || !candidate.entity->isAlive()) {
            continue;
        }
        serializeDelta(packet, connection.baselineFor(candidate.entityId), *candidate.entity);
        connection.markReplicated(candidate.entityId, tick);
    }

    transport_.send(connection.endpoint(), packet.finishAuthenticated());
}
```

우선순위에는 거리만 아니라 마지막 전송 후 경과 시간, 전투 중요도, 화면 크기와 Starvation 방지 가중치를 포함한다.

## Delta Compression

Client가 확인한 Baseline Snapshot과 현재 State의 차이만 보낸다.

```text
baseline 120: position=(10,20), health=100
snapshot 125: position=(11,20)만 전송
```

Packet Loss로 Baseline을 받지 못했다면 Delta를 복원할 수 없다. Packet에 Baseline ID를 포함하고 Client가 보유한 Snapshot을 ACK하도록 한다. 주기적인 Full Snapshot이나 새 Baseline 전환도 필요하다.

Float Position을 World 범위와 필요한 정밀도에 맞춰 Quantization하면 크기를 줄일 수 있다. 예를 들어 방 하나의 Local 좌표를 16-bit로 표현할 수 있지만 Open World 절대 좌표에는 부족할 수 있다.

Delta 적용 순서는 다음과 같다.

1. Server가 Client가 ACK한 `baselineId=120`을 찾는다.
2. 현재 Entity State와 Baseline을 Field별로 비교한다.
3. 바뀐 Field의 Bit Mask와 양자화한 값만 쓴다.
4. Packet에 `baselineId`와 새 `snapshotId=125`를 포함한다.
5. Client가 Baseline 120을 보유한 경우에만 Delta를 적용한다.
6. 없으면 Delta를 버리고 Full Snapshot 또는 Resync를 요청한다.

```cpp
void writePlayerDelta(BitWriter& writer, const PlayerState& base, const PlayerState& now) {
    enum Field : std::uint8_t { Position = 1, Velocity = 2, Health = 4, Stance = 8 };
    std::uint8_t mask{};
    if (!nearlyEqual(base.position, now.position, 0.01F)) mask |= Position;
    if (!nearlyEqual(base.velocity, now.velocity, 0.02F)) mask |= Velocity;
    if (base.health != now.health) mask |= Health;
    if (base.stance != now.stance) mask |= Stance;

    writer.writeBits(mask, 4);
    if (mask & Position) writeQuantizedPosition(writer, now.position);
    if (mask & Velocity) writeQuantizedVelocity(writer, now.velocity);
    if (mask & Health) writer.writeBits(std::clamp(now.health, 0, 100), 7);
    if (mask & Stance) writer.writeBits(static_cast<std::uint8_t>(now.stance), 2);
}
```

Delta 비교에 `float == float`를 사용하면 미세한 Noise 때문에 매 Tick 값이 바뀐 것으로 판정될 수 있다. Network 정밀도에 맞춘 Quantized 값끼리 비교하는 편이 안정적이다.

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

Spatial Grid의 가장 단순한 구현은 World를 일정 크기 Cell로 나누고 Entity가 속한 Cell을 갱신하는 것이다. Viewer 주변 Cell만 조회한 뒤 Team, Line of Sight와 Gameplay Subscription Filter를 적용한다. Grid 조회 결과를 그대로 보내지 않고 Spawn/Update/Despawn 상태 전이를 Connection별로 관리해야 한다.

```cpp
for (EntityId id : spatialGrid.queryCircle(viewer.position, prefetchRadius)) {
    const Entity& entity = world.get(id);
    if (!visibilityPolicy.canObserve(viewer, entity)) {
        continue;
    }

    const float distance = length(entity.position - viewer.position);
    const float urgency = secondsSinceLastSend(connection, id);
    const float gameplayWeight = entity.isThreatTo(viewer) ? 4.0F : 1.0F;
    candidates.push_back({id, gameplayWeight * urgency / std::max(distance, 1.0F)});
}
```

경계에서 Entity가 매 Tick 들어왔다 나갔다 하지 않도록 진입 반경보다 이탈 반경을 크게 두는 Hysteresis를 적용한다.

## Congestion과 MTU

UDP도 Network Capacity를 넘겨 보내면 Queue와 Loss가 증가한다. 전송량을 제어하지 않으면 Packet Loss를 재전송이 더 키우는 Collapse가 생긴다. RTT, Loss와 ACK 속도를 이용해 Send Rate를 조절한다.

IP Fragmentation은 일부 Fragment만 유실돼도 전체 Datagram이 사라지고 NAT·Firewall 호환성도 나빠질 수 있다. Path MTU보다 작은 Packet을 만들고 큰 Message는 Application 수준에서 Fragment와 재조립을 관리한다.

재조립 Buffer에는 `messageId`, 전체 Fragment 수, 받은 Bitset, 만료 시각과 최대 총 크기를 둔다. 공격자가 마지막 Fragment를 보내지 않아 Memory를 계속 차지하지 못하도록 Connection당 동시 Message 수와 Timeout을 제한한다. 실시간 Snapshot은 Fragment하지 말고 Entity 수를 줄이거나 다음 Packet으로 넘기는 편이 낫다.

## 보안

UDP Source Address는 위조될 수 있다. Session Token, Packet Authentication, Replay Window와 Rate Limit이 필요하다. Client가 보낸 Position이나 Damage 결과를 신뢰하지 않고 Input과 의도만 검증한다.

Packet Parser는 공격 표면이다. Length, Entity ID, Compression 값과 Fragment 수를 사용하기 전에 범위를 확인한다. 암호화 여부와 별개로 Server CPU를 소모시키는 Amplification과 Handshake Flood도 제한한다.

## 수신 Packet의 전체 처리 순서

1. Socket에서 제한된 크기의 Datagram을 받는다.
2. IP와 Port만으로 Session을 신뢰하지 않고 Cookie 또는 Session Token을 확인한다.
3. Header 길이, Protocol ID와 Payload 길이를 검사한다.
4. 인증 Tag를 검증한 뒤에만 ACK와 Sequence Window를 갱신한다.
5. 중복 또는 너무 오래된 Packet을 버린다.
6. Channel별 Message Decoder로 전달한다.
7. Message Field의 범위와 현재 Session State에서 허용된 명령인지 검사한다.
8. Gameplay Thread에는 검증된 Command만 Queue로 넘긴다.

Network Thread가 World State를 직접 수정하면 Simulation Tick 도중 State가 바뀌어 재현성이 깨질 수 있다. 수신과 Simulation 사이에는 Tick 경계에서 소비하는 Queue를 둔다.

## 기억할 점

게임 Network Protocol은 “UDP 위에 TCP를 다시 만드는 것”이 아니다. 각 데이터가 늦게 도착했을 때 가치가 남아 있는지를 기준으로 Reliability, Ordering, Frequency와 Priority를 설계하는 일이다.

# Reference

- [Unreal Engine Networking and Multiplayer](https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-and-multiplayer-in-unreal-engine)
- [[Authoritative Game Server와 Session Architecture]]
