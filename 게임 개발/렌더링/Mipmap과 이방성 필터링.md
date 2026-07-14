---
id: Mipmap과 이방성 필터링
started: 2026-06-20
tags:
  - ✅DONE
  - Game-Development
  - Rendering
  - Texture-Filtering
group: "[[게임 개발]]"
---

# Mipmap, Bilinear·Trilinear와 이방성 필터링

Texture Pixel인 Texel과 화면 Pixel은 일대일로 대응하지 않는다. Camera에서 멀거나 비스듬한 Surface에서는 한 Pixel이 넓고 찌그러진 Texture 영역을 덮는다. 어떤 Texel을 Sample할지 결정하는 과정이 Texture Filtering이다.

## Texture가 화면에 붙는 과정

Mesh의 Vertex에는 보통 `UV`라는 2차원 좌표가 있다. `U=0, V=0`은 Texture 한쪽 모서리, `U=1, V=1`은 반대쪽 모서리를 가리킨다. Rasterizer는 삼각형 내부 Pixel마다 UV를 보간하고 Pixel Shader가 그 좌표의 Texture를 읽는다.

| 용어 | 뜻 |
|---|---|
| Pixel | 최종 Render Target의 한 점 |
| Texel | Texture Image의 한 점 |
| Sample | UV에서 Texture 값을 읽는 작업 |
| Filter | 여러 Texel을 어떤 가중치로 합칠지 정하는 규칙 |
| LOD | 사용할 Mip Level |
| Footprint | 화면 Pixel 하나가 Texture에서 덮는 영역 |

Texture를 확대할 때는 Texel 하나가 여러 Pixel에 보이고, 축소할 때는 Pixel 하나가 여러 Texel을 대표한다. 축소 시 넓은 영역을 제대로 평균하지 않으면 Camera가 조금 움직일 때 선택되는 Texel이 급변해 반짝이는 Shimmering이 생긴다.

## Nearest와 Bilinear Filtering

Nearest는 가장 가까운 Texel 하나를 선택한다. 빠르고 Pixel Art에는 의도적일 수 있지만 확대 시 Block이 보이고 이동할 때 Shimmering이 생긴다.

Bilinear는 주변 2×2 Texel을 두 축으로 선형 보간한다.

```hlsl
float4 color = Texture.Sample(LinearSampler, uv);
```

확대 품질은 부드러워지지만 멀리 있는 Texture를 Full-resolution Level에서 Sample하면 많은 Texel이 한 Pixel로 축소되며 Aliasing이 발생한다.

GPU의 Hardware Sampler를 쓰는 것이 일반적이지만 동작 원리는 다음과 같다.

```hlsl
float4 SampleBilinear(Texture2D<float4> textureMap, int2 textureSize, float2 uv)
{
    float2 texelPosition = uv * textureSize - 0.5;
    int2 base = int2(floor(texelPosition));
    float2 fraction = frac(texelPosition);

    float4 c00 = textureMap.Load(int3(base, 0));
    float4 c10 = textureMap.Load(int3(base + int2(1, 0), 0));
    float4 c01 = textureMap.Load(int3(base + int2(0, 1), 0));
    float4 c11 = textureMap.Load(int3(base + int2(1, 1), 0));

    return lerp(lerp(c00, c10, fraction.x),
                lerp(c01, c11, fraction.x), fraction.y);
}
```

실무에서는 Address Mode의 Clamp/Wrap, Texture 경계와 Format 변환을 Hardware가 처리하도록 `Sample`을 사용한다. 위 코드는 네 Sample과 두 축 보간이라는 원리를 보여 주기 위한 것이다.

## Mipmap

원본 Texture를 절반씩 Downsample한 Pyramid를 미리 만든다.

```text
L0 1024×1024
L1  512×512
L2  256×256
...
```

GPU는 Screen Space의 UV 변화율을 이용해 Pixel Footprint와 적절한 LOD를 계산한다. 멀리 있는 물체는 작은 Mip Level을 사용해 Cache 효율과 축소 품질을 높인다.

Pixel Shader의 인접 Lane 사이 UV 변화는 `ddx(uv)`, `ddy(uv)`로 얻을 수 있다. 변화량을 Texel 단위로 바꾼 뒤 큰 축을 사용하면 대략적인 Mip Level을 구할 수 있다.

```hlsl
float ComputeIsotropicLod(float2 uv, float2 textureSize)
{
    float2 dx = ddx(uv) * textureSize;
    float2 dy = ddy(uv) * textureSize;
    float footprint = max(dot(dx, dx), dot(dy, dy));
    return max(0.0, 0.5 * log2(max(footprint, 1e-8)));
}
```

실제 Hardware LOD 계산은 API와 구현 세부에 따라 달라질 수 있으므로 직접 계산한 값은 Debug View나 명시적 `SampleLevel`이 필요한 Pass에 사용한다. 일반 Material은 Derivative를 아는 Pixel Shader에서 `Sample`에 맡기는 편이 안전하다.

Trilinear Filtering은 인접한 두 Mip Level에서 각각 Bilinear Sample한 뒤 Level 사이를 보간해 Mip 경계가 띠처럼 보이는 현상을 줄인다.

## 왜 비스듬한 바닥은 흐려지는가

정면 Surface의 Pixel Footprint는 Texture에서 대략 정사각형이지만 멀리 뻗은 바닥은 길고 좁은 사다리꼴에 가깝다. Isotropic Filtering은 가장 긴 축을 기준으로 정사각형 Mip을 선택하므로 짧은 축의 세부 정보까지 과도하게 흐린다.

**Anisotropic Filtering**은 방향에 따라 다른 Footprint를 고려해 긴 축을 따라 여러 Sample을 사용한다. 도로, 바닥과 벽을 비스듬히 볼 때 선명도가 크게 좋아진다.

```hlsl
SamplerState AnisotropicSampler
{
    Filter = ANISOTROPIC;
    MaxAnisotropy = 16;
    AddressU = Wrap;
    AddressV = Wrap;
};
```

2x, 4x, 8x, 16x는 대체로 최대 Anisotropy 수준을 뜻한다. 실제 Sample 수와 Algorithm은 Hardware·Driver에 따라 다르다. 비용은 비스듬한 Footprint, Texture Bandwidth와 Cache Hit에 영향을 받는다.

실무 Sampler는 Render API의 정적 설정으로 만들고 Material마다 중복 생성하지 않는다.

```cpp
SamplerDesc terrainSampler{
    .minFilter = Filter::Linear,
    .magFilter = Filter::Linear,
    .mipFilter = Filter::Linear,
    .addressU = AddressMode::Wrap,
    .addressV = AddressMode::Wrap,
    .addressW = AddressMode::Wrap,
    .mipLodBias = 0.0F,
    .maxAnisotropy = std::min(16U, deviceLimits.maxSamplerAnisotropy),
    .minLod = 0.0F,
    .maxLod = std::numeric_limits<float>::max(),
};

SamplerHandle sharedTerrainSampler = samplerCache.getOrCreate(terrainSampler);
```

Device Capability를 확인하지 않고 16x를 고정하지 않는다. Mobile이나 Texture Cache가 병목인 장면에서는 4x/8x가 더 나은 품질 대비 비용을 낼 수 있으므로 GPU Capture로 확인한다.

## LOD Bias

Negative LOD Bias는 더 높은 해상도 Mip을 선택해 정지 화면을 선명하게 보이게 하지만 움직일 때 Shimmering과 Temporal Aliasing을 키울 수 있다. Upscaling을 사용할 때 Render Resolution 변화와 Mip Bias를 함께 조정하지 않으면 Texture가 지나치게 흐리거나 불안정해진다.

## Normal Map과 Alpha Texture

Normal Map을 단순 평균하면 Vector 길이가 줄어 Lighting이 달라질 수 있어 재정규화와 전용 Filter를 고려한다. Alpha-tested 나뭇잎은 Mip 생성 과정에서 Coverage가 줄어 멀리서 사라질 수 있으므로 Alpha Coverage 보존이 필요하다.

색 Texture도 Gamma 공간에서 평균하면 어두워질 수 있다. sRGB Texture는 Linear 공간에서 Filtering되도록 Format과 Sampling 설정을 맞춘다.

Mip 생성 Pipeline도 Asset 종류를 알아야 한다.

```cpp
MipGenerationOptions optionsFor(TextureSemantic semantic) {
    switch (semantic) {
        case TextureSemantic::BaseColor:
            return MipGenerationOptions{
                .decodeSrgb = true, .filter = MipFilter::Kaiser, .encodeSrgb = true};
        case TextureSemantic::Normal:
            return MipGenerationOptions{
                .renormalizeVectors = true, .filter = MipFilter::Kaiser};
        case TextureSemantic::AlphaMask:
            return MipGenerationOptions{
                .preserveAlphaCoverage = true, .alphaCutoff = 0.5F};
        default:
            return MipGenerationOptions{};
    }
}
```

Base Color, Normal과 Alpha Mask를 같은 평균 Filter로 처리하지 않는 것이 핵심이다. 실제 Asset Build 단계에서는 Source Hash와 Option을 Cache Key에 포함해 설정이 바뀌면 Mip을 다시 생성한다.

## Texture Streaming과 Mip

Open World에서는 당장 필요한 Mip만 GPU Memory에 올린다. 화면에 보이는 크기, 거리와 이동 방향을 기반으로 고해상도 Mip을 요청한다. 늦게 도착하면 흐린 Texture가 잠시 보이는 Mip Pop이 생긴다.

Streaming Pool을 무조건 키우면 다른 Resource가 부족해진다. Mip Residency, Miss, Upload Bandwidth와 Frame Hitch를 함께 Profile한다.

요청 Mip은 현재 화면 크기만 보지 않고 Camera 속도와 I/O 지연을 반영해 미리 올린다. 요청에는 Priority와 Deadline을 붙이고, 한 Frame의 Upload Byte Budget을 넘으면 먼 Asset부터 다음 Frame으로 미룬다. Resource를 교체할 때는 GPU가 이전 Mip을 읽는 Fence가 끝나기 전에 Memory를 해제하면 안 된다.

## 기억할 점

이방성 필터링은 Texture 자체의 해상도를 높이는 기능이 아니다. 비스듬한 Surface의 비정방형 Pixel Footprint를 더 정확히 적분해, Mipmap이 과도하게 흐린 Level을 고르는 문제를 보완한다.

# Reference

- [OpenGL EXT_texture_filter_anisotropic](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_texture_filter_anisotropic.txt)
- [[Temporal Anti-Aliasing DLSS FSR과 Frame Generation]]
