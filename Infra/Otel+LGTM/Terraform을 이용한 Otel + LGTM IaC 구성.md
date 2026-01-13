---
id: Otel + LGTM IaC구성
started: 2026-01-13
tags:
  - ✅DONE
group: []
---
# Terraform을 이용한 Otel + LGTM IaC 구성

이 문서는 인프라 전문가가 아닌 **백엔드 개발자가 서비스 운영에 필요한 최소한의 관측성을 확보하기 위해 간단히 구성**하였습니다. 복잡한 설정보다는 기초적인 연동을 중심으로 기술합니다.

## 1. 개요
OpenTelemetry(Otel) Collector를 통해 메트릭, 로그, 트레이스를 수집하고, 이를 Grafana LGTM(Loki, Grafana, Tempo, Mimir) 스택으로 전송하는 구조를 IaC로 정의합니다.

## 2. Terraform 구성 상세 가이드

### 2.1 기본 설정 및 변수 (Helm Provider Setup)

먼저 AWS EKS 환경 정보와 사용자의 계정 정보를 가져오는 기본 설정을 정의합니다.

```yaml
data "aws_caller_identity" "current" {}
data "aws_eks_cluster" "cluster" {
  name = var.service_cluster_name
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  oidc_url   = replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")
}
```

> **동적 데이터 참조**: 하드코딩된 값 대신 `data` 소스를 사용하여 현재 실행 중인 AWS 계정 ID와 EKS 클러스터 정보를 동적으로 가져옵니다. 이는 코드를 다른 환경(스테이징, 프로덕션)에 그대로 가져가도 수정 없이 동작하게 만드는 IaC의 핵심 원칙입니다.
> **OIDC URL 정제**: EKS의 IAM Role 연동(IRSA)을 위해 OIDC Provider URL이 필수적입니다. `replace` 함수를 통해 `https://` 프로토콜을 제거하는 전처리 과정은 IRSA 모듈이 요구하는 형식을 맞추기 위함입니다.

---
### 2.2 S3 버킷 구성 (LGTM Storage)

로그(Loki), 메트릭(Mimir), 트레이스(Tempo) 데이터를 저장할 S3 버킷을 각각 생성합니다.

```yaml
#######################
# S3 Buckets for LGTM #
#######################

resource "aws_s3_bucket" "loki_storage" {
  bucket        = lower("${var.service_cluster_name}-loki-storage")
  force_destroy = true
}

resource "aws_s3_bucket" "mimir_storage" {
  bucket        = lower("${var.service_cluster_name}-mimir-storage")
  force_destroy = true
}

resource "aws_s3_bucket" "mimir_alertmanager_storage" {
  bucket        = lower("${var.service_cluster_name}-mimir-alertmanager-storage")
  force_destroy = true
}

resource "aws_s3_bucket" "mimir_ruler_storage" {
  bucket        = lower("${var.service_cluster_name}-mimir-ruler-storage")
  force_destroy = true
}

resource "aws_s3_bucket" "tempo_storage" {
  bucket        = lower("${var.service_cluster_name}-tempo-storage")
  force_destroy = true
}
```

> **데이터 격리 전략**: 모든 데이터를 하나의 버킷에 넣지 않고 컴포넌트별로(심지어 Mimir의 내부 컴포넌트별로) 분리했습니다.
> **이유**: 로그, 메트릭, 트레이스는 데이터의 성격과 보존 주기(Retention)가 다릅니다. 예를 들어, 트레이스 데이터는 용량이 크지만 장기 보관 필요성이 낮아 7일 후 삭제 정책을 걸고, 로그는 컴플라이언스 이슈로 1년 보관 정책을 걸 수 있습니다. 버킷을 분리해야 이러한 라이프사이클 관리가 가능합니다.
> - **`force_destroy = true`**: 테라폼 삭제 시 버킷 안에 파일이 있어도 강제로 삭제하는 옵션입니다.
> **주의**: 운영 환경(Production)에서는 실수로 데이터가 날아가는 것을 방지하기 위해 이 옵션을 `false`로 하거나 백업 정책을 마련해야 합니다. 하지만 개발자가 빠르고 간단하게 구축하고 테스트장을 허물기 위해서는 필수적인 옵션입니다.

---

### 2.3 권한 관리 (IAM Roles & IRSA)
Kubernetes 파드(Pod)가 S3에 접근할 수 있도록 IAM Policy와 Role을 생성하고 연결합니다.
```yaml
##########################
# IAM Roles & IRSA Setup #
##########################

# IAM Policy for Loki S3 Access
resource "aws_iam_policy" "loki_s3_policy" {
  name        = "${var.service_cluster_name}-LokiS3Policy"
  description = "Policy for Loki S3 access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = ["s3:ListBucket", "s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.loki_storage.arn,
          "${aws_s3_bucket.loki_storage.arn}/*"
        ]
      }
    ]
  })
}

# IAM Policy for Mimir S3 Access
resource "aws_iam_policy" "mimir_s3_policy" {
  name        = "${var.service_cluster_name}-MimirS3Policy"
  description = "Policy for Mimir S3 access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = ["s3:ListBucket", "s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.mimir_storage.arn,
          "${aws_s3_bucket.mimir_storage.arn}/*",
          aws_s3_bucket.mimir_alertmanager_storage.arn,
          "${aws_s3_bucket.mimir_alertmanager_storage.arn}/*",
          aws_s3_bucket.mimir_ruler_storage.arn,
          "${aws_s3_bucket.mimir_ruler_storage.arn}/*"
        ]
      }
    ]
  })
}

# IAM Policy for Tempo S3 Access
resource "aws_iam_policy" "tempo_s3_policy" {
  name        = "${var.service_cluster_name}-TempoS3Policy"
  description = "Policy for Tempo S3 access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = ["s3:ListBucket", "s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.tempo_storage.arn,
          "${aws_s3_bucket.tempo_storage.arn}/*"
        ]
      }
    ]
  })
}

# Generic Module for IRSA
module "irsa_monitoring" {
  for_each = {
    loki  = aws_iam_policy.loki_s3_policy.arn
    mimir = aws_iam_policy.mimir_s3_policy.arn
    tempo = aws_iam_policy.tempo_s3_policy.arn
  }
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role-with-oidc"
  version = "5.39.0"

  create_role                   = true
  role_name                     = "AmazonEKSTF${title(each.key)}Role-${var.service_cluster_name}"
  provider_url                  = local.oidc_url
  role_policy_arns              = [each.value]
  oidc_fully_qualified_subjects = ["system:serviceaccount:monitoring:${each.key}"]
}
```

>**최소 권한 원칙 (Least Privilege)**:
>- 과거에는 워커 노드(EC2) 전체에 S3 Full Access를 주는 위험한 방식을 썼지만, 여기서는 **IRSA(IAM Roles for Service Accounts)**를 사용했습니다.
>- Loki 파드는 오직 Loki 버킷에만, Tempo 파드는 오직 Tempo 버킷에만 접근할 수 있습니다. 이는 보안 사고 발생 시 피해 범위를 획기적으로 줄여줍니다.
>**모듈화의 활용**: `for_each` 반복문을 사용하여 Loki, Mimir, Tempo 3개의 서비스에 대한 IRSA 설정을 단 하나의 모듈 블록으로 깔끔하게 처리했습니다. 이는 코드 중복을 줄이고 유지보수성을 높이는 백엔드 개발자의 센스가 돋보이는 부분입니다.
>**애플리케이션 코드의 해방**: 이 방식을 사용하면 애플리케이션(Loki 등) 설정 파일에 AWS Access Key를 박아넣을 필요가 없습니다. 쿠버네티스가 자동으로 인증 토큰을 파드에 주입해주기 때문입니다.

---
### 2.4 로깅 시스템: Grafana Loki
CloudWatch Logs나 Elasticsearch 대신, 비용 효율적인 Loki를 분산 모드로 구축합니다.
```yaml
#########################
# Helm Releases: LGTM #
#########################

# https://artifacthub.io/packages/helm/grafana/loki
resource "helm_release" "loki" {
  name             = "loki"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "loki"
  version          = "6.27.0"
  namespace        = "monitoring"
  create_namespace = true

  values = [
    yamlencode({
      deploymentMode = "Distributed"

      loki = {
        storage = {
          type = "s3"
          bucketNames = {
            chunks = aws_s3_bucket.loki_storage.id
            ruler  = aws_s3_bucket.loki_storage.id
            admin  = aws_s3_bucket.loki_storage.id
          }
          s3 = {
            region = var.target_region
          }
        }
        auth_enabled = false
      }

      serviceAccount = {
        create = true
        name   = "loki"
        annotations = {
          "eks.amazonaws.com/role-arn" = module.irsa_monitoring["loki"].iam_role_arn
        }
      }

      # Optional: storageClass for PVCs if needed by components
      global = {
        storageClass = "gp3"
      }
    })
  ]
}
```

>**왜 Loki인가?**: 백엔드 개발자에게 가장 익숙한 `grep`처럼 로그를 검색할 수 있습니다. 텍스트 전체를 인덱싱하는 ELK와 달리 라벨만 인덱싱하므로 리소스 사용량이 훨씬 적습니다.
>**분산 모드 (Distributed)**: `deploymentMode = "Distributed"` 설정은 Loki를 단일 바이너리가 아닌 마이크로서비스(Ingester, Distributor, Querier 등)로 쪼개서 배포합니다. 
>- **장점**: 로그 유입량이 많을 땐 Ingester만 늘리고, 검색 속도가 느릴 땐 Querier만 늘리는 식의 유연한 확장이 가능합니다.
>**S3 백엔드**: 로컬 디스크가 아닌 S3를 저장소로 씁니다. 디스크 용량 모니터링이나 증설 작업 없이 무제한으로 로그를 저장할 수 있다는 점은 운영 부담을 0에 가깝게 만듭니다.
>**`auth_enabled = false`**: 멀티테넌시 기능을 껐습니다. 사내 단일 팀이나 단일 서비스를 위한 구성이라면 불필요한 테넌트 헤더(`X-Scope-OrgID`) 관리를 하지 않아도 되므로 구성이 훨씬 간단해집니다.

---

### 2.5 메트릭 시스템: Grafana Mimir

Prometheus의 장기 보관소 역할을 하는 Mimir를 구성합니다.

```yaml
# https://artifacthub.io/packages/helm/grafana/mimir-distributed
resource "helm_release" "mimir" {
  name             = "mimir"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "mimir-distributed"
  version          = "6.0.5"
  namespace        = "monitoring"
  create_namespace = true

  values = [
    yamlencode({
      global = {
        storageClass = "gp3"
      }
      mimir = {
        structuredConfig = {
          multitenancy_enabled = false
          common = {
            storage = {
              backend = "s3"
              s3 = {
                endpoint    = "s3.${var.target_region}.amazonaws.com"
                bucket_name = aws_s3_bucket.mimir_storage.id
                region      = var.target_region
              }
            }
          }
          blocks_storage = {
            backend = "s3"
            s3 = {
              endpoint    = "s3.${var.target_region}.amazonaws.com"
              bucket_name = aws_s3_bucket.mimir_storage.id
              region      = var.target_region
            }
          }
          alertmanager_storage = {
            backend = "s3"
            s3 = {
              endpoint    = "s3.${var.target_region}.amazonaws.com"
              bucket_name = aws_s3_bucket.mimir_alertmanager_storage.id
              region      = var.target_region
            }
          }
          ruler_storage = {
            backend = "s3"
            s3 = {
              endpoint    = "s3.${var.target_region}.amazonaws.com"
              bucket_name = aws_s3_bucket.mimir_ruler_storage.id
              region      = var.target_region
            }
          }
          ingester = {
            push_grpc_method_enabled = true
            ring = {
              replication_factor = 1
            }
          }
          ingest_storage = {
            enabled = false
          }
        }
      }

      ingester = {
        replicas = 1
        zoneAwareReplication = {
          enabled = false
        }
        persistentVolume = {
          size         = "10Gi"
          storageClass = "gp3"
        }
      }
      distributor = {
        replicas = 1
      }
      querier = {
        replicas = 1
      }
      query_scheduler = {
        replicas = 1
      }
      alertmanager = {
        replicas = 1
        persistentVolume = {
          storageClass = "gp3"
        }
      }
      compactor = {
        persistentVolume = {
          storageClass = "gp3"
        }
      }
      store_gateway = {
        replicas = 1
        zoneAwareReplication = {
          enabled = false
        }
        persistentVolume = {
          storageClass = "gp3"
        }
      }
      serviceAccount = {
        create = true
        name   = "mimir"
        annotations = {
          "eks.amazonaws.com/role-arn" = module.irsa_monitoring["mimir"].iam_role_arn
        }
      }
      minio = {
        enabled = false
      }
      kafka = {
        enabled = false
      }
    })
  ]
}
```

>**복잡성 제거**: Mimir는 기본적으로 대규모 ISP급 운영을 위해 설계되어 매우 복잡합니다. 하지만 여기서 백엔드 개발자가 주목할 점은 `multitenancy_enabled = false`와 `replication_factor = 1` 설정입니다.
>- **Replication Factor = 1**: 개발/스테이징 환경에서는 데이터를 3중으로 복제할 필요가 없습니다. 이를 1로 줄임으로써 스토리지 비용과 통신 오버헤드를 1/3로 줄이는 실용적인 구성을 택했습니다.
>**S3 기반 블록 스토리지**: `blocks_storage` 설정은 메트릭 데이터를 일정 시간(보통 2시간) 메모리에 들고 있다가, 압축하여 S3에 덩어리(Block)째로 저장합니다. 
>- 이는 Prometheus가 로컬 디스크를 사용할 때 겪는 장기 보관의 어려움을 완벽하게 해결합니다. 백엔드 개발자는 "2년 전 크리스마스의 CPU 사용량"도 S3 비용만으로 저렴하게 확인할 수 있습니다.
>**멀티태넌시 비활성화 (`multitenancy_enabled = false`) 심층 분석**:
>- **왜 필요한가?**: SaaS(Software as a Service) 형태의 모니터링 시스템을 구축할 때, '고객 A'의 데이터가 '고객 B'에게 보이면 안 됩니다. Mimir는 기본적으로 `X-Scope-OrgID`라는 헤더를 통해 데이터를 격리하는 멀티태넌시 기능을 제공합니다.
>- **왜 껐는가?**: 사내 서비스 모니터링 용도라면 우리 팀이 남의 팀 데이터를 본다고 큰일이 나지 않습니다. 오히려 헤더를 매번 설정해야 하는 번거로움이 더 큽니다.
>- **장점**: 
>  1. **쿼리 복잡도 감소**: Grafana 데이터소스 설정 시 별도의 헤더를 주입할 필요가 없습니다.
>  2. **수집 파이프라인 단순화**: Otel Collector나 앱에서 데이터를 보낼 때 테넌트 ID를 신경 쓸 필요가 없습니다.
>- **단점**: 데이터 격리가 안 되므로, 특정 팀의 메트릭만 골라서 지우거나 용량 쿼터를 제한하는 세밀한 제어가 어렵습니다.
>
>**Kafka 비활성화 (`kafka.enabled = false`) 심층 분석**:
>- **왜 껐는가?**: Mimir는 대규모 트래픽을 처리하기 위해 인제션(수집) 경로에 Kafka를 버퍼로 둘 수 있습니다. 하지만 이는 운영 복잡도를 기하급수적으로 높입니다.
>- **장점 (Simplification)**: Zookeeper나 Kraft 같은 분산 코디네이터를 관리할 필요가 없습니다. 백엔드 개발자가 가장 싫어하는 "Kafka 터져서 모니터링 죽는" 상황을 원천 차단합니다. 비용 측면에서도 EC2 인스턴스 3~5대 분량을 아낄 수 있습니다.
>- **단점 (Risk)**: 트래픽이 순간적으로 Mimir가 처리할 수 있는 양을 넘어서면(Burst), 버퍼가 없어서 데이터가 유실될 수 있습니다(Drop). 하지만 금융권의 정산 데이터가 아닌 이상, 1~2분의 CPU 메트릭 유실은 허용 가능한 리스크입니다. "완벽함"보다 "운영 가능함"을 선택한 결과입니다.
>**MinIO 비활성화**: AWS S3를 사용하므로 클러스터 내부에 MinIO를 띄울 이유가 전혀 없습니다. `enabled = false`로 명시하여 리소스를 아낍니다.

---
### 2.6 분산 트레이싱: Grafana Tempo
마이크로서비스 간의 복잡한 호출 관계를 추적하는 Tempo를 구성합니다.
```yaml
# https://artifacthub.io/packages/helm/grafana/tempo-distributed
resource "helm_release" "tempo" {
  name             = "tempo"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "tempo-distributed"
  version          = "1.60.0"
  namespace        = "monitoring"
  create_namespace = true

  values = [
    yamlencode({
      global = {
        storageClass = "gp3"
      }
      reportingEnabled = false
      traces = {
        otlp = {
          grpc = {
            enabled = true
          }
        }
      }
      storage = {
        trace = {
          backend = "s3"
          s3 = {
            bucket = aws_s3_bucket.tempo_storage.id
            region = var.target_region
          }
        }
      }
      tempo = {
        structuredConfig = {
          storage = {
            trace = {
              backend = "s3"
              s3 = {
                endpoint = "s3.${var.target_region}.amazonaws.com"
                bucket   = aws_s3_bucket.tempo_storage.id
                region   = var.target_region
              }
            }
          }
        }
      }
      serviceAccount = {
        create = true
        name   = "tempo"
        annotations = {
          "eks.amazonaws.com/role-arn" = module.irsa_monitoring["tempo"].iam_role_arn
        }
      }
      ingester = {
        replicas = 1
        config = {
          replication_factor = 1
        }
      }
      distributor = {
        replicas = 1
        receivers = {
          otlp = {
            protocols = {
              grpc = {
                endpoint = "0.0.0.0:4317"
              }
            }
          }
        }
        service = {
          extraPorts = [
            {
              name       = "otlp-grpc"
              protocol   = "TCP"
              port       = 4317
              targetPort = 4317
            }
          ]
        }
      }
      compactor = {
        replicas = 1
      }
      querier = {
        replicas = 1
      }
      queryFrontend = {
        replicas = 1
      }
      minio = {
        enabled = false
      }
    })
  ]
}
```

>**OTLP(OpenTelemetry Protocol) 준비 완료**: `extraPorts` 설정으로 `4317` 포트를 명시적으로 열었습니다. 이는 Tempo가 "나는 표준 프로토콜로 트레이스 데이터를 받을 준비가 됐다"고 선언하는 것입니다. 백엔드 앱은 이제 벤더 종속적인 에이전트 없이 OTLP 포맷으로 데이터만 쏘면 됩니다.
>**S3 백엔드의 중요성**: 트레이스 데이터는 용량이 매우 큽니다. 모든 요청의 헤더와 태그를 저장하기 때문입니다. Tempo는 이를 S3에 저장함으로써 "스토리지 비용 때문에 트레이싱을 끈다"는 딜레마를 해결해 줍니다. 백엔드 개발자는 마음 놓고 `Trace`를 활성화할 수 있습니다.
>**구조의 일관성**: Loki, Mimir와 동일하게 Ingester, Distributor 같은 분산 아키텍처를 가집니다. 하나를 이해하면 나머니 둘도 이해할 수 있는 일관된 구조는 학습 비용을 낮춰줍니다.

---
### 2.7 데이터 수집 파이프라인: OpenTelemetry Collector
애플리케이션과 저장소(LGTM) 사이의 중개자 역할을 하는 Collector를 설정합니다.
```yaml
resource "helm_release" "otel_collector" {
  name             = "otel-collector"
  repository       = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart            = "opentelemetry-collector"
  version          = "0.143.0"
  namespace        = "monitoring"
  create_namespace = true

  values = [
    yamlencode({
      image = {
        repository = "otel/opentelemetry-collector-contrib"
        tag        = "0.91.0"
      }
      mode = "deployment"
      config = {
        receivers = {
          otlp = {
            protocols = {
              grpc = {}
              http = {}
            }
          }
        }
        exporters = {
          prometheusremotewrite = {
            endpoint = "http://mimir-distributor.monitoring.svc.cluster.local:8080/api/v1/push"
          }
          loki = {
            endpoint = "http://loki-loki-distributed-distributor.monitoring.svc.cluster.local:3100/loki/api/v1/push"
          }
          "otlp/tempo" = {
            endpoint = "tempo-distributor.monitoring.svc.cluster.local:4317"
            tls      = { insecure = true }
          }
        }
        service = {
          pipelines = {
            metrics = {
              receivers = ["otlp"]
              exporters = ["prometheusremotewrite"]
            }
            logs = {
              receivers = ["otlp"]
              exporters = ["loki"]
            }
            traces = {
              receivers = ["otlp"]
              exporters = ["otlp/tempo"]
            }
          }
        }
      }
    })
  ]

  depends_on = [
    helm_release.mimir,
    helm_release.tempo,
    helm_release.loki
  ]
}
```

>**벤더 중립성(Vendor Agnostic)의 실현**: 이 부분이 전체 아키텍처의 핵심입니다. 애플리케이션은 Collector에게 OTLP로 데이터를 보냅니다. Collector는 이를 받아서:
>- 메트릭은 `prometheusremotewrite`로 변환해 Mimir로,
>- 로그는 `loki` 프로토콜로 변환해 Loki로,
>- 트레이스는 `otlp` 그대로 Tempo로 보냅니다.
>**백엔드 개발자를 위한 이점**: 만약 내일 당장 회사가 "우리는 Datadog을 쓰겠다"라고 결정해도, 애플리케이션 코드는 **단 한 줄도 수정할 필요가 없습니다**. 오직 Collector의 `exporters` 설정만 Datadog으로 바꾸면 됩니다. 이것이 바로 느슨한 결합(Loose Coupling)이 주는 강력함입니다.
>**`deployment` 모드**: Collector를 데몬셋(DaemonSet)으로 모든 노드에 띄우는 대신, 디플로이먼트(Deployment)로 하나만 띄웠습니다. 트래픽이 적은 개발 단계에서는 리소스를 아끼는 합리적인 선택입니다.

---
### 2.8 시각화 및 대시보드: Grafana
모든 데이터를 한 눈에 볼 수 있는 Grafana를 설치하고 데이터 소스를 자동 연결합니다.
```yaml
# https://github.com/grafana/helm-charts
resource "helm_release" "grafana" {
  name             = "grafana"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "grafana"
  version          = "10.5.5"
  namespace        = "monitoring"
  create_namespace = true

  values = [
    yamlencode({
      adminUser     = var.grafana_admin_user
      adminPassword = var.grafana_admin_password
      ingress = {
        enabled          = true
        ingressClassName = "alb"
        annotations = {
          "alb.ingress.kubernetes.io/scheme"          = "internal"
          "alb.ingress.kubernetes.io/target-type"     = "ip"
          "alb.ingress.kubernetes.io/security-groups" = "${var.eks_cluster_sg_id},${var.node_group_sg_id},${var.client_vpn_sg_id}"
          "alb.ingress.kubernetes.io/listen-ports"    = jsonencode([{ HTTP = 80 }])
        }
        hosts = [var.grafana_domain_name]
      }
      datasources = {
        "datasources.yaml" = {
          apiVersion = 1
          datasources = [
            {
              name      = "Loki"
              type      = "loki"
              url       = "http://loki-loki-distributed-query-frontend.monitoring.svc.cluster.local:3100"
              access    = "proxy"
              isDefault = false
            },
            {
              name      = "Mimir"
              type      = "prometheus"
              url       = "http://mimir-query-frontend.monitoring.svc.cluster.local:8080/prometheus"
              access    = "proxy"
              isDefault = true
            },
            {
              name      = "Tempo"
              type      = "tempo"
              url       = "http://tempo-query-frontend.monitoring.svc.cluster.local:3200"
              access    = "proxy"
              isDefault = false
            }
          ]
        }
      }
    })
  ]
  depends_on = [var.alb_controller_id]
}
```

>**프로비저닝(Provisioning) 자동화**: `datasources.yaml` 섹션을 통해 Loki, Mimir, Tempo를 Grafana 데이터 소스로 **자동 등록**합니다. 
>- 수동으로 IP를 입력하고 연결 테스트를 하는 번거로움과 실수를 원천 차단합니다. Terraform `apply`가 끝나는 순간, Grafana에는 이미 모든 연결이 완료되어 있습니다.
>**보안 인그레스(Ingress) 설정**: 
>- `scheme = "internal"`: 로드밸런서를 인터넷에 노출하지 않고 내부망 전용으로 만듭니다.
>- `security-groups`: 사내 VPN이나 특정 보안 그룹에서만 접근 가능하도록 제한함으로써, 모니터링 대시보드가 외부에 노출되는 보안 위협을 방지했습니다. 
>- 웹 브라우저에서 `var.grafana_domain_name`으로 접속만 하면 됩니다.

1. **상관 관계 분석 (Correlation)**: Grafana에서 에러 로그(Loki)를 보다가, 연결된 트레이스 버튼을 누르면 해당 요청의 전체 흐름(Tempo)을 볼 수 있고, 당시의 CPU 상태(Mimir)까지 한 큐에 파악 가능합니다. 이 구성을 통해 그것이 자동으로 연결됩니다.
2. **비용 효율성**: 모든 무거운 데이터는 저렴한 AWS S3로 보냅니다. 디스크 터질 걱정 없이 맘껏 로그를 찍으셔도 됩니다.
3. **확장성**: 사용자 트래픽이 늘어나면 Terraform에서 `replicas: 1`을 `replicas: 3`으로 바꾸고 `apply`하는 것으로 가용성을 늘릴 수 있습니다. 인프라 구조 변경 없이 성능만 선형적으로 확장됩니다.

# Reference