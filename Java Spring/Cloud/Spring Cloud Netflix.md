---
id: Spring Cloud Netflix
started: 2025-08-24
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Netflix (Eureka & Legacy Stack)

## 1. 개요 (Overview)
public class EurekaServerApplication { ... }
```
- **Eureka Client 설정**
```yaml
eureka:
  client:
    service-url:
      defaultZone: http://localhost:8761/eureka/
  instance:
    prefer-ip-address: true
```

# Reference