---
id: Temporal Anti-Aliasing DLSS FSR과 Frame Generation
started: 2026-06-23
tags:
  - ✅DONE
  - Game-Development
  - Rendering
  - DLSS
  - Upscaling
group: "[[게임 개발]]"
---

# Temporal Anti-Aliasing, DLSS·FSR과 Frame Generation

Rasterization은 연속적인 삼각형을 Pixel Grid에 Sample한다. Sample이 부족하면 대각선의 Stair-step, 가는 Geometry의 Flicker와 Specular Shimmering이 생긴다. Anti-aliasing과 Upscaling은 여러 종류의 정보와 시간축을 사용해 부족한 Sample을 복원한다.

## Sampling과 Aliasing의 기초

현실의 선과 삼각형은 연속적이지만 화면은 유한한 Pixel Grid다. Pixel 중심 한 점만 검사하면 가는 선이 어떤 Frame에는 Sample되고 다음 Frame에는 빠질 수 있다. 원래 Signal의 변화보다 Sample 간격이 거칠 때 잘못된 무늬가 생기는 현상이 **Aliasing**이다.

| Artifact | 보이는 현상 | 주된 원인 |
|---|---|---|
| Stair-step | 대각선이 계단처럼 보임 | Geometry Coverage Sample 부족 |
| Shimmering | 이동 시 Texture가 반짝임 | Texture·Specular 축소 Sample 부족 |
| Flicker | 가는 물체가 나타났다 사라짐 | Subpixel Geometry의 불안정한 Coverage |
| Ghosting | 움직인 물체 뒤에 잔상 | 잘못된 Temporal History 재사용 |

Anti-aliasing은 단순 Blur가 아니라 Pixel이 덮는 영역의 평균에 가까운 값을 제한된 Sample로 추정하는 일이다.

## Spatial Anti-aliasing

### MSAA

Pixel 안의 Coverage를 여러 위치에서 Sample한다. Geometry Edge에는 효과적이지만 Shader와 Texture 내부의 Specular Aliasing을 모두 해결하지 못한다. Deferred Rendering에서는 G-buffer와 Memory 비용이 커질 수 있다.

4x MSAA는 Pixel마다 Coverage 위치 네 곳을 검사한다. Alpha-tested 잎, 투명 Particle과 Shader가 만든 반짝임은 Geometry Edge가 아니므로 별도 처리가 필요하다.

### FXAA와 SMAA

완성된 Image의 Edge를 찾아 후처리한다. 저렴하고 쉽게 적용할 수 있지만 실제 Subpixel 정보를 복원하지 못해 Text와 Texture가 흐려질 수 있다.

## TAA

Temporal Anti-Aliasing은 매 Frame Projection을 Subpixel 단위로 Jitter하고 이전 Frame History를 현재 Frame에 재투영한다.

```text
current color
+ reprojected history
+ motion vector
+ depth
-> history validation와 clamp
-> temporal resolve
```

Camera와 Object Motion Vector가 정확해야 한다. 이전 Frame에서 가려졌던 영역이 새로 보이는 Disocclusion, 투명 Particle, Animation과 밝은 Specular는 History가 잘못될 가능성이 크다.

Motion Vector는 “현재 Pixel의 물체가 이전 Frame 어디에 있었는가”를 나타낸다. Camera Motion은 Depth와 이전 View-Projection Matrix로 구할 수 있지만, Skinning·나뭇잎·Particle처럼 물체 자체가 변하면 이전 Vertex 위치도 필요하다.

History Weight가 크면 안정적이지만 Ghosting과 잔상이 생기고, 작으면 Flicker와 Noise가 남는다. Neighborhood Clamp, Reactive Mask와 Disocclusion Detection으로 History 사용량을 조절한다.

```hlsl
float4 ResolveTemporal(float4 position : SV_Position) : SV_Target
{
    uint2 pixel = uint2(position.xy);
    float2 uv = (float2(pixel) + 0.5) * Constants.inverseRenderSize;
    float2 historyUv = uv - MotionVectors.Load(int3(pixel, 0));
    float3 current = CurrentColor.Load(int3(pixel, 0)).rgb;

    bool outside = any(historyUv < 0.0) || any(historyUv > 1.0);
    float previousDepth = HistoryDepth.SampleLevel(LinearClamp, historyUv, 0);
    float currentDepth = CurrentDepth.Load(int3(pixel, 0));
    bool disoccluded = abs(previousDepth - currentDepth) > Constants.depthRejectThreshold;

    float3 history = HistoryColor.SampleLevel(LinearClamp, historyUv, 0).rgb;
    float3 clippedHistory = ClipHistoryToCurrentNeighborhood(history, pixel);
    float validHistory = Constants.historyValid && !outside && !disoccluded ? 1.0 : 0.0;
    float weight = Constants.historyWeight * validHistory;
    return float4(lerp(current, clippedHistory, weight), 1.0);
}
```

`ClipHistoryToCurrentNeighborhood`는 현재 Pixel 주변 3×3 Color의 최소·최대 또는 분산 범위로 과거 Color를 제한한다. Production Shader는 화면 경계 Load를 Clamp하고 HDR Color Space, Reactive Mask와 Exposure 차이도 처리한다.

## Temporal Upscaling

낮은 해상도로 Rendering하되 여러 Frame의 Jittered Sample, Motion Vector와 Depth를 이용해 높은 출력 해상도를 구성한다. 단순 Bilinear 확대와 달리 시간에 걸쳐 더 많은 Sample을 모은다.

Integration에 필요한 대표 입력은 다음과 같다.

- Low-resolution Color
- Motion Vector와 방향·Scale 규약
- Depth Buffer와 Reverse-Z 여부
- Exposure
- Jitter Offset
- Reactive·Transparency Mask
- Camera Cut 또는 History Reset Flag

Motion Vector가 빠지거나 좌표계가 틀리면 움직이는 물체에 Ghosting이 생긴다. Camera Cut 때 History를 버리지 않으면 이전 장면이 남는다.

Engine은 Resource 좌표계와 Lifetime을 한 계약으로 관리한다.

```cpp
struct TemporalUpscaleInputs {
    TextureView lowResolutionColor;
    TextureView depth;
    TextureView motionVectors;
    TextureView exposure;
    TextureView reactiveMask;
    Extent2D renderSize;
    Extent2D outputSize;
    Float2 jitterPixels;
    MotionVectorConvention motionConvention;
    bool resetHistory;
};

std::expected<UpscaleResult, UpscaleError> TemporalUpscaler::dispatch(
    RenderGraph& graph,
    const ViewState& view,
    const TemporalUpscaleInputs& inputs
) {
    return validateDimensions(inputs)
        .and_then(validateMotionVectorConvention)
        .and_then([&](const TemporalUpscaleInputs& valid) {
            const bool reset = valid.resetHistory ||
                               !history_.matches(valid.outputSize) ||
                               view.cameraCut ||
                               view.projectionChangedDiscontinuously;
            return backend_->schedule(graph, valid, history_, reset);
        })
        .transform([&](UpscaleResult result) {
            history_.rotateAfter(graph, result.output, inputs.depth);
            return result;
        });
}
```

Render Graph는 Low-resolution Color가 끝난 뒤 Upscale Pass를 실행하고, 결과가 준비된 뒤 Tone Mapping과 UI가 읽도록 Barrier를 만든다. History Texture는 다음 Frame까지 유지한다.

## DLSS

NVIDIA DLSS는 RTX Tensor Core를 사용하는 Neural Rendering 기술군이다. 현재 계열에는 Super Resolution, Frame Generation, Ray Reconstruction과 Native-resolution DLAA가 포함된다. Super Resolution은 낮은 해상도 Frame과 Motion·History Data를 이용해 고해상도 출력을 구성한다.

DLSS는 게임 안에서 모델을 Training하는 것이 아니다. NVIDIA가 사전 학습한 Network를 Runtime에서 추론한다. 품질은 모델뿐 아니라 Engine이 제공하는 Motion Vector, Exposure, Mask와 Render Pipeline Integration에 크게 좌우된다.

DLSS라는 이름을 하나의 기능으로 취급하지 않는다. Super Resolution은 고해상도 Frame을 재구성하고, DLAA는 Native 해상도에서 Anti-aliasing을 수행하며, Ray Reconstruction은 Ray-traced Signal 복원을 다루고, Frame Generation은 중간 표시 Frame을 만든다. 지원 조건은 기능마다 다르므로 Runtime Capability Query로 Option을 구성한다.

Ray Reconstruction은 Ray-traced Signal별 Hand-tuned Denoiser를 Neural Reconstruction으로 대체하는 영역이고, Super Resolution과 목적이 다르다.

## FSR과 XeSS

AMD FSR 계열도 Temporal Upscaling과 Frame Generation을 제공하며 최근 SDK는 ML 기반 Upscaling 기술을 포함한다. Intel XeSS 역시 Temporal 정보와 ML을 활용하는 Upscaler다. Hardware 지원, License, API와 품질 특성이 다르므로 동일 Scene의 Motion·Particle·UI를 비교해야 한다.

제품 Version별 지원 범위는 바뀔 수 있으므로 통합한 SDK Version과 Feature Query 결과를 Build Metadata에 남긴다. Vendor Backend가 실패하면 Native TAA 같은 안전한 경로로 Fallback하고, Pipeline 변경 시 History를 Reset한다.

Vendor별 기능을 한 Integration Layer로 추상화할 때 공통 입력의 Lifetime과 좌표 규약을 먼저 표준화한다. 가장 낮은 공통 기능만 노출하면 Ray Reconstruction 같은 고유 기능을 사용하기 어려울 수 있다.

## Frame Generation

Frame Generation은 두 Rendered Frame 사이의 중간 Frame을 Optical Flow와 Motion Data로 생성한다.

```text
rendered N -> generated N+0.5 -> rendered N+1
```

표시 FPS는 늘지만 중간 Frame에서 Game Simulation과 새 Input을 처리한 것은 아니다. Base FPS가 낮으면 생성 Frame도 오래된 입력을 바탕으로 하고 Artifact가 오래 보인다. 저지연 기술과 Frame Queue 관리가 함께 필요한 이유다.

UI는 World Motion과 다르게 움직이므로 Generated Frame에 포함하면 왜곡될 수 있다. UI를 별도 Render Target으로 분리해 Frame Generation 후 합성하는 방식이 사용된다.

처리 순서는 `Base Frame N Render -> Base Frame N+1 Render -> 두 Frame과 Motion/Optical Flow로 중간 Image 추정 -> UI 합성 -> Present`다. Generated Frame에는 새 Simulation 결과가 없으므로 Base 30 FPS를 60 표시 FPS로 만들어도 조작 Sampling은 30 FPS 기반이다. 먼저 Base Frame Time을 안정화해야 한다.

## Dynamic Resolution

GPU Frame Time이 Budget을 넘으면 Internal Resolution을 낮추고 여유가 생기면 높인다. 급격한 Scale 변화는 품질이 흔들리므로 이동 평균, Hysteresis와 변경 속도 제한을 둔다.

```text
target_gpu_ms = 16.0
if gpu_ms > target: scale -= small_step
if gpu_ms < target - margin: scale += small_step
```

Upscaler의 품질 Mode는 단순 이름이 아니라 Input-to-output Scale을 결정한다. Mode와 Dynamic Resolution의 허용 범위를 조합해 너무 낮은 Input Resolution으로 떨어지지 않게 한다.

```cpp
float DynamicResolutionController::update(const GpuFrameSample sample) {
    const float filteredMs = frameTimeEma_.push(sample.criticalPathMs);
    const float error = targetGpuMs_ - filteredMs;
    const float requested = currentScale_ + controller_.step(error, sample.deltaSeconds);

    currentScale_ = std::clamp(
        limitChangeRate(requested, currentScale_, maxScaleChangePerSecond_, sample.deltaSeconds),
        minimumScale_,
        maximumScale_);
    return quantizeToRenderExtent(currentScale_, outputExtent_);
}
```

순간 Spike 하나에 반응하지 않고 GPU Timestamp의 이동 통계와 Hysteresis를 사용한다. Render Size가 바뀌면 Jitter Scale, Motion Vector Scale, LOD Bias와 History 유효성도 함께 갱신한다.

## 품질 평가

정지 Screenshot만 비교하면 Temporal Artifact를 놓친다.

- Camera Pan과 빠른 회전
- 얇은 전선·울타리와 머리카락
- Particle, 반투명과 HUD
- Disocclusion과 빠른 Character
- 어두운 Ray-traced Reflection
- Frame Time Spike와 Dynamic Resolution 전환

Native, TAA, Upscaling Mode와 Frame Generation을 같은 Base 조건에서 Capture한다. 표시 FPS 외에 Base FPS와 Input Latency를 별도로 기록한다.

Capture에는 `render size`, `output size`, Jitter, History Reset 원인, Motion Vector 유효 Pixel 비율과 Disocclusion 비율도 Frame별로 남긴다. Artifact가 보인 Frame을 GPU Debugger에서 재현할 수 있어야 Integration 오류와 Algorithm 한계를 구분할 수 있다.

## 기억할 점

DLSS와 FSR은 “낮은 해상도를 선명하게 만드는 Filter”만이 아니다. 여러 Frame의 불완전한 Sample을 Motion과 History로 재구성하는 Temporal System이다. 품질은 Algorithm 이름보다 Engine이 제공하는 Data의 정확성과 History 관리에서 크게 결정된다.

# Reference

- [NVIDIA DLSS](https://developer.nvidia.com/rtx/dlss)
- [AMD FidelityFX Super Resolution](https://gpuopen.com/fidelityfx-super-resolution-3/)
- [[VSync Frame Pacing과 VRR]]
- [[Mipmap과 이방성 필터링]]
