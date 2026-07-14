---
id: Netcode 모델 Lockstep Snapshot Prediction Rollback
started: 2026-06-05
tags:
  - ✅DONE
  - Game-Development
  - Netcode
  - Multiplayer
group: "[[게임 개발]]"
---

# Netcode 모델: Lockstep, Snapshot, Prediction과 Rollback

Netcode의 목표는 모든 화면을 완벽히 같은 순간으로 만드는 것이 아니다. Latency, Packet Loss와 서로 다른 Simulation Clock 속에서도 플레이어가 납득할 수 있는 결과를 제공하는 것이다. 장르에 따라 “정확성”, “즉각적인 입력 반응”과 “많은 객체”의 우선순위가 다르다.

## Latency를 숨길 수는 있어도 없앨 수는 없다

왕복 지연이 100 ms인 환경에서 Server 확인을 기다린 뒤 움직이면 입력이 무겁게 느껴진다. Client가 먼저 움직이면 반응성은 좋아지지만 Server 결과와 다를 때 수정해야 한다. 모든 Netcode는 이 Trade-off를 다른 방식으로 선택한다.

## Deterministic Lockstep

각 Client는 World State 대신 매 Tick의 Input만 공유한다. 모든 Player의 Input이 도착하면 같은 Simulation을 실행한다.

```text
tick 100: P1=move-right, P2=attack
tick 101: P1=idle,       P2=move-left
```

Traffic은 작지만 가장 느린 Player를 기다리므로 지연에 민감하다. 모든 Platform에서 같은 Input이 같은 State를 만들어야 한다. Floating-point 연산 순서, Random Seed와 Container iteration 순서까지 Deterministic해야 한다. RTS처럼 Unit이 많고 입력 빈도가 State 크기보다 작은 장르에 적합하다.

## Authoritative Snapshot

Server가 World를 Simulation하고 주기적으로 State Snapshot을 보낸다. Client는 받은 두 Snapshot 사이를 보간한다.

```text
server simulation: 60 Hz
snapshot send:     20 Hz
client render:    144 Hz
```

Server 권위와 Cheat 방어에 유리하고 복잡한 Physics의 완전한 결정성을 요구하지 않는다. 반면 State가 크므로 Delta Compression과 Interest Management가 중요하다. FPS와 대규모 Action Game에서 널리 쓰이는 기반이다.

## Client-side Prediction과 Reconciliation

Local Player 입력은 Server 응답을 기다리지 않고 즉시 Simulation한다. 각 Input에 Sequence 번호를 붙여 Server로 전송한다. Server Snapshot에는 마지막으로 처리한 Input 번호가 포함된다.

Client가 Snapshot을 받으면 다음 순서로 교정한다.

1. Authoritative State로 되돌린다.
2. Server가 처리한 Input을 Pending Queue에서 제거한다.
3. 아직 확인되지 않은 Input을 순서대로 다시 실행한다.

이 방식은 Local 입력 지연을 숨긴다. Simulation Code가 Client와 Server에서 충분히 같아야 하며 큰 오차를 즉시 Snap하면 화면이 튄다. Render Transform을 별도로 Smooth하게 따라가게 만들 수 있지만 Gameplay State 자체를 늦추면 안 된다.

## Snapshot Interpolation

Remote Player는 미래 State를 예측하기보다 약간 과거를 그리는 것이 안정적이다. 100 ms Interpolation Buffer를 두면 Client는 `serverTime - 100ms` 시점 양쪽 Snapshot을 가질 가능성이 높다.

```text
수신 Snapshot: 10.0s, 10.05s, 10.11s
Render Time:   10.06s
결과: 10.05와 10.11 사이 보간
```

Buffer가 크면 Jitter에 강하지만 다른 Player가 더 늦게 보인다. Buffer가 작아 Snapshot이 부족하면 Extrapolation하거나 마지막 State에서 멈춰야 한다.

## Rollback Netcode

주로 대전 격투 게임에서 사용한다. Remote Input이 아직 오지 않았으면 최근 Input이 계속된다고 예측하고 즉시 Frame을 진행한다. 실제 Input이 다르면 과거 State를 복원해 현재 Frame까지 빠르게 재실행한다.

```text
frame 30: remote input 미도착 -> idle로 예측
frame 33: frame 30의 attack 도착
-> frame 30 state 복원
-> 30~32 재실행
-> 수정된 frame 33 표시
```

입력 반응은 빠르지만 Simulation이 Deterministic해야 하고 과거 State를 저장할 Memory와 빠른 Replay가 필요하다. 오디오, Particle과 외부 Side Effect는 중복 실행되지 않도록 Simulation Event와 Presentation을 분리한다.

## Server Rewind와 Lag Compensation

Shooter에서 Client 화면상 명중했지만 Server 현재 시점의 Target은 이미 이동했을 수 있다. Server는 Player의 관측 시간으로 Hitbox History를 되감아 Ray를 판정한다.

```text
shot_time = server_receive_time - estimated_one_way_latency
rewound_hitboxes = history.sample(shot_time)
hit = raycast(origin, direction, rewound_hitboxes)
```

공격자에게 공정하지만 피해자는 벽 뒤에서 맞았다고 느낄 수 있다. Rewind 최대 시간, Clock 추정, Teleport와 Spawn 경계를 제한해야 한다. Client가 보낸 시간만 신뢰하면 과거를 조작할 수 있으므로 Server가 관측한 RTT 범위에서 Clamp한다.

## 장르별 선택

| 장르 | 일반적인 중심 모델 | 이유 |
|---|---|---|
| RTS | Deterministic Lockstep | 많은 Unit State 대신 Input 전송 |
| 격투 | Rollback | Frame 단위 입력 반응과 1:1 결정성 |
| FPS | Snapshot + Prediction + Rewind | Server 권위와 즉각적인 이동·사격 |
| Racing | Prediction + Snapshot | 연속 이동과 충돌 교정 |
| MMO | Authoritative Snapshot + Interest | 큰 World와 Cheat 방어 |

실제 게임은 하나만 고르지 않는다. Local Player는 Prediction, Remote Player는 Interpolation, Projectile은 Server Authority, Cosmetic Effect는 Client-only로 처리할 수 있다.

## 기억할 점

좋은 Netcode는 Network를 감추는 Code가 아니라 불확실성을 어디에서 수용할지 명시하는 설계다. State 권위, 예측 가능성, 교정 방식과 사용자에게 보이는 Artifact를 함께 결정해야 한다.

# Reference

- [GGPO Rollback SDK](https://github.com/pond3r/ggpo)
- [Unreal Engine Networking and Multiplayer](https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-and-multiplayer-in-unreal-engine)
- [[Client Prediction Snapshot Interpolation과 Rollback 구현]]
- [[UDP Reliability Tick과 Interest Management]]
