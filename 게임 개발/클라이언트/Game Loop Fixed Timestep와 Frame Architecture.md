---
id: Game Loop Fixed Timestep와 Frame Architecture
started: 2026-06-02
tags:
  - ✅DONE
  - Game-Development
  - Game-Loop
  - Client
group: "[[게임 개발]]"
---

# Game Loop, Fixed Timestep와 Client Frame Architecture

게임은 입력을 받고 World를 갱신한 뒤 화면을 그리는 작업을 반복한다. 단순한 `while` 문처럼 보이지만 Simulation 시간과 Rendering 시간을 어떻게 분리하는지가 물리 안정성, Network 동기화와 입력 지연을 결정한다.

## Variable Timestep의 문제

```python
previous = now()
while running:
    current = now()
    delta = current - previous
    previous = current
    update(delta)
    render()
```

Frame마다 `delta`가 달라지면 적분 오차와 Collision 결과가 Hardware 부하에 따라 달라진다. 큰 Hitch 뒤에는 물체가 벽을 통과하거나 Spring이 폭발할 수 있다. Multiplayer에서 같은 입력을 재생해도 다른 결과가 나와 Lockstep과 Rollback을 어렵게 한다.

## Fixed Timestep

Simulation은 일정한 간격으로 실행하고 Rendering은 가능한 속도로 수행한다.

```python
fixed_dt = 1.0 / 60.0
accumulator = 0.0
previous = now()

while running:
    current = now()
    frame_time = min(current - previous, 0.25)
    previous = current
    accumulator += frame_time

    poll_input()
    while accumulator >= fixed_dt:
        previous_state = current_state
        simulate(current_state, fixed_dt)
        accumulator -= fixed_dt

    alpha = accumulator / fixed_dt
    render(interpolate(previous_state, current_state, alpha))
```

Accumulator는 아직 Simulation하지 않은 실제 시간을 보관한다. Rendering은 두 Simulation State 사이를 `alpha`로 보간해 60 Hz Simulation보다 높은 주사율에서도 부드럽게 보인다.

한 Frame에서 Update가 너무 오래 걸리면 밀린 Update가 더 많은 시간을 소비하는 **Spiral of Death**가 발생한다. Frame Time 상한, 한 Frame당 최대 Simulation Step과 품질 저하 정책이 필요하다.

## Client Frame의 일반적인 순서

```text
OS Event와 Input Sample
-> Network Packet 수신
-> Fixed Simulation Tick
-> Animation·Physics
-> Transform 확정
-> Render Graph 작성
-> GPU Command 제출
-> Present
```

입력을 Frame 초기에 한 번만 읽으면 GPU Queue가 긴 환경에서 지연이 커질 수 있다. Camera와 조준처럼 Simulation을 바꾸지 않는 값은 Rendering 직전에 다시 Sample하는 Late Update가 효과적이다. 반면 Gameplay Input은 Tick 번호와 함께 기록해야 Prediction과 Replay가 가능하다.

## Render Thread와 GPU는 비동기다

CPU가 Frame N+1을 준비하는 동안 GPU는 Frame N을 그릴 수 있다. Throughput은 좋아지지만 Queue에 Frame이 여러 개 쌓이면 화면에 보이는 입력이 오래된 것이 된다.

```text
CPU Simulation N+2
CPU Render Submit N+1
GPU Rendering N
Display N-1
```

저지연 모드는 CPU가 GPU보다 너무 앞서가지 않도록 Queue 깊이를 제한한다. 평균 FPS만 보지 말고 Input-to-photon Latency와 Frame Time 분포를 측정해야 한다.

## ECS와 Job System

Entity Component System은 Data를 Component별로 연속 배치하고 System이 같은 Component 집합을 Batch 처리하게 만든다.

```text
Transform[]
Velocity[]
Health[]
```

Object마다 Virtual Method를 호출하는 구조보다 Cache Locality와 SIMD 활용에 유리할 수 있다. Job System은 Animation, Visibility, Physics 준비 작업을 Dependency Graph로 나누어 여러 Core에 배치한다.

ECS가 모든 Gameplay Code를 자동으로 단순하게 만들지는 않는다. Entity 구조가 자주 바뀌는 Structural Change, Debugging과 순서 의존성이 비용이 된다. 많은 Entity에 같은 연산을 적용하는 Hot Path부터 도입하는 편이 안전하다.

## Asset Streaming

Open World는 모든 Texture와 Mesh를 한 번에 Memory에 올릴 수 없다. Camera 위치와 예상 이동 경로를 바탕으로 필요한 Asset을 비동기로 읽는다.

```text
Storage Read -> Decompress -> CPU Upload Buffer -> GPU Copy -> Resource Ready
```

Rendering Thread에서 File I/O나 Shader Compilation을 기다리면 Stutter가 생긴다. Streaming Budget, 우선순위, 취소, LOD와 임시 Placeholder가 필요하다. 평균 Frame Time이 좋아도 1% Low가 나쁘다면 Shader Compilation과 Asset Page Fault를 확인한다.

## 기억할 점

Game Loop는 “매 Frame 무엇을 실행할까”가 아니라 서로 다른 Clock을 조정하는 구조다. Simulation Tick, Network Tick, Render Frame과 Display Refresh가 각각 다른 속도로 움직인다는 사실에서 Client Architecture가 시작된다.

# Reference

- [[Netcode 모델 Lockstep Snapshot Prediction Rollback]]
- [[VSync Frame Pacing과 VRR]]
