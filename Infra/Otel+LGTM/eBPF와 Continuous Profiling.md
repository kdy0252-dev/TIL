---
id: eBPF와 Continuous Profiling
started: 2026-06-19
tags:
  - ✅DONE
  - eBPF
  - Profiling
group:
  - "[[Infra Otel+LGTM]]"
---
# eBPF와 Continuous Profiling

## 1. 개요

Continuous Profiling은 운영 Process의 CPU·Allocation·Lock Profile을 지속적으로 Sampling해 시간에 따른 코드 비용을 저장합니다. eBPF는 Kernel의 검증된 Program을 이용해 Network, Syscall과 CPU Stack을 낮은 Overhead로 관찰합니다.

---

## 2. Metric·Trace와 차이

- Metric: 얼마나 자주·얼마나 큰 문제인가
- Trace: 어떤 요청 경로인가
- Profile: 어느 코드 Stack이 Resource를 소비하는가

세 Signal을 Service, Version과 시간으로 연결합니다.

---

## 3. On-CPU와 Off-CPU

On-CPU Profile은 실행 중인 Stack을, Off-CPU는 Lock·I/O·Scheduler 대기를 봅니다. CPU가 낮고 Latency가 높은 장애는 Off-CPU 분석이 중요합니다.

---

## 4. eBPF 장점과 한계

Application 수정 없이 Kernel·Native Frame을 볼 수 있지만 Kernel Version, 권한, Symbol과 Container Namespace 제약이 있습니다. 암호화된 Payload의 업무 의미까지 자동으로 알 수는 없습니다.

---

## 5. JVM Symbol

JIT Code와 Java Stack을 해석하려면 JVM Symbol 지원이 필요합니다. Frame Pointer, perf-map, Agent 조합에 따라 결과 품질이 달라집니다. JFR·async-profiler 결과와 교차 검증합니다.

---

## 6. Differential Profile

배포 전후 Flame Graph의 Sample 비율 차이를 비교하면 새 Hotspot을 찾을 수 있습니다. Traffic Mix와 Resource가 같은 조건인지 확인합니다.

---

## 7. Kubernetes 배치

Node Agent는 Host PID, BPF와 Kernel 접근이 필요할 수 있어 강한 권한을 가집니다. 전용 Node, 최소 Capability, 읽기 전용 Mount, 서명 Image와 Network 제한을 적용합니다.

---

## 8. 비용과 Cardinality

Profile Label에 Pod UID·Commit을 과도하게 넣으면 Storage가 증가합니다. Service, Environment, Version, Node 정도의 안정 Label을 사용하고 보존 기간과 Sampling Frequency를 조절합니다.

---

## 9. 사례 적용

k6 Run 구간의 Profile을 Image Digest별로 비교하고 Virtual Thread Pinning, JSON 직렬화, Query Mapping, GC·Native I/O 비용을 찾습니다. 항상 JFR·Trace·Metric과 함께 결론을 냅니다.

---

## 10. Continuous Profiling Backend

Profile은 시간, Service와 Version별로 저장해야 배포 전후를 비교할 수 있습니다. Pyroscope 같은 Backend는 Profile을 Label로 검색하고 Flame Graph와 Differential View를 제공합니다.

Raw Profile의 보존 기간, 집계 해상도와 Tenant 격리를 정합니다. Stack에 Package·Method와 Native Library 정보가 있으므로 운영 정보로 취급합니다.

---

## 11. 실패 양상

- Symbol이 없어 Stack이 Address로만 보임
- CPU Throttling을 Application Hotspot으로 오판
- Sampling Frequency가 높아 Agent Overhead 증가
- Node Agent 권한이 과도해 보안 경계 약화
- Pod UID Label로 Profile Cardinality 폭증
- Traffic Mix가 다른 배포를 직접 비교

Agent 자체 CPU, Lost Sample과 Symbolization 실패를 감시합니다.

---

## 12. 실습

1. k6 Baseline 동안 JFR과 CPU Profile을 함께 수집합니다.
2. 의도적으로 CPU 계산과 I/O 대기 Endpoint를 만듭니다.
3. On-CPU와 Off-CPU Flame Graph 차이를 확인합니다.
4. 새 Image에서 Differential Profile을 생성합니다.
5. Node Agent 중단이 업무 Pod에 영향을 주지 않는지 검증합니다.

---

## 13. 완료 기준

- [ ] On-CPU와 Off-CPU Profile을 구분합니다.
- [ ] Java·Native·Kernel Stack Symbol을 검증합니다.
- [ ] Version별 Differential Profile이 가능합니다.
- [ ] Agent 권한과 데이터 접근이 최소화되어 있습니다.
- [ ] Profile 비용·보존·Label Budget이 정의됩니다.

# Reference

- [eBPF Documentation](https://docs.ebpf.io/)
- [Grafana Pyroscope](https://grafana.com/docs/pyroscope/latest/)
- [[JFR와 async-profiler JVM 성능 진단]]
