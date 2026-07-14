---
id: VSync Frame Pacing과 VRR
started: 2026-06-17
tags:
  - ✅DONE
  - Game-Development
  - Rendering
  - VSync
  - VRR
group: "[[게임 개발]]"
---

# VSync, Frame Pacing과 Variable Refresh Rate

GPU가 Frame을 완성하는 속도와 Display가 화면을 Scan-out하는 속도는 독립적이다. 두 Clock을 어떻게 맞추는지에 따라 Tearing, Stutter와 입력 지연이 달라진다.

## 화면이 표시되기까지

CPU는 Draw Command를 만들고 GPU는 그 Command로 Back Buffer에 Image를 그린다. **Swapchain**은 화면에 표시할 Buffer 여러 개를 관리하며, **Present**는 완성된 Buffer를 표시 Queue에 넘기는 요청이다. Monitor는 한순간에 전체 화면을 바꾸는 것이 아니라 보통 위에서 아래로 Scan-out한다.

```text
Input -> CPU Simulation -> Render Command -> GPU Rendering
      -> Present Queue -> Display Scan-out -> Pixel Response
```

각 화살표에서 기다림이 생길 수 있다. 그래서 GPU Render Time만으로 전체 입력 지연을 설명할 수 없다.

## Tearing이 발생하는 이유

Display가 위에서 아래로 Framebuffer를 읽는 도중 GPU가 새 Back Buffer를 Present하면 화면 위쪽은 이전 Frame, 아래쪽은 새 Frame이 될 수 있다. 이 경계가 Tearing이다.

Double Buffering은 Front Buffer를 Display가 읽는 동안 Back Buffer에 Rendering한다. 문제는 언제 두 Buffer를 교체할지다.

## VSync

VSync는 Vertical Blank 시점까지 Present를 기다려 Scan-out 중 교체를 막는다. Tearing은 사라지지만 GPU가 Refresh Deadline을 놓치면 다음 주기까지 기다릴 수 있다.

60 Hz Display의 한 주기는 약 16.67 ms다. Rendering이 17 ms 걸리면 전통적인 Double-buffer VSync에서는 표시가 33.3 ms 간격으로 떨어질 수 있다. 실제 동작은 Swapchain Mode와 Buffer 수에 따라 달라진다.

Refresh 주기는 `1000 / Hz`로 계산한다.

| Refresh Rate | 한 주기 |
|---:|---:|
| 60 Hz | 16.67 ms |
| 120 Hz | 8.33 ms |
| 144 Hz | 6.94 ms |
| 240 Hz | 4.17 ms |

144 Hz에서 7.2 ms가 걸리면 Deadline을 약 0.26 ms 놓친 것이다. Fixed Refresh FIFO에서는 다음 VBlank까지 기다릴 수 있지만 VRR 범위 안에서는 Display가 7.2 ms에 맞춰 Refresh할 수 있다.

## Triple Buffering과 Queue

Back Buffer를 하나 더 두면 GPU가 Display 대기 중에도 다음 Frame을 그릴 수 있어 Throughput과 Frame Pacing이 개선될 수 있다. 하지만 Queue가 깊어지면 오래된 입력을 담은 Frame이 줄을 서 입력 지연이 증가한다.

```text
latency = input sample
        + CPU simulation
        + render queue
        + GPU render
        + present wait
        + scan-out
        + display response
```

최대 사전 Render Frame 수와 Low-latency Mode는 Queue 깊이를 제한한다. CPU와 GPU 중 어느 쪽이 병목인지에 따라 효과가 다르다.

Frame Context가 3개라는 사실과 항상 3 Frame이 Queue에 쌓인다는 사실은 다르다. Context는 Resource 재사용을 안전하게 하는 수단이고, 실제 Queue Depth는 CPU가 GPU보다 얼마나 앞서 Submit했는지로 결정된다. Fence나 Waitable Object로 앞선 Frame 수를 제한한다.

## Frame Pacing

평균 60 FPS라도 Frame Time이 `8, 25, 8, 25 ms`로 반복되면 끊겨 보인다. Frame Pacing은 Frame이 일정한 간격으로 표시되도록 제출과 Present 시간을 조절한다.

```text
평균 FPS만 측정 X
Frame Time Histogram, 1% Low, Present-to-present 간격 측정 O
```

Sleep은 OS Scheduler Granularity 때문에 정확하지 않을 수 있다. Sleep 후 짧은 Spin, 고정밀 Timer와 Present API의 대기 Object를 조합하되 CPU 소비와 전력 사용을 고려한다.

```cpp
class FramePacer {
public:
    void beginFrame() {
        // DXGI waitable swapchain이 표시 Queue에 여유가 생길 때까지 기다린다.
        waitForSingleObject(frameLatencyWaitableObject_, kWaitTimeoutMs);
        frameStart_ = clock_.now();
    }

    void endFrame(Seconds targetFrameTime) {
        const auto target = frameStart_ + targetFrameTime;
        const auto coarseWakeup = target - kSpinThreshold;
        clock_.sleepUntil(coarseWakeup);

        while (clock_.now() < target) {
            cpuRelax();
        }
    }

private:
    static constexpr Milliseconds kSpinThreshold{0.2};
    static constexpr std::uint32_t kWaitTimeoutMs = 1'000;
    NativeHandle frameLatencyWaitableObject_;
    TimePoint frameStart_;
    MonotonicClock& clock_;
};
```

실제 구현은 Timeout, Window 비활성화, Resize와 Device Lost를 처리해야 한다. Battery 환경에서는 Spin 시간을 줄이고 OS Timer 중심으로 전력 정책을 달리할 수 있다.

## VRR

G-SYNC, FreeSync 같은 Variable Refresh Rate는 Display가 고정 주기를 강제하지 않고 GPU Frame 완료 시점에 맞춰 Refresh한다. 지원 범위 안에서는 Tearing과 VSync Deadline Stutter를 함께 줄일 수 있다.

Frame Rate가 VRR 범위를 넘으면 다시 Tearing이나 VSync 대기가 발생할 수 있어 최대 Refresh보다 약간 낮은 FPS Limit을 두는 구성이 사용된다. 범위 아래에서는 Low Framerate Compensation이 같은 Frame을 여러 번 표시할 수 있다.

예를 들어 VRR 범위가 48~144 Hz이면 Frame Time 6.94~20.83 ms 사이에서 Display가 Frame 완료에 맞출 수 있다. 30 FPS의 33.3 ms는 범위 아래이므로 LFC가 같은 Frame을 두 번 표시해 60 Hz 신호처럼 동작할 수 있다. LFC가 새 Simulation Frame을 만드는 것은 아니다.

## Present Mode

개념적으로 다음 정책을 구분할 수 있다.

| Mode | 동작 | 특성 |
|---|---|---|
| Immediate | 완성 즉시 교체 | 낮은 대기, Tearing 가능 |
| FIFO | VBlank 순서대로 표시 | Tearing 방지, Queue 가능 |
| Mailbox | 최신 완성 Frame만 유지 | 낮은 대기와 무 Tearing, Buffer 필요 |
| Adaptive | Refresh보다 빠를 때만 Sync | 느릴 때 Tearing 허용 |

API와 Platform마다 이름과 지원 조건이 다르다. Windows의 DXGI Flip Model은 Content를 복사하는 대신 Buffer Handle을 공유하는 방식으로 Presentation 효율을 개선한다.

Windows DXGI의 생성부는 설정을 한곳에서 결정하고 결과를 검증한다.

```cpp
DXGI_SWAP_CHAIN_DESC1 makeSwapchainDesc(const WindowExtent extent, const PresentationConfig& config) {
    return DXGI_SWAP_CHAIN_DESC1{
        .Width = extent.width,
        .Height = extent.height,
        .Format = DXGI_FORMAT_R10G10B10A2_UNORM,
        .Stereo = FALSE,
        .SampleDesc = {.Count = 1, .Quality = 0},
        .BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT,
        .BufferCount = 3,
        .Scaling = DXGI_SCALING_STRETCH,
        .SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD,
        .AlphaMode = DXGI_ALPHA_MODE_IGNORE,
        .Flags = config.allowTearing
            ? DXGI_SWAP_CHAIN_FLAG_ALLOW_TEARING | DXGI_SWAP_CHAIN_FLAG_FRAME_LATENCY_WAITABLE_OBJECT
            : DXGI_SWAP_CHAIN_FLAG_FRAME_LATENCY_WAITABLE_OBJECT,
    };
}

HRESULT present(IDXGISwapChain4& swapchain, const PresentationConfig& config) {
    const UINT syncInterval = config.vsync ? 1U : 0U;
    const UINT flags = !config.vsync && config.allowTearing ? DXGI_PRESENT_ALLOW_TEARING : 0U;
    return swapchain.Present(syncInterval, flags);
}
```

Tearing 지원은 OS와 Adapter Capability를 조회한 뒤 활성화한다. Exclusive Fullscreen, Borderless와 Windowed Mode에 따라 지원 조건이 다를 수 있고 `Present` 실패는 Device Removed·Occlusion 등을 구분해 처리한다.

## Frame Generation과 표시 FPS

DLSS나 FSR의 Frame Generation은 실제 Simulation Frame 사이에 보간 Frame을 넣는다. 표시가 부드러워질 수 있지만 Game State와 입력을 새로 계산한 Frame은 아니다. Base Frame Rate가 너무 낮으면 입력 지연과 Artifact를 감추기 어렵다.

따라서 Generated FPS만 보고 성능을 평가하지 않는다. Base Rendering FPS, Input Latency, Frame Pacing과 UI 합성 품질을 함께 측정한다.

## 실무 측정 항목

- CPU Frame 시작부터 Submit까지의 시간
- GPU Queue 시작·종료 Timestamp
- Present 호출과 실제 Display 시점의 간격
- Queue Depth와 기다린 Fence 시간
- Input Event Timestamp부터 해당 결과가 포함된 Present까지의 시간
- P50/P95/P99 Frame Time과 1% Low

한 평균값으로 합치지 말고 VSync/VRR/FPS Limit 조합별로 같은 입력 Script와 Camera Path를 재생해 비교한다.

## 기억할 점

VSync는 단순한 On/Off 품질 옵션이 아니라 Rendering Queue와 Display Clock을 조정하는 정책이다. 가장 좋은 설정은 Tearing, Frame Pacing, 지연과 전력 중 게임 장르가 우선하는 목표에 따라 달라진다.

# Reference

- [Microsoft DXGI Flip Model](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/dxgi-flip-model)
- [[Temporal Anti-Aliasing DLSS FSR과 Frame Generation]]
