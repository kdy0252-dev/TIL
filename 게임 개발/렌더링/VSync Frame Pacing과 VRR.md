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

## Tearing이 발생하는 이유

Display가 위에서 아래로 Framebuffer를 읽는 도중 GPU가 새 Back Buffer를 Present하면 화면 위쪽은 이전 Frame, 아래쪽은 새 Frame이 될 수 있다. 이 경계가 Tearing이다.

Double Buffering은 Front Buffer를 Display가 읽는 동안 Back Buffer에 Rendering한다. 문제는 언제 두 Buffer를 교체할지다.

## VSync

VSync는 Vertical Blank 시점까지 Present를 기다려 Scan-out 중 교체를 막는다. Tearing은 사라지지만 GPU가 Refresh Deadline을 놓치면 다음 주기까지 기다릴 수 있다.

60 Hz Display의 한 주기는 약 16.67 ms다. Rendering이 17 ms 걸리면 전통적인 Double-buffer VSync에서는 표시가 33.3 ms 간격으로 떨어질 수 있다. 실제 동작은 Swapchain Mode와 Buffer 수에 따라 달라진다.

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

## Frame Pacing

평균 60 FPS라도 Frame Time이 `8, 25, 8, 25 ms`로 반복되면 끊겨 보인다. Frame Pacing은 Frame이 일정한 간격으로 표시되도록 제출과 Present 시간을 조절한다.

```text
평균 FPS만 측정 X
Frame Time Histogram, 1% Low, Present-to-present 간격 측정 O
```

Sleep은 OS Scheduler Granularity 때문에 정확하지 않을 수 있다. Sleep 후 짧은 Spin, 고정밀 Timer와 Present API의 대기 Object를 조합하되 CPU 소비와 전력 사용을 고려한다.

## VRR

G-SYNC, FreeSync 같은 Variable Refresh Rate는 Display가 고정 주기를 강제하지 않고 GPU Frame 완료 시점에 맞춰 Refresh한다. 지원 범위 안에서는 Tearing과 VSync Deadline Stutter를 함께 줄일 수 있다.

Frame Rate가 VRR 범위를 넘으면 다시 Tearing이나 VSync 대기가 발생할 수 있어 최대 Refresh보다 약간 낮은 FPS Limit을 두는 구성이 사용된다. 범위 아래에서는 Low Framerate Compensation이 같은 Frame을 여러 번 표시할 수 있다.

## Present Mode

개념적으로 다음 정책을 구분할 수 있다.

| Mode | 동작 | 특성 |
|---|---|---|
| Immediate | 완성 즉시 교체 | 낮은 대기, Tearing 가능 |
| FIFO | VBlank 순서대로 표시 | Tearing 방지, Queue 가능 |
| Mailbox | 최신 완성 Frame만 유지 | 낮은 대기와 무 Tearing, Buffer 필요 |
| Adaptive | Refresh보다 빠를 때만 Sync | 느릴 때 Tearing 허용 |

API와 Platform마다 이름과 지원 조건이 다르다. Windows의 DXGI Flip Model은 Content를 복사하는 대신 Buffer Handle을 공유하는 방식으로 Presentation 효율을 개선한다.

## Frame Generation과 표시 FPS

DLSS나 FSR의 Frame Generation은 실제 Simulation Frame 사이에 보간 Frame을 넣는다. 표시가 부드러워질 수 있지만 Game State와 입력을 새로 계산한 Frame은 아니다. Base Frame Rate가 너무 낮으면 입력 지연과 Artifact를 감추기 어렵다.

따라서 Generated FPS만 보고 성능을 평가하지 않는다. Base Rendering FPS, Input Latency, Frame Pacing과 UI 합성 품질을 함께 측정한다.

## 기억할 점

VSync는 단순한 On/Off 품질 옵션이 아니라 Rendering Queue와 Display Clock을 조정하는 정책이다. 가장 좋은 설정은 Tearing, Frame Pacing, 지연과 전력 중 게임 장르가 우선하는 목표에 따라 달라진다.

# Reference

- [Microsoft DXGI Flip Model](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/dxgi-flip-model)
- [[Temporal Anti-Aliasing DLSS FSR과 Frame Generation]]
