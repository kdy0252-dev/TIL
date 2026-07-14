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

Logical Dump는 Database의 Schema와 Row를 SQL 또는 Archive 형식으로 내보낸다. File 복사보다 Version 간 이동과 일부 Table 복원에 유연하지만, 대규모 Database에서는 생성·복원 시간이 길고 실행 중인 Transaction 일관성을 별도로 고려해야 한다.

Backup은 Dump File이 만들어졌다는 사실이 아니라 **목표 시간 안에 복원되어 Application이 읽을 수 있음**을 검증해야 완성된다. 암호화, 보존 기간, 접근 권한과 정기 Restore Test를 함께 설계한다.

## DB 전체 Dump
```shell title="db 전체 dump"
mysqldump \
  --quick \
  --single-transaction \
  --routines \
  --events \
  --triggers \
  -h <host> \
  -u <user> \
  -p \
  <DB name> \
  > dump.sql
```

Shell의 `\` 뒤에는 주석이나 공백을 붙이지 않는다. 줄 연결이 끊어져 Option이 별도 명령으로 실행될 수 있다. `--no-data`는 전체 Dump가 아니라 Schema-only Dump이므로 전체 Backup 예제에서 제거했다.

`--single-transaction`은 Transactional Table에서 일관된 Snapshot을 얻고 장시간 Global Read Lock을 줄이는 데 유용하다. MyISAM 같은 Non-transactional Table, Dump 중 발생한 DDL과 모든 외부 상태까지 같은 일관성을 보장하지는 않는다.

```shell title="Schema만 Dump"
mysqldump --no-data -h <host> -u <user> -p <database> > schema.sql
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

Foreign Key와 Unique Check를 끄면 복원 속도가 개선될 수 있지만 잘못된 데이터도 들어갈 수 있다. 복원 종료 후 Constraint가 실제로 유효한지 검사하고, 오류가 발생해도 Check를 원복하도록 자동화한다. 운영 복원 전에는 빈 격리 Database에서 Version 호환성과 문자 집합을 검증한다.

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

PostgreSQL의 일반적인 Backup에는 Custom Archive 형식이 병렬 복원과 선택 복원에 유리하다.

```shell title="Custom Format Backup"
pg_dump \
  --format=custom \
  --file=database.dump \
  --host=<host> \
  --username=<user> \
  <database>

pg_restore --list database.dump
pg_restore \
  --clean \
  --if-exists \
  --dbname=<restore_database> \
  database.dump
```

`--clean`은 대상 Object를 삭제할 수 있으므로 새 복원 Database에서 먼저 실행한다. Role과 Tablespace 같은 Cluster 전역 Object는 `pg_dump`에 모두 포함되지 않으므로 필요하면 `pg_dumpall --globals-only`를 별도로 사용한다.

## 안전한 Credential 처리

Command Line의 `--password=<value>`는 Process 목록과 Shell History에 노출될 수 있다. MySQL Option File, PostgreSQL `.pgpass` 또는 Secret 주입을 사용하고 File 권한을 제한한다. Dump File에는 개인정보와 Password Hash가 포함될 수 있으므로 전송·보관 암호화와 접근 감사를 적용한다.

## 복원 검증 Checklist

1. Dump Tool과 Server Major Version 호환성을 기록한다.
2. Checksum을 생성해 전송 중 손상을 확인한다.
3. 새 Database에 실제로 복원한다.
4. Row Count만이 아니라 Constraint, Sequence, View, Function과 권한을 확인한다.
5. Application Migration을 적용하고 핵심 Read/Write Test를 실행한다.
6. RPO와 RTO 목표 안에 완료되는지 측정한다.

# Reference
[MySQL - mysqldump](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html)
[MariaDB - mariadb-dump](https://mariadb.com/kb/en/mariadb-dump/)
[PostgreSQL - pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html)
[PostgreSQL - pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html)
