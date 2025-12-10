---
id: DB Dump
started: 2025-05-08
tags:
  - ✅DONE
  - DB
group:
  - "[[DBMS]]"
---
# Mysql & Maria DB Dump
## DB 전체 Dump
```shell title="db 전체 dump"
mysqldump \
  --quick \
  --single-transaction \ # Single Transaction으로 실행됨
  --no-create-db \ # DB 생성문만 없어짐
  --no-data \ # 데이터 덤프뜨지 않고 스키마만 뜸
  -h <host> \
  -u <user> \
  -p \
  <DB name> \
  > dump.sql
```

```shell title="dump 파일 적용하기"
(
  echo "SET autocommit=0;"
  echo "SET foreign_key_checks=0;"
  echo "SET unique_checks=0;"
  cat 스크립트 파일.sql
  echo "SET unique_checks=1;"
  echo "SET foreign_key_checks=1;"
  echo "COMMIT;"
) | mariadb -u<User ID> -p <DB Name>
```
# PostgreSQL DB Dump
## DB Schema Dump
```shell title="postgreSQL DB Schema dump"
pg_dump \
  -h <호스트> -p <포트> -U <사용자> \
  -s \                # --schema-only
  -t your_table \     # 특정 테이블만
  your_database \
  > table-schema.sql
```

# Reference