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

## 먼저 알아둘 기초 용어

온라인 게임에서는 각 컴퓨터가 자기 안에 World의 복사본을 가진다. Server의 World와 각 Client의 World는 Network 전달 시간 때문에 완전히 같은 순간을 보고 있지 않다. Netcode는 이 여러 복사본을 충분히 비슷하게 유지하는 규칙의 묶음이다.

| 용어 | 뜻 | 쉬운 예 |
|---|---|---|
| Client | Player의 입력을 받고 화면을 그리는 Program | 내 PC에서 실행 중인 Game |
| Server | 규칙을 판정하고 기준 State를 관리하는 Program | 누가 맞았는지 결정하는 심판 |
| State | 특정 시점의 World를 설명하는 값 | 위치, 속도, 체력, 총알 수 |
| Input | Player가 하려는 행동 | 이동축, 점프, 공격 Button |
| Tick | Simulation을 한 번 갱신하는 고정 단위 | 60 Hz이면 1 Tick은 약 16.67 ms |
| Snapshot | 특정 Tick의 State를 복사한 기록 | Tick 120의 모든 Player 위치 |
| RTT | Packet이 갔다가 응답이 돌아오는 왕복 시간 | Ping 80 ms |
| Jitter | Packet 도착 간격이 일정하지 않은 현상 | 40 ms, 42 ms, 110 ms로 들쭉날쭉 도착 |
| Packet Loss | 전송한 Packet이 중간에서 사라지는 현상 | 100개 중 2개가 도착하지 않음 |
| Authority | 최종 결과를 결정할 권한 | Server 위치가 Client 위치보다 우선 |

`60 Hz`는 1초에 60번 갱신한다는 뜻이다. 한 Tick의 시간은 `1 / 60초 = 약 16.67 ms`다. Rendering이 144 Hz여도 Server Simulation은 60 Hz일 수 있고, Network Snapshot은 20 Hz로만 보낼 수도 있다. 이 Clock들은 서로 다른 목적을 가진다.

## 왜 Client마다 다른 World가 보이는가

Player A가 0 ms에 이동 Button을 눌렀다고 가정한다.

```text
0 ms   A Client: 입력을 감지
40 ms  Server: A의 입력을 수신하고 이동 판정
80 ms  A Client: Server 결과를 수신
95 ms  B Client: A의 새 위치를 수신
```

0~95 ms 사이에 A, Server와 B가 알고 있는 위치는 서로 다르다. 이 차이는 Bug가 아니라 물리적으로 떨어진 컴퓨터가 통신할 때 생기는 정상적인 결과다. 설계자는 다음 세 질문에 답해야 한다.

1. 최종 State는 누가 결정하는가?
2. 결과를 기다리는 동안 Client는 무엇을 보여 주는가?
3. 나중에 다른 결과가 도착하면 어떻게 고치는가?

Lockstep, Snapshot, Prediction과 Rollback은 이 질문에 서로 다른 답을 준다.

## Latency를 숨길 수는 있어도 없앨 수는 없다

왕복 지연이 100 ms인 환경에서 Server 확인을 기다린 뒤 움직이면 입력이 무겁게 느껴진다. Client가 먼저 움직이면 반응성은 좋아지지만 Server 결과와 다를 때 수정해야 한다. 모든 Netcode는 이 Trade-off를 다른 방식으로 선택한다.

Latency는 한 숫자로 끝나지 않는다. 입력 장치 Polling, 다음 Simulation Tick까지의 대기, Packet 전송, Server 처리, Client Render Queue와 Display Scan-out이 모두 더해진다. 따라서 Ping이 40 ms여도 Input-to-photon Latency는 그보다 훨씬 클 수 있다.

```text
전체 체감 지연
= 입력 Sampling 대기
+ Client Tick 대기
+ Uplink
+ Server Tick 대기와 처리
+ Downlink
+ Interpolation 또는 Render Queue
+ Display Scan-out
```

## Deterministic Lockstep

각 Client는 World State 대신 매 Tick의 Input만 공유한다. 모든 Player의 Input이 도착하면 같은 Simulation을 실행한다.

```text
tick 100: P1=move-right, P2=attack
tick 101: P1=idle,       P2=move-left
```

Traffic은 작지만 가장 느린 Player를 기다리므로 지연에 민감하다. 모든 Platform에서 같은 Input이 같은 State를 만들어야 한다. Floating-point 연산 순서, Random Seed와 Container iteration 순서까지 Deterministic해야 한다. RTS처럼 Unit이 많고 입력 빈도가 State 크기보다 작은 장르에 적합하다.

처리 순서는 다음과 같다.

1. 각 Client가 `tick 100`에 실행할 Input을 만든다.
2. Input에 Tick 번호를 붙여 다른 Peer 또는 중계 Server에 보낸다.
3. 모든 참가자의 Tick 100 Input이 모일 때까지 기다린다.
4. 모든 컴퓨터가 같은 Input 집합으로 Tick 100을 계산한다.
5. 다음 Tick으로 넘어간다.

Unit 10,000개의 위치를 매번 보내는 대신 “Player 1이 Unit 20개에 이동 명령을 내렸다”는 작은 Input만 보내므로 Traffic이 작다. 대신 한 컴퓨터에서 결과가 조금이라도 달라지면 이후 모든 Tick의 차이가 누적되는 **Desync**가 발생한다. 주기적으로 World State Hash를 비교하면 언제 처음 달라졌는지 찾을 수 있다.

## Authoritative Snapshot

Server가 World를 Simulation하고 주기적으로 State Snapshot을 보낸다. Client는 받은 두 Snapshot 사이를 보간한다.

```text
server simulation: 60 Hz
snapshot send:     20 Hz
client render:    144 Hz
```

Server 권위와 Cheat 방어에 유리하고 복잡한 Physics의 완전한 결정성을 요구하지 않는다. 반면 State가 크므로 Delta Compression과 Interest Management가 중요하다. FPS와 대규모 Action Game에서 널리 쓰이는 기반이다.

Snapshot 방식의 한 Cycle은 다음과 같다.

1. Client가 `input sequence=52, move=right`를 Server에 보낸다.
2. Server가 다음 Tick에서 충돌과 이동 가능 여부를 검사한다.
3. Server가 Player 위치를 `x=12.4`로 확정한다.
4. Snapshot 전송 시점이 되면 관련 Client에 Tick과 State를 보낸다.
5. 내 Character는 Prediction 결과를 교정하고, 다른 Character는 Snapshot 사이를 보간한다.

60 Hz Simulation에서 20 Hz Snapshot을 보내면 Snapshot 사이에는 Simulation Tick이 3개 있다. Client가 144 Hz로 화면을 그린다면 같은 Network State를 여러 Render Frame에 걸쳐 부드럽게 표현해야 한다.

## Client-side Prediction과 Reconciliation

Local Player 입력은 Server 응답을 기다리지 않고 즉시 Simulation한다. 각 Input에 Sequence 번호를 붙여 Server로 전송한다. Server Snapshot에는 마지막으로 처리한 Input 번호가 포함된다.

Client가 Snapshot을 받으면 다음 순서로 교정한다.

1. Authoritative State로 되돌린다.
2. Server가 처리한 Input을 Pending Queue에서 제거한다.
3. 아직 확인되지 않은 Input을 순서대로 다시 실행한다.

이 방식은 Local 입력 지연을 숨긴다. Simulation Code가 Client와 Server에서 충분히 같아야 하며 큰 오차를 즉시 Snap하면 화면이 튄다. Render Transform을 별도로 Smooth하게 따라가게 만들 수 있지만 Gameplay State 자체를 늦추면 안 된다.

예를 들어 Server가 확인한 위치가 `10.0`이고 아직 확인하지 않은 Input 두 개가 각각 `+0.2` 이동이라면 Client는 `10.0`으로만 돌아가지 않는다.

```text
authoritative position = 10.0
replay input 53        = +0.2
replay input 54        = +0.2
reconciled position    = 10.4
```

여기서 충돌 결과 때문에 원래 Client 예측이 `10.7`이었다면 Gameplay State는 즉시 `10.4`로 바로잡는다. 화면에 쓰는 Render 위치만 짧은 시간 동안 `10.7 -> 10.4`로 부드럽게 이동시켜 교정을 덜 거슬리게 할 수 있다.

## Snapshot Interpolation

Remote Player는 미래 State를 예측하기보다 약간 과거를 그리는 것이 안정적이다. 100 ms Interpolation Buffer를 두면 Client는 `serverTime - 100ms` 시점 양쪽 Snapshot을 가질 가능성이 높다.

```text
수신 Snapshot: 10.0s, 10.05s, 10.11s
Render Time:   10.06s
결과: 10.05와 10.11 사이 보간
```

Buffer가 크면 Jitter에 강하지만 다른 Player가 더 늦게 보인다. Buffer가 작아 Snapshot이 부족하면 Extrapolation하거나 마지막 State에서 멈춰야 한다.

보간 비율은 다음처럼 계산한다.

```text
A.time=10.05, A.x=5
B.time=10.11, B.x=8
renderTime=10.06
alpha=(10.06-10.05)/(10.11-10.05)=1/6
renderX=5+(8-5)×1/6=5.5
```

Interpolation은 이미 받은 과거 두 State 사이를 그리므로 안정적이지만 의도적으로 지연을 추가한다. Extrapolation은 마지막 속도로 미래를 추정하므로 지연은 작지만 방향 전환이나 충돌에서 크게 틀릴 수 있다.

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

Rollback에 필요한 자료는 세 종류다.

- `state_history[frame]`: 되돌아갈 수 있도록 저장한 과거 State
- `local_inputs[frame]`: 이미 알고 있는 내 Input
- `remote_inputs[frame]`: 도착한 실제 Input 또는 아직 안 왔을 때의 예측값

60 FPS에서 최대 8 Frame을 Rollback한다면 최소 8 Frame보다 넉넉한 History가 필요하다. World 전체 복사가 너무 크면 Rollback 대상 State를 작게 만들거나 Snapshot을 압축한다. Replay는 화면을 다시 8번 그리는 것이 아니라 Simulation만 빠르게 8번 실행한 뒤 최종 결과 한 장을 표시한다.

## Server Rewind와 Lag Compensation

Shooter에서 Client 화면상 명중했지만 Server 현재 시점의 Target은 이미 이동했을 수 있다. Server는 Player의 관측 시간으로 Hitbox History를 되감아 Ray를 판정한다.

```text
shot_time = server_receive_time - estimated_one_way_latency
rewound_hitboxes = history.sample(shot_time)
hit = raycast(origin, direction, rewound_hitboxes)
```

공격자에게 공정하지만 피해자는 벽 뒤에서 맞았다고 느낄 수 있다. Rewind 최대 시간, Clock 추정, Teleport와 Spawn 경계를 제한해야 한다. Client가 보낸 시간만 신뢰하면 과거를 조작할 수 있으므로 Server가 관측한 RTT 범위에서 Clamp한다.

Rollback과 Server Rewind는 이름은 비슷하지만 목적이 다르다. Rollback Netcode는 여러 참가자의 Simulation을 과거부터 다시 계산한다. Server Rewind는 보통 공격 판정 순간에만 과거 Hitbox를 조회하고 현재 World 전체를 다시 진행하지 않는다.

## 장르별 선택

| 장르 | 일반적인 중심 모델 | 이유 |
|---|---|---|
| RTS | Deterministic Lockstep | 많은 Unit State 대신 Input 전송 |
| 격투 | Rollback | Frame 단위 입력 반응과 1:1 결정성 |
| FPS | Snapshot + Prediction + Rewind | Server 권위와 즉각적인 이동·사격 |
| Racing | Prediction + Snapshot | 연속 이동과 충돌 교정 |
| MMO | Authoritative Snapshot + Interest | 큰 World와 Cheat 방어 |

실제 게임은 하나만 고르지 않는다. Local Player는 Prediction, Remote Player는 Interpolation, Projectile은 Server Authority, Cosmetic Effect는 Client-only로 처리할 수 있다.

## 처음 설계할 때의 선택 순서

1. 먼저 승패에 영향을 주는 State와 Cosmetic State를 나눈다.
2. 승패 State의 최종 Authority를 정한다. 경쟁 게임이라면 보통 Server다.
3. 객체마다 늦은 데이터의 가치가 남아 있는지 판단한다.
4. Local 조작에는 Prediction이 필요한지 결정한다.
5. Remote 객체에는 Interpolation Buffer를 정한다.
6. 사격 판정에는 Rewind가 필요한지, 격투 Simulation에는 Rollback이 필요한지 구분한다.
7. 목표 RTT, Jitter와 Loss 조건을 Network Emulator로 재현한다.
8. 교정 거리, Rollback Frame 수와 Input-to-photon Latency를 측정한다.

처음부터 “FPS이므로 이 방식”이라고 고정하기보다 Player가 어떤 Artifact를 더 불공정하게 느끼는지 정해야 한다. 입력이 늦는 것, Character가 순간 이동하는 것, 벽 뒤에서 맞는 것은 서로 다른 비용이다.

## 기억할 점

좋은 Netcode는 Network를 감추는 Code가 아니라 불확실성을 어디에서 수용할지 명시하는 설계다. State 권위, 예측 가능성, 교정 방식과 사용자에게 보이는 Artifact를 함께 결정해야 한다.

# Reference

- [GGPO Rollback SDK](https://github.com/pond3r/ggpo)
- [Unreal Engine Networking and Multiplayer](https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-and-multiplayer-in-unreal-engine)
- [[Client Prediction Snapshot Interpolation과 Rollback 구현]]
- [[UDP Reliability Tick과 Interest Management]]
