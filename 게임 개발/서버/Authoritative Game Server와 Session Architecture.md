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

## Server Authority

Client는 “내 위치는 여기다”가 아니라 “오른쪽으로 이동하려 했다”는 Input을 보낸다. Server가 이동 가능 여부, 충돌, Damage와 보상을 계산한다.

```text
Client intent -> validation -> authoritative simulation -> replicated state
```

모든 것을 Server에서 계산하면 Cheat 방어에는 유리하지만 Latency와 비용이 증가한다. Camera, Animation Blend와 Cosmetic Particle은 Client에 두고 승패·경제·충돌처럼 결과에 영향을 주는 State를 Server가 소유한다.

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

## Matchmaking

Match 품질은 Queue 시간, Skill 차이, Ping, Party Size, Platform과 Role 제약의 다목적 최적화 문제다. 처음에는 좁은 조건으로 찾고 대기 시간이 늘면 허용 범위를 단계적으로 넓힌다.

Server 선택은 평균 Ping만 보지 않는다. Player 모두의 지연과 Data Center Capacity를 고려하고, 선택 후 발급한 짧은 수명의 Join Token으로 임의 Session 접속을 막는다.

## Session Lifecycle

```text
ALLOCATING -> WARMING -> ACCEPTING -> IN_GAME
-> RESULT_COMMITTING -> DRAINING -> TERMINATED
```

Image Pull과 Process 시작 시간이 길면 Player가 Match 후 기다린다. Warm Pool을 두면 지연은 줄지만 Idle 비용이 생긴다. Autoscaling은 현재 CPU보다 Queue 길이, 예상 Match 시작률과 Session 평균 지속 시간을 선행 신호로 사용해야 한다.

배포 시 진행 중 Match를 즉시 종료하지 않는다. 새 Build는 신규 Session만 받고 기존 Server는 Match 종료까지 Drain한다. Protocol과 Content Version을 Handshake에서 검증한다.

## Persistence Boundary

실시간 Tick마다 Database에 쓰면 Latency와 장애 결합도가 커진다. Match 중 필요한 State는 Memory에 두고 중요한 Event 또는 결과를 비동기로 저장한다.

결과 저장은 중복될 수 있으므로 `match_id`와 결과 Version을 Idempotency Key로 사용한다. Server가 결과를 보낸 뒤 죽는 경우를 위해 Durable Event나 Reconciliation이 필요하다. Client가 제출한 보상 결과를 진실로 사용하지 않는다.

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

## 기억할 점

게임 Server Architecture의 핵심은 무상태 API 확장보다 시간에 민감한 Session을 격리하고 안전하게 수명 주기를 관리하는 데 있다. 권위는 Server에 두되 반응성은 Client Prediction으로 보완하고, Match 결과는 별도의 Durable Boundary에서 수렴시킨다.

# Reference

- [Unreal Engine Networking and Multiplayer](https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-and-multiplayer-in-unreal-engine)
- [[UDP Reliability Tick과 Interest Management]]
