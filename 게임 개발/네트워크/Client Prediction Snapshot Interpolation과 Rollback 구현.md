---
id: Client Prediction Snapshot Interpolation과 Rollback 구현
started: 2026-06-08
tags:
  - ✅DONE
  - Game-Development
  - Netcode
  - Prediction
  - Rollback
group: "[[게임 개발]]"
---

# Client Prediction, Snapshot Interpolation과 Rollback 구현

Netcode는 Diagram만 봐서는 체감하기 어렵다. 이 글은 1차원 World를 사용해 세 가지 핵심 Algorithm을 실제 Python Code로 실행한다. 단순한 환경이지만 Production 구현에 필요한 Sequence, History와 Replay 구조가 그대로 드러난다.

## Client Prediction과 Server Reconciliation

[client_prediction.py](../Resources/client_prediction.py)는 Client와 Server가 같은 이동 함수를 사용한다.

```python
DT = 1.0 / 20.0
SPEED = 4.0

position += input.axis * SPEED * DT
```

Client는 Input을 즉시 적용하고 Pending Queue와 Network Pipe에 넣는다.

```python
pending.append(command)
client_position += command.axis * SPEED * DT
input_pipe.append((tick + delay, command))
```

Server Snapshot이 도착하면 확인된 Sequence를 제거하고 아직 Server가 처리하지 않은 Input만 다시 적용한다.

```python
pending = [
    command
    for command in pending
    if command.sequence > acknowledged_sequence
]
client_position = authoritative_position
for command in pending:
    client_position += command.axis * SPEED * DT
```

```bash
python3 '게임 개발/Resources/client_prediction.py'
```

출력의 `error`는 Network 지연 동안 Client가 Server보다 앞서 있는 거리다. Reconciliation 후에도 Pending Input을 다시 적용하므로 Local 화면이 단순히 과거 Server 위치로 돌아가지 않는다.

Production에서는 Input을 여러 Packet에 중복해서 담아 Packet Loss를 견디고, Server는 Sequence 중복과 너무 오래된 Input을 거부한다. Physics가 완전히 같지 않다면 Position·Velocity·Grounded State 등을 Snapshot에 포함하고 허용 오차를 넘을 때만 교정할 수 있다.

## Snapshot Interpolation

[snapshot_interpolation.py](../Resources/snapshot_interpolation.py)는 Render Clock을 Local Clock보다 100 ms 늦춘다.

```python
render_time = local_time - interpolation_delay
position = sample(snapshots, render_time)
```

두 Snapshot `A`, `B` 사이의 비율은 다음과 같다.

```python
alpha = (render_time - A.time) / (B.time - A.time)
position = A.position + (B.position - A.position) * alpha
```

```bash
python3 '게임 개발/Resources/snapshot_interpolation.py'
```

Position은 Linear Interpolation, Rotation은 Quaternion Slerp가 일반적이다. Velocity가 있으면 Hermite Interpolation으로 움직임의 기울기를 보존할 수 있다. Teleport, Respawn과 문 통과처럼 연속적이지 않은 Event에는 보간하면 안 된다는 Flag가 필요하다.

Jitter가 커지면 고정 Buffer 대신 최근 Snapshot 도착 간격의 분산을 이용해 Delay를 조절할 수 있다. 너무 자주 바꾸면 Remote Player의 시간축 자체가 흔들리므로 천천히 보정한다.

## Rollback

[rollback_netcode.py](../Resources/rollback_netcode.py)는 Remote Input이 3 Frame 늦게 오는 상황을 재현한다. 미도착 Input은 마지막으로 알려진 값을 유지한다고 예측한다.

```python
predicted_remote[frame] = known_remote.get(frame, last_known)
state_history[frame + 1] = advance(
    state,
    local_input,
    predicted_remote[frame],
)
```

나중에 실제 Input이 다르면 해당 Frame의 State를 복원하고 현재까지 재실행한다.

```python
state = state_history[wrong_frame]
for frame in range(wrong_frame, current_frame):
    state = advance(state, local_inputs[frame], resolved_remote_input(frame))
```

```bash
python3 '게임 개발/Resources/rollback_netcode.py'
```

## Deterministic Simulation 조건

Rollback의 `advance(state, input)`는 같은 입력에 항상 같은 결과를 내야 한다.

- Random Number는 Seed와 호출 순서를 State에 포함한다.
- Floating-point 차이가 누적된다면 Fixed-point 또는 결정적 Math Library를 검토한다.
- Hash Map iteration 순서에 Simulation 결과를 의존하지 않는다.
- Physics Engine이 Target Platform 사이에서 결정적인지 확인한다.
- Frame 외부의 현재 시간, File I/O와 비동기 결과를 직접 읽지 않는다.

각 Frame State를 Hash해 Peer 간 비교하면 Desync가 시작된 Frame을 찾을 수 있다.

## Presentation Side Effect

Rollback 중 공격 Frame이 두 번 실행되면 Sound와 Particle도 두 번 재생될 수 있다. Simulation은 “공격 Event 발생”을 기록하고 Presentation Layer는 확정·예측 상태를 구분한다.

```text
simulation event id = player + frame + event type
```

같은 ID를 이미 재생했다면 중복 Effect를 막는다. 예측 Effect를 즉시 보여주되 틀렸을 때 자연스럽게 취소하거나 작은 불일치는 그대로 두는 정책도 필요하다.

## Network 조건을 추가하는 방법

실험을 확장할 때 Packet에 Delivery Tick을 넣고 다음 요소를 Random하게 적용한다.

- Base Latency
- Jitter
- Packet Loss
- Duplication
- Reordering

Test Seed를 고정하면 실패를 재현할 수 있다. 평균 50 ms만 시험하지 말고 99th Percentile Jitter, Burst Loss와 일시적인 500 ms Stall을 넣어 History 크기와 복구 결과를 확인한다.

## 기억할 점

Prediction은 미래를 추정하고, Interpolation은 안전한 과거를 그리며, Rollback은 틀린 미래를 과거부터 다시 계산한다. 세 Algorithm은 시간축을 다루는 방식이 다르므로 객체 유형별로 선택해야 한다.

# Reference

- [GGPO Rollback SDK](https://github.com/pond3r/ggpo)
- [[Netcode 모델 Lockstep Snapshot Prediction Rollback]]
