# Backend Engineering Notes

백엔드 개발과 소프트웨어 운영 과정에서 학습한 내용을 기술 블로그 형식으로 정리한 저장소입니다. 단순한 사용법보다 기술이 필요한 이유, 내부 동작, 설계 선택지, 실패 지점과 운영 시 주의사항을 함께 기록합니다.

문서는 Obsidian으로 관리하며 GitHub에서도 읽을 수 있도록 Markdown과 주제별 디렉터리를 사용합니다.

## 다루는 주제

| 분류 | 주요 내용 |
|---|---|
| [AI](./AI) | LLM 원리와 GPU 구현, Coding Agent, Context Engineering, RAG와 AI Framework |
| [Java](./Java) | 언어 메커니즘, 함수형 프로그래밍, JVM 성능 분석, Library |
| [Spring](./Java%20Spring) | Architecture, 데이터 접근, 비동기 처리, 인증, 관측성, Test |
| [Database](./DBMS) | PostgreSQL, Index, Lock, WAL, Query 최적화, Connection Pool |
| [Infrastructure](./Infra) | AWS, Kubernetes, GitOps, CI/CD, 관측성, 보안, 운영 자동화 |
| [Game Development](./게임%20개발) | Netcode, Game Server, Client Architecture, Rendering과 GPU 기술 |
| [Computer Science](./CS) | 분산 시스템, 운영체제, 자료구조와 알고리즘 |
| [Software Design](./설계) | Architecture Pattern, 시스템 설계, Production Readiness |
| [Load Testing](./부하테스트) | k6 설치, 시나리오 설계와 성능 검증 |
| [Docker](./Docker) | Container Image, Compose, Build와 공급망 보안 |
| [Linux](./Linux) | Network, 방화벽, Server 설정과 진단 명령어 |
| [Security](./보안) | 암호화, 인증서와 애플리케이션 보안 |

## 추천 시작 문서

- [AI Coding Agent를 위한 Context Engineering](./AI/AI%20Coding%20Agent를%20위한%20Context%20Engineering.md): 저장소 규칙을 AI가 사용할 수 있는 Context로 설계하는 방법
- [벡터·텐서에서 NVIDIA GPU Mini GPT까지](./AI/LLM/01.%20벡터%20행렬%20텐서와%20신경망%20가중치.md): 수학 기초부터 Transformer 학습 구현까지 이어지는 LLM 시리즈
- [Netcode 모델](./게임%20개발/네트워크/Netcode%20모델%20Lockstep%20Snapshot%20Prediction%20Rollback.md): Lockstep, Snapshot, Prediction, Rollback과 Lag Compensation 비교
- [Production Readiness Review](./설계/Production%20Readiness%20Review.md): 서비스가 운영 가능한지를 검증하는 관점
- [In-flight Deduplication](./Java%20Spring/Design%20Pattern/In-flight%20Deduplication.md): 동시에 들어온 동일 작업을 하나로 합치는 방법
- [Projection과 Hydration](./Java%20Spring/DB/JPA/Projection과%20Hydration.md): 조회 모델과 도메인 복원의 경계
- [k6 부하 테스트와 성능 검증](./Java%20Spring/Test/k6%20부하%20테스트와%20성능%20검증.md): 성능 목표와 부하 시나리오 설계
- [EKS 기반 GitOps 플랫폼 아키텍처 사례](./Infra/Architecture/EKS%20기반%20GitOps%20플랫폼%20아키텍처%20사례.md): AWS와 Kubernetes 운영 구조

## 문서 작성 원칙

- 특정 프로젝트나 조직의 이름보다 다른 환경에도 적용할 수 있는 기술 개념을 중심으로 설명합니다.
- 기술의 장점뿐 아니라 한계, 실패 상황과 Trade-off를 함께 기록합니다.
- 명령어와 Code는 맥락과 기대 결과를 설명할 수 있을 때 사용합니다.
- 학습 과제 목록보다 하나의 주제를 독립적으로 읽을 수 있는 완결된 글을 지향합니다.
- 외부 자료를 참고한 문서는 하단의 `Reference`에 출처를 남깁니다.

## 이 저장소에서 중요하게 생각하는 것

백엔드 엔지니어링은 대규모 트래픽을 처리하는 기술만으로 완성되지 않습니다. 언어와 Runtime을 정확히 이해하고, 읽기 쉬운 Code를 작성하며, 데이터 정합성과 실패 복구를 설계하고, 운영 결과를 관측할 수 있어야 합니다.

동작하는 구현을 넘어 유지보수성, 가독성, 검증 가능성과 운영 가능성을 함께 고민하는 것이 이 저장소의 목표입니다.
