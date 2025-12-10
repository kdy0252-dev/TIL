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
## Local Repository 확인 및 삭제 방법
### 내부 리포지토리 확인
```shell title="docker local registry 내부 리포지토리 확인"
curl -XGET 127.0.0.1:5000/v2/_catalog

curl -s -u <username>:<password> https://<your-registry-domain>/v2/_catalog

curl -s -u <username>:<password> https://<your-registry-domain>/v2/<repository-name>/tags/list

```
### 내부 리포지토리 삭제
```shell title="docker local Registry 내부의 리포지토리 삭제"
docker exec -it ieee160921-registry sh

cd /var/lib/registry/docker/registry/v2/repositories 내부에서 삭제
```
### Tar File Load
```shell title="image tar file load"
docker load -i {도커 이미지 tar 파일}  
  
docker tag {원래 이미지}:{태그} {도커 이미지 레지스트리 주소:포트}/{이미지 이름}:{태그}  
  
docker push {도커 이미지 레지스트리 주소:포트}/{이미지 이름}:{태그}
```
# Reference