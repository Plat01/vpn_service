# Architecture Rules

## Главная архитектурная позиция

Проект строится как **модульный монолит** на FastAPI с явным разделением на bounded contexts и слои DDD.

По умолчанию агент должен предпочитать:
- модульный монолит вместо ранних микросервисов;
- явные порты/адаптеры вместо прямой зависимости use case от внешней технологии;
- отдельные сущности и value objects вместо "словари везде";
- маленькие use case классы/функции вместо god-service.

## Обязательное разбиение по слоям

### Domain
Содержит:
- entities;
- value objects;
- domain policies;
- repository ports;
- domain events при необходимости.

Не содержит:
- FastAPI;
- SQLAlchemy ORM модели;
- HTTP исключения;
- прямой работы с временем системы без абстракции;
- прямой криптографии через конкретную библиотеку.

### Application
Содержит:
- use cases;
- orchestration;
- транзакционные сценарии;
- координацию нескольких repository ports;
- проверку политик доступа на уровне сценария.

### Infrastructure
Содержит:
- SQLAlchemy models;
- реализации repositories;
- crypto adapters;
- HAPP adapter;
- auth providers;
- внешние клиенты;
- кеш, очередь, внешние API.

### Presentation
Содержит:
- routers;
- request/response DTO;
- dependency wiring;
- mapping HTTP <-> use case.

## Что делать при новой фиче

При добавлении новой фичи агент должен:

1. определить bounded context;
2. определить, это новая сущность, value object, policy или application scenario;
3. не добавлять инфраструктурную деталь в domain;
4. держать внешний контракт стабильным и явным.

## Правила проектирования сущностей

- Если объект имеет собственный жизненный цикл и идентичность — это entity.
- Если объект описывает неизменяемое значение и сравнивается по значению — это value object.
- Если правило зависит от нескольких сущностей и не принадлежит одной из них — это domain service/policy.
- Если правило касается последовательности шагов, транзакции или авторизации запроса — это application layer.

## Обязательная аргументация выбора

Для любой архитектурной задачи агент обязан показать минимум 2 варианта:
- простой/быстрый;
- более расширяемый/строгий.

После этого агент обязан выбрать один и кратко объяснить:
- почему он лучше для DDD;
- как он влияет на SOLID;
- не создаёт ли он преждевременную сложность;
- как он скажется на будущем OAuth2 и личном кабинете.

## Рекомендуемая структура каталогов

```text
src/
  domain/
    identity/
    vpn_catalog/
    subscription_issuance/
    device_access/
    audit/
  application/
    identity/
    vpn_catalog/
    subscription_issuance/
    device_access/
    audit/
  infrastructure/
    db/
    auth/
    crypto/
    happ/
    repositories/
  presentation/
    http/
      api/
      dependencies/
      schemas/
tests/
  unit/
  integration/
  e2e/
```

## Антипаттерны, которых нужно избегать

- fat routers;
- fat repositories с бизнес-логикой;
- ORM model = domain model без обсуждения;
- один giant service "SubscriptionService" на всё;
- utils/helpers папка как свалка доменной логики;
- прямое чтение env внутри use case;
- хранение правил TTL/device limit только в Pydantic схеме.

## Когда можно упростить

Упростить можно, если:
- это не размывает границы домена;
- это не ухудшает тестируемость;
- это не блокирует будущий OAuth2/OIDC;
- это не заставит переписывать слой выдачи подписок.

Даже при упрощении агент должен назвать упрощение временным и описать путь эволюции.
