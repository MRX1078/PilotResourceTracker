# Pilot Resource Tracker (MVP)

Внутренний веб-сервис для учета загрузки сотрудников по пилотам, расчета трудозатрат, стоимости ресурсов и оценки доходности.

## Документация
- Подробная инструкция по сервису, запуску и эксплуатации: [docs/INSTRUCTION_RU.md](/Users/maksimshatokhin/Documents/New%20project/pilot-resource-tracker/docs/INSTRUCTION_RU.md)

## Что реализовано
- Backend на FastAPI + SQLAlchemy + PostgreSQL
- Alembic миграции
- Seed-данные (5 пилотов, 12 сотрудников, пересечения, несколько недель)
- SQL refresh через Trino (`POST /api/pilots/{id}/refresh`, `POST /api/pilots/refresh-all`)
- Валидация колонок SQL-ответа Trino
- История запусков SQL-запросов (`trino_query_runs`)
- Импорт назначений сотрудников из CSV в ручных пилотах
- Экспорт/импорт полного бэкапа БД для передачи между коллегами
- Frontend на React + TypeScript + Vite + Ant Design + Recharts
- Dashboard, список пилотов, карточка пилота, форма пилота, карточка сотрудника, страница сотрудников, страница обновлений, страница бэкапов
- Базовые тесты расчетов метрик (`pytest`)

## Архитектура проекта

```text
pilot-resource-tracker/
  backend/
    app/
      api/
      config.py
      constants.py
      database.py
      main.py
      models/
      schemas/
      services/
        metrics_service.py
        refresh_service.py
        trino_service.py
      utils/
    alembic/
    scripts/seed.py
    tests/test_metrics_service.py
    Dockerfile
  frontend/
    src/
      api/
      components/
      hooks/
      pages/
      types/
      utils/
    Dockerfile
  docker-compose.yml
  .env.example
```

## 1. Как запустить проект локально

### Вариант A: через Docker Compose
1. Скопируйте env:
   - `cp .env.example .env`
2. Поднимите сервисы:
   - `docker compose up --build`
3. Примените seed (один раз):
   - `docker compose exec backend python scripts/seed.py`
4. Откройте:
   - Frontend: `http://localhost:5173`
   - Backend OpenAPI: `http://localhost:8000/docs`

### Вариант B: локально без Docker
1. Поднимите PostgreSQL и создайте БД `pilot_tracker`.
2. Backend:
   - `cd backend`
   - `python3 -m pip install -r requirements.txt`
   - `cp .env.example .env`
   - `alembic upgrade head`
   - `PYTHONPATH=. python scripts/seed.py`
   - `PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
3. Frontend:
   - `cd frontend`
   - `npm install`
   - `npm run dev`

## 2. Какие env-переменные нужны

### Обязательные
- `DATABASE_URL`
- `CORS_ORIGINS`
- `WORK_HOURS_PER_WEEK` (по умолчанию 40)
- `COST_PER_MINUTE` (по умолчанию 23)

### Для Trino (SQL-режим)
- `TRINO_HOST` (обязательно)
- `TRINO_PORT`
- `TRINO_USER` (обязательно)
- `TRINO_PASSWORD` (опционально)
- `TRINO_CATALOG` (опционально, но нужен если указываете `TRINO_SCHEMA`)
- `TRINO_SCHEMA` (опционально)
- `TRINO_HTTP_SCHEME`

### Для frontend
- `VITE_API_BASE_URL` (обычно `http://localhost:8000/api`)

## 3. Какие endpoints доступны

### Pilots
- `GET /api/pilots`
- `GET /api/pilots/{id}`
- `POST /api/pilots`
- `PUT /api/pilots/{id}`
- `DELETE /api/pilots/{id}`
- `POST /api/pilots/{id}/refresh`
- `POST /api/pilots/refresh-all`
- `POST /api/pilots/validate-sql`

### Employees
- `GET /api/employees`
- `POST /api/employees/import-csv`
- `GET /api/employees/{id}`
- `GET /api/employees/{id}/pilots`
- `GET /api/employees/by-cas/{cas}`

### Assignments
- `GET /api/pilots/{pilot_id}/assignments`
- `POST /api/pilots/{pilot_id}/assignments`
- `PUT /api/assignments/{id}`
- `DELETE /api/assignments/{id}`

### Metrics + Dashboard
- `GET /api/pilots/{pilot_id}/metrics`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/cross-assignments`
- `GET /api/dashboard/weekly-costs`
- `GET /api/dashboard/resource-load`
- `GET /api/dashboard/resource-by-rc`

### SQL update history
- `GET /api/trino-runs`

### Backup / Data transfer
- `GET /api/system/backup/export`
- `POST /api/system/backup/import?run_refresh_all_sql=true|false`

## 4. Как работает refresh одного пилота
- Endpoint: `POST /api/pilots/{pilot_id}/refresh`
- Проверяется, что пилот активен и в `sql`-режиме.
- Создается запись в `trino_query_runs` со статусом `running`.
- Выполняется SQL через `TrinoService`.
- Валидируются колонки результата: обязательно `hours` и дата (`week_start_date` или `date`/`work_date`/`event_date`), а также идентификатор сотрудника:
  - либо `cas` (рекомендуется),
  - либо связка `full_name + rc`.
- Если сотрудник с таким `cas` уже есть в системе, ФИО/РЦ подтягиваются автоматически из справочника.
- Если `cas` не найден в справочнике, нужно либо сначала импортировать сотрудников, либо вернуть `full_name` и `rc` в SQL.
- Если `load_percent` отсутствует, считается как `hours / WORK_HOURS_PER_WEEK * 100`.
- `pshe` считается как `hours / WORK_HOURS_PER_WEEK`.
- SQL-назначения пилота пересоздаются.
- Пересчитываются недельные метрики пилота.
- В `trino_query_runs` пишется `success` или `failed` с ошибкой.

Если Trino недоступен, возвращается понятная ошибка, run помечается как `failed`, сервис не падает целиком.

## 5. Как работает refresh-all
- Endpoint: `POST /api/pilots/refresh-all`
- Берутся все активные пилоты в `sql`-режиме.
- Обновление выполняется **последовательно**.
- Ошибка одного пилота не останавливает остальные.
- Возвращается summary:
  - `success_count`
  - `failed_count`
  - `errors[]` (pilot_id, pilot_name, error)

## 6. Как добавить новый пилот в ручном режиме

### Через UI
1. Откройте `Пилоты` → `Новый пилот`.
2. Заполните:
   - Название
   - Описание
   - Доходность в год
   - Дополнительная ПШЕ
   - Режим `Manual`
3. Сохраните.
4. В карточке пилота добавьте сотрудников в блоке `Добавить назначение сотрудника`.
5. Если сначала хотите загрузить справочник сотрудников один раз:
   - откройте `Сотрудники` → `Импорт сотрудников CSV`;
   - формат CSV: `cas_id` (или `cas`), `full_name`, `rc`;
   - после импорта в ручных пилотах можно назначать сотрудников по одному `cas`.

### Через API
```bash
curl -X POST http://localhost:8000/api/pilots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pilot Manual X",
    "description": "Ручной пилот",
    "annual_revenue": 25000000,
    "accounting_mode": "manual",
    "additional_pshe_default": 0.2,
    "is_active": true
  }'
```

## 7. Как добавить новый пилот в SQL-режиме

### Через UI
1. `Пилоты` → `Новый пилот`.
2. Выберите режим `SQL`.
3. Заполните блок `Подключение к Trino` (host/port/user/password/catalog/schema/http scheme), если для этого пилота нужны отдельные креды.
4. Вставьте SQL-запрос в редактор.
5. Нажмите `Проверить запрос`.
6. Сохраните пилот.
7. В карточке пилота нажмите `Refresh SQL`.

Если поля подключения в форме оставить пустыми, backend использует общие переменные из `.env` (`TRINO_*`).
Если в SQL пишете полные имена таблиц (`catalog.schema.table`), то `TRINO_CATALOG` и `TRINO_SCHEMA` можно не заполнять.

### Через API
```bash
curl -X POST http://localhost:8000/api/pilots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pilot SQL Y",
    "description": "Пилот на Trino",
    "annual_revenue": 47000000,
    "accounting_mode": "sql",
    "trino_host": "trino.company.local",
    "trino_port": 8080,
    "trino_user": "svc_trino_user",
    "trino_password": "secret",
    "trino_catalog": "hive",
    "trino_schema": "default",
    "trino_http_scheme": "http",
    "sql_query": "SELECT cas, date, hours, load_percent FROM ...",
    "additional_pshe_default": 0,
    "is_active": true
  }'
```

После создания:
```bash
curl -X POST http://localhost:8000/api/pilots/<pilot_id>/refresh
```

## 8. Как передавать базу между коллегами (полу-оффлайн)

### Через UI
1. Откройте раздел `Бэкапы`.
2. Нажмите `Скачать бэкап` — будет выгружен JSON с:
   - пилотами (включая SQL-запросы),
   - сотрудниками,
   - назначениями,
   - недельными метриками,
   - историей запусков SQL.
3. Передайте файл коллеге.
4. На стороне коллеги в разделе `Бэкапы` нажмите `Загрузить бэкап`.
5. Опционально включите `После импорта запустить refresh-all SQL`.

### Через API
```bash
# Экспорт
curl -L http://localhost:8000/api/system/backup/export -o pilot_tracker_backup.json

# Импорт (сразу после импорта запустить sync SQL)
curl -X POST \"http://localhost:8000/api/system/backup/import?run_refresh_all_sql=true\" \\
  -F \"file=@pilot_tracker_backup.json\"
```

## 9. Импорт справочника сотрудников по CAS

### Через UI
1. Откройте страницу `Сотрудники`.
2. Нажмите `Импорт сотрудников CSV`.
3. Загрузите файл с колонками:
   - `cas_id` или `cas` (уникальный идентификатор),
   - `full_name`,
   - `rc`.
4. После импорта открывайте ручной пилот и добавляйте назначения:
   - из выпадающего списка сотрудников,
   - или по одному `cas` (без повторного ввода ФИО/РЦ, если сотрудник уже в справочнике).
5. Для SQL-пилотов можно возвращать только `cas + hours` и дату (`date` или `week_start_date`) — система сама агрегирует по неделям, сматчит сотрудника по `cas` и подтянет профиль из справочника.

### Через API
```bash
curl -X POST http://localhost:8000/api/employees/import-csv \
  -F "file=@employees.csv"
```

## Формулы расчета
- `cost_from_hours = hours * 60 * 23`
- `pshe = hours / WORK_HOURS_PER_WEEK`
- `load_percent = hours / WORK_HOURS_PER_WEEK * 100`
- `cost_from_pshe = pshe * WORK_HOURS_PER_WEEK * 60 * 23`
- `weekly_revenue_estimate = annual_revenue / 52`
- `profitability_estimate = weekly_revenue_estimate - total_cost`

## Seed-данные
`python scripts/seed.py` создаёт:
- 5 пилотов
- 12 сотрудников
- пересечения сотрудников между пилотами
- несколько недель назначения и метрик
- SQL-пилот с примером запроса
- историю запусков SQL (`success` + `failed`)

## Авторизация
JWT в MVP не реализован, но архитектурно API и frontend разделены, поэтому слой авторизации можно добавить отдельным middleware/роутером без переработки доменной логики.
