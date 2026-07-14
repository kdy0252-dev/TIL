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

Python 예제는 Algorithm의 시간축을 눈으로 확인하기 위한 실험 도구다. 실제 Client에서는 위치 하나만 저장하지 않고 Tick, Input Sequence, Position, Velocity, Movement Mode와 Snapshot 수신 시각을 함께 관리한다. 아래 C++ 예시는 특정 Engine API에 묶이지 않으면서도 실제 구현에 옮길 수 있는 경계를 보여 준다.

## 구현 전에 정할 계약

Client와 Server가 같은 의미로 해석해야 하는 값부터 고정한다.

- Simulation은 60 Hz Fixed Tick으로 실행한다.
- `InputCommand::sequence`는 Client별로 단조 증가한다.
- `InputCommand::clientTick`은 입력이 적용될 Tick이다.
- Server Snapshot은 마지막으로 처리한 Input Sequence를 돌려준다.
- Network Position은 meter, Velocity는 meter/second를 사용한다.
- 모든 Packet 값은 역직렬화 직후 범위를 검사한다.

```cpp
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
#include <optional>

struct Vec3 {
    float x{};
    float y{};
    float z{};
};

struct InputCommand {
    std::uint32_t sequence{};
    std::uint32_t clientTick{};
    std::int16_t moveX{};   // [-32767, 32767]로 양자화한 입력
    std::int16_t moveY{};
    std::uint16_t buttons{};
};

struct PlayerState {
    Vec3 position{};
    Vec3 velocity{};
    std::uint8_t movementMode{}; // ground, air, ladder 등
};

struct AuthoritativeSnapshot {
    std::uint32_t serverTick{};
    std::uint32_t acknowledgedInput{};
    PlayerState player{};
};

constexpr float kFixedDt = 1.0F / 60.0F;
constexpr std::size_t kMaxPendingInputs = 256;
```

`float` Input을 그대로 보내지 않고 `int16_t`로 양자화하면 Platform 표현 차이와 Packet 크기를 줄일 수 있다. 수신 측은 `moveX / 32767.0F`로 복원하되 범위를 다시 Clamp한다.

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

### 실무형 Prediction과 Reconciliation

아래 구조는 Gameplay State와 화면용 보정값을 분리한다. `simulateMovement`는 Client와 Server가 공유하는 결정적 이동 함수라고 가정한다.

```cpp
class PredictedPlayer {
public:
    InputCommand sampleInput(const RawInput& raw, std::uint32_t tick) {
        InputCommand command{
            .sequence = nextSequence_++,
            .clientTick = tick,
            .moveX = quantizeAxis(raw.moveX),
            .moveY = quantizeAxis(raw.moveY),
            .buttons = encodeButtons(raw),
        };

        if (pending_.size() == kMaxPendingInputs) {
            // ACK가 지나치게 오래 오지 않은 연결이다. 무한히 Memory를 늘리지 않는다.
            pending_.pop_front();
            predictionHistoryLost_ = true;
        }

        pending_.push_back(command);
        state_ = simulateMovement(state_, command, kFixedDt);
        return command;
    }

    void reconcile(const AuthoritativeSnapshot& snapshot) {
        if (!isNewer(snapshot.serverTick, lastServerTick_)) {
            return; // Reordering으로 늦게 도착한 Snapshot 폐기
        }
        lastServerTick_ = snapshot.serverTick;

        std::erase_if(pending_, [&](const InputCommand& command) {
            return !isNewer(command.sequence, snapshot.acknowledgedInput);
        });

        const Vec3 before = state_.position;
        state_ = snapshot.player;

        if (!predictionHistoryLost_) {
            for (const InputCommand& command : pending_) {
                state_ = simulateMovement(state_, command, kFixedDt);
            }
        } else {
            // History 일부를 잃었다면 거짓 Replay보다 Server State를 기준으로 재시작한다.
            pending_.clear();
            predictionHistoryLost_ = false;
        }

        const Vec3 correction = subtract(before, state_.position);
        if (lengthSquared(correction) > kVisualCorrectionThresholdSquared) {
            visualOffset_ = add(visualOffset_, correction);
        }
    }

    Vec3 renderPosition(float frameDt) {
        visualOffset_ = damp(visualOffset_, Vec3{}, 18.0F, frameDt);
        return add(state_.position, visualOffset_);
    }

private:
    PlayerState state_{};
    std::deque<InputCommand> pending_{};
    Vec3 visualOffset_{};
    std::uint32_t nextSequence_{1};
    std::uint32_t lastServerTick_{};
    bool predictionHistoryLost_{};
};
```

중요한 점은 `state_`가 판정에 쓰는 Gameplay State이고 `visualOffset_`은 화면에만 쓰인다는 것이다. 보정 Animation이 Collision이나 다음 Input 계산에 들어가면 오차가 다시 Server로 전파된다.

Input Packet에는 최신 명령 하나만 보내지 않고 최근 몇 개를 중복할 수 있다.

```cpp
struct InputBatch {
    std::uint32_t newestSequence{};
    std::uint8_t count{};
    std::array<InputCommand, 6> commands{};
};

InputBatch buildInputBatch(const std::deque<InputCommand>& pending) {
    InputBatch batch{};
    batch.count = static_cast<std::uint8_t>(std::min<std::size_t>(6, pending.size()));
    const auto first = pending.end() - batch.count;
    std::copy(first, pending.end(), batch.commands.begin());
    batch.newestSequence = batch.count == 0 ? 0 : batch.commands[batch.count - 1].sequence;
    return batch;
}
```

하나가 유실돼도 다음 Packet의 중복 Input으로 복구할 수 있다. Server는 Sequence별로 한 번만 적용해야 하므로 중복 제거가 필수다.

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

### 실무형 Snapshot Buffer

Snapshot은 도착 순서가 아니라 `serverTime` 순서로 보관한다. 너무 오래된 Packet, 같은 Tick의 중복 Packet과 Teleport 경계를 처리해야 한다.

```cpp
struct RemoteSnapshot {
    std::uint32_t serverTick{};
    double serverTime{};
    Vec3 position{};
    Vec3 velocity{};
    bool discontinuity{}; // teleport, respawn, scene transfer
};

class SnapshotBuffer {
public:
    void push(RemoteSnapshot snapshot) {
        if (!std::isfinite(snapshot.serverTime) || snapshots_.size() > 128) {
            return;
        }

        const auto position = std::lower_bound(
            snapshots_.begin(), snapshots_.end(), snapshot.serverTime,
            [](const RemoteSnapshot& value, double time) {
                return value.serverTime < time;
            });

        if (position != snapshots_.end() && position->serverTick == snapshot.serverTick) {
            return;
        }
        snapshots_.insert(position, snapshot);
    }

    std::optional<Vec3> sample(double estimatedServerNow) {
        const double renderTime = estimatedServerNow - interpolationDelay_;
        while (snapshots_.size() >= 3 && snapshots_[1].serverTime <= renderTime) {
            snapshots_.pop_front();
        }
        if (snapshots_.size() < 2) {
            return std::nullopt;
        }

        const RemoteSnapshot& a = snapshots_[0];
        const RemoteSnapshot& b = snapshots_[1];
        if (b.discontinuity || b.serverTime <= a.serverTime) {
            return b.position;
        }

        const float alpha = std::clamp(static_cast<float>(
            (renderTime - a.serverTime) / (b.serverTime - a.serverTime)), 0.0F, 1.0F);
        return hermite(a.position, a.velocity, b.position, b.velocity,
                       alpha, static_cast<float>(b.serverTime - a.serverTime));
    }

private:
    std::deque<RemoteSnapshot> snapshots_{};
    double interpolationDelay_{0.100};
};
```

Buffer가 두 Snapshot을 확보하지 못했다고 무제한 Extrapolation하면 Character가 벽을 통과한다. 예를 들어 최대 100 ms까지만 속도로 추정하고, 그 이후에는 마지막 위치에서 멈추는 정책이 필요하다.

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

### 실무형 Rollback History

동적 할당을 매 Frame 수행하지 않도록 고정 크기 Ring Buffer를 사용한다. Buffer 크기는 `최대 Rollback Frame + 안전 여유`보다 커야 한다.

```cpp
template <typename T, std::size_t Capacity>
class FrameHistory {
public:
    void store(std::uint32_t frame, const T& value) {
        slots_[frame % Capacity] = Slot{frame, value, true};
    }

    const T* find(std::uint32_t frame) const {
        const Slot& slot = slots_[frame % Capacity];
        return slot.valid && slot.frame == frame ? &slot.value : nullptr;
    }

private:
    struct Slot {
        std::uint32_t frame{};
        T value{};
        bool valid{};
    };
    std::array<Slot, Capacity> slots_{};
};

constexpr std::size_t kHistoryFrames = 32;
FrameHistory<FightState, kHistoryFrames> stateHistory;
FrameHistory<PlayerInputs, kHistoryFrames> inputHistory;

bool rollbackAndReplay(std::uint32_t wrongFrame, std::uint32_t currentFrame) {
    const FightState* saved = stateHistory.find(wrongFrame);
    if (saved == nullptr || currentFrame - wrongFrame >= kHistoryFrames) {
        return false; // 복구 범위를 벗어남: Resync 요청 또는 Match 중단 정책
    }

    FightState replayed = *saved;
    for (std::uint32_t frame = wrongFrame; frame < currentFrame; ++frame) {
        const PlayerInputs* inputs = inputHistory.find(frame);
        if (inputs == nullptr) {
            return false;
        }
        stateHistory.store(frame, replayed);
        replayed = simulateFrame(replayed, *inputs);
    }

    currentState = replayed;
    return true;
}
```

실제 Remote Input이 도착하면 예측 Input과 Bit 단위로 비교한다. 달라진 가장 오래된 Frame 한 곳부터 한 번만 Replay해야 한다. Packet 하나마다 따로 Rollback하면 같은 구간을 반복 계산하게 된다.

## Deterministic Simulation 조건

Rollback의 `advance(state, input)`는 같은 입력에 항상 같은 결과를 내야 한다.

- Random Number는 Seed와 호출 순서를 State에 포함한다.
- Floating-point 차이가 누적된다면 Fixed-point 또는 결정적 Math Library를 검토한다.
- Hash Map iteration 순서에 Simulation 결과를 의존하지 않는다.
- Physics Engine이 Target Platform 사이에서 결정적인지 확인한다.
- Frame 외부의 현재 시간, File I/O와 비동기 결과를 직접 읽지 않는다.

각 Frame State를 Hash해 Peer 간 비교하면 Desync가 시작된 Frame을 찾을 수 있다.

Hash에는 Padding Byte나 Pointer 주소를 넣지 않는다. Serialization 순서를 고정한 Gameplay State만 Hash하고, Frame 번호와 Build Version을 함께 Log한다. Release Build에서도 최근 수백 Frame의 Input과 Hash를 작은 Ring Buffer에 유지하면 재현하기 어려운 Desync 조사에 도움이 된다.

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

## Production에서 확인할 Metric

- Prediction Error의 평균뿐 아니라 P95/P99와 최대값
- Snapshot Buffer가 비어서 Extrapolation한 시간
- 초당 Reconciliation 횟수와 Visual Correction 거리
- Rollback 횟수, 평균 Frame 수와 최대 Replay 비용
- Input Queue가 가득 찬 횟수
- State Hash 불일치가 처음 발생한 Frame

정상 LAN 환경만 통과하는 것은 충분하지 않다. 80 ms RTT, ±30 ms Jitter, 2% Random Loss, 5 Packet Burst Loss와 Reordering을 각각 독립적으로 재현하고 조합 조건도 시험한다.

## 기억할 점

Prediction은 미래를 추정하고, Interpolation은 안전한 과거를 그리며, Rollback은 틀린 미래를 과거부터 다시 계산한다. 세 Algorithm은 시간축을 다루는 방식이 다르므로 객체 유형별로 선택해야 한다.

# Reference

- [GGPO Rollback SDK](https://github.com/pond3r/ggpo)
- [[Netcode 모델 Lockstep Snapshot Prediction Rollback]]
