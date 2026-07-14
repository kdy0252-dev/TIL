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

## Frame과 Clock의 기초

**Frame**은 Display에 한 번 보여 줄 Image이고 **Tick**은 Gameplay State를 한 번 갱신하는 Simulation 단위다. 60 Hz Tick은 약 16.67 ms, 120 Hz는 약 8.33 ms마다 실행된다. Input Poll, Simulation, Network Send, Rendering과 Display Refresh는 모두 다른 속도로 움직일 수 있다.

| Clock | 예시 | 목적 |
|---|---|---|
| Input Poll | 250 Hz | Controller와 Mouse 상태 수집 |
| Simulation Tick | 60 Hz | Physics와 Gameplay를 일정 간격으로 계산 |
| Network Send | 20 Hz | Bandwidth에 맞춰 Snapshot 전송 |
| Render Frame | 90~240 FPS | 가능한 속도로 Image 생성 |
| Display Refresh | 144 Hz | Monitor가 화면을 Scan-out |

## Variable Timestep의 문제

```cpp
auto previous = clock.now();
while (!platform.shouldQuit()) {
    const auto current = clock.now();
    const Seconds frameDelta = current - previous;
    previous = current;

    input.pollPlatformEvents();
    world.update(frameDelta); // 부하에 따라 매번 다른 delta가 전달되는 문제
    renderer.render(world.buildRenderView());
}
```

Frame마다 `delta`가 달라지면 적분 오차와 Collision 결과가 Hardware 부하에 따라 달라진다. 큰 Hitch 뒤에는 물체가 벽을 통과하거나 Spring이 폭발할 수 있다. Multiplayer에서 같은 입력을 재생해도 다른 결과가 나와 Lockstep과 Rollback을 어렵게 한다.

## Fixed Timestep

Simulation은 일정한 간격으로 실행하고 Rendering은 가능한 속도로 수행한다.

```cpp
class GameLoop {
public:
    void run() {
        auto previousTime = clock_.now();
        Seconds accumulator{};

        while (!platform_.shouldQuit()) {
            const auto frameStart = clock_.now();
            const Seconds elapsed = std::min(frameStart - previousTime, kMaxFrameGap);
            previousTime = frameStart;
            accumulator += elapsed;

            platform_.pollEvents();
            network_.drainReceivedPackets(commandQueue_);

            std::uint32_t steps{};
            while (accumulator >= kFixedStep && steps < kMaxStepsPerFrame) {
                previousState_ = currentState_;
                const Tick tick = ++simulationTick_;
                const InputCommand input = input_.sampleForTick(tick);
                commandQueue_.consumeUpTo(tick, currentState_);
                currentState_ = simulation_.advance(currentState_, input, kFixedStep);
                prediction_.record(tick, input, currentState_);
                accumulator -= kFixedStep;
                ++steps;
            }

            if (steps == kMaxStepsPerFrame && accumulator >= kFixedStep) {
                metrics_.increment("client.simulation.step_budget_exhausted");
                accumulator = std::min(accumulator, kFixedStep);
            }

            const float alpha = static_cast<float>(accumulator / kFixedStep);
            const RenderView view = presentation_.interpolate(previousState_, currentState_, alpha);
            renderer_.submit(view, input_.sampleLateViewInput());
            framePacer_.waitUntilNextPresentation(frameStart);
        }
    }

private:
    static constexpr Seconds kFixedStep{1.0 / 60.0};
    static constexpr Seconds kMaxFrameGap{0.250};
    static constexpr std::uint32_t kMaxStepsPerFrame{5};
};
```

Accumulator는 아직 Simulation하지 않은 실제 시간을 보관한다. Rendering은 두 Simulation State 사이를 `alpha`로 보간해 60 Hz Simulation보다 높은 주사율에서도 부드럽게 보인다.

Fixed Step이 16.67 ms이고 Accumulator에 6 ms가 남았다면 `alpha = 6 / 16.67 ≈ 0.36`이다. Render 위치만 이전 State에서 현재 State까지 36% 지점을 사용한다. 충돌과 다음 Tick은 보간된 위치가 아니라 확정된 Simulation State를 사용한다.

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

Network Thread는 Packet을 검증해 Queue에 넣을 뿐 World를 직접 수정하지 않는다. Simulation Thread가 Tick 경계에서 Command를 소비하고, Render Thread는 불변 Render Snapshot만 읽는다. 이 소유권을 지키면 Frame 도중 위치가 바뀌는 Race Condition을 피할 수 있다.

## Render Thread와 GPU는 비동기다

CPU가 Frame N+1을 준비하는 동안 GPU는 Frame N을 그릴 수 있다. Throughput은 좋아지지만 Queue에 Frame이 여러 개 쌓이면 화면에 보이는 입력이 오래된 것이 된다.

```text
CPU Simulation N+2
CPU Render Submit N+1
GPU Rendering N
Display N-1
```

저지연 모드는 CPU가 GPU보다 너무 앞서가지 않도록 Queue 깊이를 제한한다. 평균 FPS만 보지 말고 Input-to-photon Latency와 Frame Time 분포를 측정해야 한다.

```cpp
struct FrameContext {
    CommandAllocator commandAllocator;
    UploadArena uploadArena;
    FenceValue completionFence{};
};

FrameContext& Renderer::beginFrame() {
    FrameContext& frame = frames_[frameNumber_ % frames_.size()];
    gpuQueue_.wait(frame.completionFence);
    frame.commandAllocator.reset();
    frame.uploadArena.reset();
    return frame;
}

void Renderer::endFrame(FrameContext& frame, const RenderGraph& graph) {
    const auto commandLists = graph.recordParallel(frame.commandAllocator, jobs_);
    gpuQueue_.submit(commandLists);
    frame.completionFence = gpuQueue_.signal();
    swapchain_.present(presentationPolicy_);
    ++frameNumber_;
}
```

`waitIdle()`을 매 Frame 호출하면 CPU와 GPU 병렬성이 사라진다. 재사용할 Frame Context의 Fence만 기다리고 Resource별 Lifetime과 Barrier는 Render Graph가 관리하게 한다.

## ECS와 Job System

Entity Component System은 Data를 Component별로 연속 배치하고 System이 같은 Component 집합을 Batch 처리하게 만든다.

```text
Transform[]
Velocity[]
Health[]
```

Object마다 Virtual Method를 호출하는 구조보다 Cache Locality와 SIMD 활용에 유리할 수 있다. Job System은 Animation, Visibility, Physics 준비 작업을 Dependency Graph로 나누어 여러 Core에 배치한다.

ECS가 모든 Gameplay Code를 자동으로 단순하게 만들지는 않는다. Entity 구조가 자주 바뀌는 Structural Change, Debugging과 순서 의존성이 비용이 된다. 많은 Entity에 같은 연산을 적용하는 Hot Path부터 도입하는 편이 안전하다.

Job은 단순 Lambda 목록이 아니라 읽기·쓰기 Resource Dependency를 가진다. Animation이 `LocalPose`를 쓴 뒤 Physics가 읽고, Physics가 `PhysicsState`를 쓴 뒤 Transform 전파가 읽는 순서를 Scheduler가 Graph로 보장해야 한다. 같은 Component에 동시에 쓰는 Job은 병렬 실행하면 안 된다.

## Asset Streaming

Open World는 모든 Texture와 Mesh를 한 번에 Memory에 올릴 수 없다. Camera 위치와 예상 이동 경로를 바탕으로 필요한 Asset을 비동기로 읽는다.

```text
Storage Read -> Decompress -> CPU Upload Buffer -> GPU Copy -> Resource Ready
```

Rendering Thread에서 File I/O나 Shader Compilation을 기다리면 Stutter가 생긴다. Streaming Budget, 우선순위, 취소, LOD와 임시 Placeholder가 필요하다. 평균 Frame Time이 좋아도 1% Low가 나쁘다면 Shader Compilation과 Asset Page Fault를 확인한다.

```cpp
AssetFuture<TextureHandle> TextureStreamer::request(TextureRequest request) {
    return residency_.find(request.assetId)
        .transform([](ResidentTexture& texture) { return makeReadyFuture(texture.handle()); })
        .or_else([&] {
            return io_.readAsync(request.path, request.priority)
                .then(decompressionPool_, decompressTexture)
                .then(renderUploadQueue_, [this, request](DecodedTexture decoded) {
                    return uploadMipRange(request.assetId, request.requiredMips, std::move(decoded));
                })
                .withCancellation(request.cancellation)
                .withFallback(fallbackTexture_);
        });
}
```

API 이름은 Engine마다 다르지만 Storage Read, Decompression과 GPU Upload를 다른 Queue에서 실행하고, Upload Fence 완료 후에만 Resource를 공개하는 원칙은 같다.

## 기억할 점

Game Loop는 “매 Frame 무엇을 실행할까”가 아니라 서로 다른 Clock을 조정하는 구조다. Simulation Tick, Network Tick, Render Frame과 Display Refresh가 각각 다른 속도로 움직인다는 사실에서 Client Architecture가 시작된다.

# Reference

- [[Netcode 모델 Lockstep Snapshot Prediction Rollback]]
- [[VSync Frame Pacing과 VRR]]
