# Pilot Resource Tracker: инструкция по сервису

Документ для быстрого онбординга команды: что это за сервис, как его запускать, как работать с пилотами и сотрудниками, как переносить данные между коллегами.

## 1. Что делает сервис

`Pilot Resource Tracker` помогает:
- учитывать загрузку сотрудников по пилотам;
- считать трудозатраты (часы, ПШЕ, % загрузки);
- считать стоимость ресурса и ориентировочную прибыльность пилота;
- видеть пересечения сотрудников между пилотами;
- обновлять SQL-пилоты из Trino;
- переносить конфигурацию и данные через backup JSON.

## 2. Основные понятия

- `ПШЕ` (полная штатная единица): 1 ПШЕ = 40 часов в неделю (по умолчанию).
- `Стоимость минуты`: 23 руб/мин (по умолчанию).
- `manual` пилот: загрузка вводится руками или CSV.
- `sql` пилот: загрузка подтягивается SQL-запросом из Trino.
- `cas_id` (`cas`): уникальный идентификатор сотрудника (главный ключ матчинга).

## 3. Быстрый запуск (рекомендуется через Docker)

1. В корне проекта:
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python scripts/seed.py
```

2. Открыть:
- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

3. Проверка здоровья:
```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:
```json
{"status":"ok"}
```

## 4. Запуск без Docker

### Backend
```bash
cd backend
python3 -m pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
PYTHONPATH=. python scripts/seed.py
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 5. Базовый рабочий процесс

1. Импортируйте справочник сотрудников (`cas_id, full_name, rc`) один раз.
2. Создайте пилот:
- `manual` — если хотите вводить вручную/CSV;
- `sql` — если хотите считать загрузку из Trino.
3. Для `manual`:
- добавляйте назначения вручную или CSV;
- достаточно `cas_id + трудозатраты`, профиль сотрудника подтянется по `cas`.
4. Для `sql`:
- вставьте SQL и (опционально) отдельные Trino-креды в карточке пилота;
- нажмите `Проверить запрос`, затем `Refresh SQL`.
5. Смотрите метрики на Dashboard и в карточках пилотов/сотрудников.

## 6. SQL-пилоты: требования к результату запроса

Минимально SQL должен вернуть:
- `week_start_date`
- `cas` (рекомендуется) **или** пару `full_name + rc`
- `hours`

Опционально:
- `load_percent` (если не вернулся, вычислится автоматически)

Если сотрудник с таким `cas` уже есть в справочнике, сервис подтянет ФИО/РЦ автоматически.

## 7. Перенос данных между коллегами

В разделе `Бэкапы`:
1. `Скачать бэкап` на одной машине.
2. Передать JSON-файл коллеге.
3. `Загрузить бэкап` на другой машине.
4. Опционально включить `run refresh-all SQL` сразу после импорта.

Переносятся:
- пилоты и SQL-запросы,
- сотрудники,
- назначения,
- недельные метрики,
- история SQL-refresh.

## 8. Полезные команды эксплуатации

```bash
# Поднять сервисы
docker compose up --build -d

# Логи backend
docker compose logs -f backend

# Логи frontend
docker compose logs -f frontend

# Применить миграции вручную
docker compose exec backend alembic upgrade head

# Повторно залить seed-данные
docker compose exec backend python scripts/seed.py

# Остановить сервисы
docker compose down
```

## 9. Типовые проблемы и решения

1. `Trino is not configured`
- Заполните `TRINO_*` в `.env` или поля Trino в карточке SQL-пилота.

2. `Employee with CAS ... not found`
- Импортируйте сотрудника в справочник (`Сотрудники -> Импорт CSV`) или добавьте `full_name + rc`.

3. Пустой dashboard после запуска
- Выполните seed:
```bash
docker compose exec backend python scripts/seed.py
```

4. Порт занят (`5173`, `8000`, `5432`)
- Освободите порт или измените маппинг в `docker-compose.yml`.

## 10. Проверка перед демо

1. `docker compose ps` — все сервисы `Up`.
2. `http://localhost:8000/health` — `ok`.
3. На Dashboard есть данные.
4. На странице `Сотрудники` есть справочник.
5. У SQL-пилота работает `Проверить запрос` / `Refresh SQL`.
