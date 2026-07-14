---
id: Private Repository 사용법
started: 2025-03-19
tags:
  - ✅DONE
  - Docker
group:
  - "[[Docker]]"
---
# Private Repository 사용법

Private Container Registry는 팀 내부 Image를 이름과 Tag로 배포하는 저장소다. Registry의 Repository는 Git Repository와 달리 Image Manifest와 여러 Layer Blob의 참조 관계로 구성된다. 이 구조 때문에 Server의 저장 Directory를 직접 지우면 공유 Layer 참조가 깨질 수 있다.

Image 이름은 보통 `<registry>/<repository>:<tag>` 형태다. Tag는 움직일 수 있는 별칭이고 Digest는 내용에서 계산된 불변 식별자다. 운영 배포에서 같은 Tag를 덮어쓸 수 있다면 실제 배포 Image를 추적하기 위해 Digest와 Build Metadata를 함께 남긴다.

## Local Repository 확인 및 삭제 방법
### 내부 리포지토리 확인
```shell title="docker local registry 내부 리포지토리 확인"
curl --fail --silent http://127.0.0.1:5000/v2/_catalog

curl -s -u <username>:<password> https://<your-registry-domain>/v2/_catalog

curl -s -u <username>:<password> https://<your-registry-domain>/v2/<repository-name>/tags/list

```
Catalog API는 Registry에 존재하는 Repository 이름을 나열한다. Pagination과 접근 제어 정책이 적용될 수 있으므로 결과가 전체 목록이라고 무조건 가정하지 않는다.

### Manifest를 API로 삭제하기

Filesystem Directory를 직접 삭제하지 않는다. 먼저 Registry 설정에서 Manifest 삭제를 허용한 뒤, Tag가 가리키는 Manifest Digest를 구해 Digest로 삭제한다.

```shell
digest=$(curl --silent --head \
  --header 'Accept: application/vnd.docker.distribution.manifest.v2+json' \
  https://<registry>/v2/<repository>/manifests/<tag> \
  | awk -F': ' 'tolower($1) == "docker-content-digest" {print $2}' \
  | tr -d '\r')

curl --request DELETE \
  https://<registry>/v2/<repository>/manifests/$digest
```

Manifest 삭제는 참조를 제거할 뿐 Blob Disk 공간을 즉시 회수하지 않을 수 있다. Garbage Collection은 Registry를 읽기 전용으로 전환하거나 중지한 상태에서 먼저 `--dry-run`으로 확인한다. Upload와 동시에 실행하면 아직 Mark되지 않은 Layer를 지워 Registry를 손상할 수 있다.

### Tar File Load
```shell title="image tar file load"
docker load --input <image.tar>
  
docker tag {원래 이미지}:{태그} {도커 이미지 레지스트리 주소:포트}/{이미지 이름}:{태그}  
  
docker push {도커 이미지 레지스트리 주소:포트}/{이미지 이름}:{태그}
```

`docker save`/`load`는 Image Layer, Tag와 Metadata를 보존한다. `docker export`/`import`는 Container Filesystem Snapshot을 다루며 Image History와 설정을 동일하게 보존하지 않으므로 폐쇄망 Image 전달에는 보통 `save`/`load`를 사용한다.

## 인증서와 인증

운영 Registry는 TLS와 인증을 기본으로 한다. `insecure-registries`는 통신 위·변조 위험이 있으므로 격리된 개발망의 임시 구성이 아니라면 사용하지 않는다. 사설 CA를 쓴다면 Docker와 Container Runtime의 Trust Store에 CA 인증서를 배포한다.

```shell
docker login registry.example.internal
docker push registry.example.internal/team/order-api:1.4.2
docker logout registry.example.internal
```

CI에서는 개인 Password 대신 최소 권한 Robot Account나 짧은 수명의 Token을 사용하고, Credential이 Build Log에 출력되지 않게 한다. Registry 데이터와 설정, 인증서의 Backup 및 실제 복원도 정기적으로 검증한다.

# Reference
[CNCF Distribution - Registry](https://distribution.github.io/distribution/about/)
[CNCF Distribution - Garbage collection](https://distribution.github.io/distribution/about/garbage-collection/)
[OCI Distribution Specification](https://github.com/opencontainers/distribution-spec)
