---
id: Authoritative Game Server와 Session Architecture
started: 2026-06-14
tags:
  - ✅DONE
  - Game-Development
  - Game-Server
  - Architecture
group: "[[게임 개발]]"
---

# Authoritative Game Server와 Session Architecture

게임 Server는 API 요청을 처리하는 일반 Backend와 다른 시간 제약을 가진다. Match가 시작되면 일정 Tick 안에 Input을 소비하고 World를 갱신해 모든 Client에 결과를 전달해야 한다. 평균 처리량보다 한 Session의 Tick Deadline과 State 일관성이 중요하다.

## 먼저 알아둘 Server 구성

**Session**은 한 Match의 Player, World와 규칙을 실행하는 단위다. 일반 Web API는 요청이 끝나면 Local State를 버릴 수 있지만, Session Server는 Match가 끝날 때까지 수천 Tick의 State를 Memory에 유지한다.

| 구성 요소 | 책임 | State 수명 |
|---|---|---|
| Gateway | 인증, DDoS 방어와 접속 Routing | Connection 단위 |
| Matchmaker | Skill·Region·Party 조건으로 참가자 조합 | Queue 단위 |
| Allocator | 실행할 Session Process와 Port 배정 | 할당 단위 |
| Session Server | Input, Simulation, 판정과 Replication | Match 단위 |
| Result Service | 전적·보상·Ranking 저장 | 영구 |

한 Process가 여러 Session을 실행할 수도 있고, 격리를 위해 Process 하나가 Session 하나만 실행할 수도 있다. 어느 쪽이든 한 Session의 긴 GC Pause나 Crash가 다른 Session에 미치는 범위를 알아야 한다.

## Server Authority

Client는 “내 위치는 여기다”가 아니라 “오른쪽으로 이동하려 했다”는 Input을 보낸다. Server가 이동 가능 여부, 충돌, Damage와 보상을 계산한다.

```text
Client intent -> validation -> authoritative simulation -> replicated state
```

모든 것을 Server에서 계산하면 Cheat 방어에는 유리하지만 Latency와 비용이 증가한다. Camera, Animation Blend와 Cosmetic Particle은 Client에 두고 승패·경제·충돌처럼 결과에 영향을 주는 State를 Server가 소유한다.

권위는 “모든 Code를 Server에서 실행한다”가 아니라 값마다 최종 결정권을 정하는 것이다. 위치·충돌·Damage는 Server, Inventory·재화는 Durable Backend, Camera·Particle은 Client가 맡는 식이다.

Server는 Network Thread에서 World를 직접 바꾸지 않는다. 인증·역직렬화·범위 검사를 통과한 Command를 제한된 Queue에 넣고 Simulation Thread가 Tick 경계에서 소비한다.

```cpp
struct MoveCommand {
    PlayerId playerId;
    std::uint32_t sequence;
    std::uint32_t clientTick;
    QuantizedAxis movement;
    std::uint16_t buttons;
};

std::expected<MoveCommand, CommandError> validateMove(
    const SessionView& session,
    const AuthenticatedConnection& connection,
    const MovePacket& packet
) {
    return validateOwnership(session, connection, packet.playerId)
        .and_then([&](PlayerId playerId) {
            return validateSequence(connection, packet.sequence)
                .transform([&] { return playerId; });
        })
        .and_then([&](PlayerId playerId) {
            return validateTickWindow(session.tick(), packet.clientTick)
                .transform([&] { return playerId; });
        })
        .and_then([&](PlayerId playerId) {
            return decodeAxis(packet.moveX, packet.moveY)
                .transform([&](QuantizedAxis axis) {
                    return MoveCommand{playerId, packet.sequence, packet.clientTick, axis, packet.buttons};
                });
        });
}

void NetworkIngress::onMovePacket(const AuthenticatedConnection& connection, const MovePacket& packet) {
    validateMove(sessionView_, connection, packet)
        .and_then([&](MoveCommand command) { return commandQueue_.tryPush(std::move(command)); })
        .or_else([&](CommandError error) {
            metrics_.increment("session.command.rejected", tag("reason", toString(error)));
            return std::expected<void, CommandError>{};
        });
}
```

Queue가 가득 찼을 때 Memory를 늘리지 말고 Connection별 Rate Limit 또는 Disconnect 정책을 적용한다. `std::expected` 흐름은 검증 실패 시 World를 변경하지 않는 경계를 드러낸다.

## Dedicated Server와 Listen Server

Listen Server는 Player 한 명이 Host이므로 비용은 낮지만 Host Advantage, NAT와 Host 종료 문제가 있다. Dedicated Server는 중립적인 권위와 안정적인 Network를 제공하지만 Region별 Capacity와 운영 비용이 필요하다.

경쟁 게임은 Dedicated Server가 일반적이고 소규모 Cooperative Game은 Listen Server와 Host Migration을 선택할 수 있다.

## Control Plane과 Session Plane

```text
Control Plane
  Login, Party, Lobby, Matchmaking, Allocation

Session Plane
  Real-time UDP, Simulation Tick, Replication

Data Plane
  Profile, Inventory, Ranking, Match Result
```

Matchmaking API와 실시간 Session을 같은 Process에 넣으면 HTTP Traffic Spike나 GC가 Tick을 방해할 수 있다. Session Server는 Match 단위로 격리하고 Control Plane이 Region과 Build Version에 맞는 Instance를 할당한다.

한 Match는 보통 다음 순서로 진행된다.

1. Client가 Login Service에서 Access Token을 받는다.
2. Party가 Matchmaking Ticket을 만든다.
3. Matchmaker가 Skill, Ping과 Party 조건으로 참가자를 묶는다.
4. Allocator가 Region과 Build Version에 맞는 Session을 확보한다.
5. Control Plane이 짧은 수명의 1회용 Join Token을 발급한다.
6. Client가 Session에 UDP Handshake를 보낸다.
7. Session이 Token, Protocol Version과 Player Slot을 검증한다.
8. 모든 Player가 Ready가 되면 Fixed Tick Simulation을 시작한다.
9. 종료 후 Server가 서명된 Result Event를 Durable Queue에 기록한다.
10. Result Service가 `match_id` 기준으로 전적과 보상을 멱등 반영한다.

## Matchmaking

Match 품질은 Queue 시간, Skill 차이, Ping, Party Size, Platform과 Role 제약의 다목적 최적화 문제다. 처음에는 좁은 조건으로 찾고 대기 시간이 늘면 허용 범위를 단계적으로 넓힌다.

Server 선택은 평균 Ping만 보지 않는다. Player 모두의 지연과 Data Center Capacity를 고려하고, 선택 후 발급한 짧은 수명의 Join Token으로 임의 Session 접속을 막는다.

서울 Ping이 `[20, 24, 140, 150] ms`, 도쿄가 `[65, 70, 75, 80] ms`라면 평균뿐 아니라 최대 Ping과 편차를 봐야 한다. `평균 + 최대 지연 가중치 + 표준편차 가중치 + Capacity Penalty` 같은 Score를 사용하고, 오래 기다린 Ticket은 조건을 단계적으로 완화한다.

## Session Lifecycle

```text
ALLOCATING -> WARMING -> ACCEPTING -> IN_GAME
-> RESULT_COMMITTING -> DRAINING -> TERMINATED
```

Image Pull과 Process 시작 시간이 길면 Player가 Match 후 기다린다. Warm Pool을 두면 지연은 줄지만 Idle 비용이 생긴다. Autoscaling은 현재 CPU보다 Queue 길이, 예상 Match 시작률과 Session 평균 지속 시간을 선행 신호로 사용해야 한다.

배포 시 진행 중 Match를 즉시 종료하지 않는다. 새 Build는 신규 Session만 받고 기존 Server는 Match 종료까지 Drain한다. Protocol과 Content Version을 Handshake에서 검증한다.

상태 전이를 임의 대입하지 않고 허용된 Event로 제한한다.

```cpp
enum class SessionPhase { Allocating, Warming, Accepting, InGame, ResultCommitting, Draining, Terminated };

class SessionLifecycle {
public:
    std::expected<void, TransitionError> apply(SessionEvent event) {
        return transitionFor(phase_, event)
            .transform([&](SessionPhase next) {
                const SessionPhase previous = std::exchange(phase_, next);
                audit_.record(previous, next, event, clock_.now());
            });
    }

private:
    static std::expected<SessionPhase, TransitionError> transitionFor(
        SessionPhase phase,
        SessionEvent event
    ) {
        static const std::map<std::pair<SessionPhase, SessionEvent>, SessionPhase> transitions{
            {{SessionPhase::Allocating, SessionEvent::CapacityReady}, SessionPhase::Warming},
            {{SessionPhase::Warming, SessionEvent::AssetsLoaded}, SessionPhase::Accepting},
            {{SessionPhase::Accepting, SessionEvent::PlayersReady}, SessionPhase::InGame},
            {{SessionPhase::InGame, SessionEvent::MatchFinished}, SessionPhase::ResultCommitting},
            {{SessionPhase::ResultCommitting, SessionEvent::ResultPersisted}, SessionPhase::Draining},
            {{SessionPhase::Draining, SessionEvent::ConnectionsClosed}, SessionPhase::Terminated},
        };

        const auto found = transitions.find({phase, event});
        return found == transitions.end()
            ? std::unexpected(TransitionError{phase, event})
            : std::expected<SessionPhase, TransitionError>{found->second};
    }

    SessionPhase phase_{SessionPhase::Allocating};
    SessionAudit& audit_;
    Clock& clock_;
};
```

전이 Log에는 `session_id`, Build, 이전/다음 상태, 원인과 소요 시간을 남긴다. `WARMING` Timeout이면 Allocation을 취소하고 Player를 다시 Queue로 돌린다.

## Persistence Boundary

실시간 Tick마다 Database에 쓰면 Latency와 장애 결합도가 커진다. Match 중 필요한 State는 Memory에 두고 중요한 Event 또는 결과를 비동기로 저장한다.

결과 저장은 중복될 수 있으므로 `match_id`와 결과 Version을 Idempotency Key로 사용한다. Server가 결과를 보낸 뒤 죽는 경우를 위해 Durable Event나 Reconciliation이 필요하다. Client가 제출한 보상 결과를 진실로 사용하지 않는다.

Match Result와 발행할 Event를 같은 Transaction에 저장하는 Transactional Outbox를 쓰면 “DB 저장은 됐지만 Message 발행은 안 된” 틈을 복구할 수 있다. Consumer는 `match_id + result_version`으로 중복 Event를 안전하게 무시한다.

## Anti-cheat

Server Authority만으로 모든 Cheat를 막지는 못한다.

- 이동 속도와 가속도, Fire Rate의 물리적 범위 검증
- Client가 볼 수 없는 Entity 정보 최소화
- Lag Compensation 시간의 Server-side Clamp
- Replay와 입력 History를 이용한 사후 판정
- Binary Integrity와 Anti-tamper는 보조 신호로 사용

Detection은 False Positive가 있으므로 즉시 Ban, Shadow Pool, 추가 관찰 등 대응 단계를 나눈다. 탐지 규칙 자체가 공격자에게 Oracle이 되지 않도록 한다.

## 운영 관측성

일반 CPU·Memory 외에 게임 고유 지표가 필요하다.

- Tick Duration P50/P95/P99와 Deadline Overrun
- Session당 Player, Entity와 Replication Byte
- RTT, Jitter, Packet Loss, Reconciliation 거리
- Matchmaking Queue 시간과 품질
- Disconnect 이유, Crash와 Match Completion Rate
- Region·Build Version별 결과 저장 실패

Packet Capture와 Replay에는 개인정보와 전략 정보가 포함될 수 있어 접근 권한과 Retention을 제한한다.

## Capacity를 계산하는 순서

1. 60 Hz라면 16.67 ms인 Tick Budget을 정한다.
2. Session당 최대 Player와 Entity 수를 정한다.
3. Simulation, Physics와 Replication P99 시간을 측정한다.
4. Core 하나에 넣을 Session 수를 최악 조건으로 계산한다.
5. Match 시작률과 평균 지속 시간으로 동시 Session 수를 추정한다.
6. Region 장애, 배포 Drain과 Warm Pool 여유를 더한다.

평균 CPU 40%만 보고 Session을 더 넣으면 전투가 몰린 Tick의 P99가 Deadline을 넘을 수 있다. Autoscaling도 CPU뿐 아니라 Queue Player, 할당 실패율, Warm Instance 수와 예상 종료 Session 수를 사용한다.

## 기억할 점

게임 Server Architecture의 핵심은 무상태 API 확장보다 시간에 민감한 Session을 격리하고 안전하게 수명 주기를 관리하는 데 있다. 권위는 Server에 두되 반응성은 Client Prediction으로 보완하고, Match 결과는 별도의 Durable Boundary에서 수렴시킨다.

# Reference

- [Unreal Engine Networking and Multiplayer](https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-and-multiplayer-in-unreal-engine)
- [[UDP Reliability Tick과 Interest Management]]
