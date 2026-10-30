# TaskFlow API

REST API для управления задачами команды.
Стек: FastAPI, PostgreSQL 16, SQLAlchemy 2, Alembic, Docker Compose.

## Требования

- Docker
- Docker Compose

Локально ставить Python и PostgreSQL не нужно — всё работает в контейнерах.

## Запуск

1. Скопировать пример переменных окружения в рабочий файл:

   ```bash
   cp .env.example .env
   ```

2. Собрать и запустить оба сервиса (API + PostgreSQL):

   ```bash
   docker compose up --build
   ```

3. Дождаться строки в логе:

   ```
   Uvicorn running on http://0.0.0.0:8000
   ```

4. Открыть в браузере:

   - Swagger UI: <http://localhost:8000/docs>
   - Health-check: <http://localhost:8000/health>

Миграции Alembic применяются автоматически при старте контейнера `api`.

## Остановка

Остановить, но сохранить данные в БД:

```bash
docker compose down
```

Полный сброс, включая данные PostgreSQL:

```bash
docker compose down -v
```

## Примеры запросов

### Создать пользователя

```bash
curl -X POST http://localhost:8000/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","display_name":"Alice","role":"admin"}'
```

Ответ — `201 Created` с объектом пользователя.

### Создать проект

```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo","description":"Тестовый проект"}'
```

Ответ — `201 Created`.

### Список задач с фильтром

```bash
curl "http://localhost:8000/v1/tasks?project_id=1&status=open"
```

Ответ — `200 OK` со списком задач проекта 1 в статусе `open`.


## Тесты

```bash
pip install -r requirements-dev.txt
docker compose -f docker-compose.test.yml up -d
pytest
```

Тестам нужен PostgreSQL: адрес берётся из `TEST_DATABASE_URL`, по умолчанию это
`postgresql+psycopg2://taskflow:taskflow@localhost:5433/taskflow_test` (его поднимает
`docker-compose.test.yml`). Базу и схему тесты создают сами, схема накатывается миграциями.
`pytest` падает, если покрытие `app/` и `alembic/` ниже 100%.

| Папка | Что проверяет |
|---|---|
| `tests/unit` | схемы, конфиг, обработка конфликтов, без базы |
| `tests/db` | ограничения, каскады и миграции на настоящем PostgreSQL |
| `tests/integration` | все эндпоинты через `TestClient` с реальной базой |
| `tests/e2e` | сценарии по HTTP к запущенному uvicorn |

Отдельный слой: `pytest -m unit`, `-m db`, `-m integration`, `-m e2e`.

## Тесты

Проект покрыт тестами (unit, db, integration, e2e). Покрытие — 100%.

### Запуск тестов

1. Установить dev-зависимости:
   ```
   pip install -r requirements-dev.txt
   ```
2. Поднять тестовую БД:
   ```
   docker compose -f docker-compose.test.yml up -d
   ```
3. Запустить тесты:
   ```
   pytest
   ```
4. Остановить тестовую БД:
   ```
   docker compose -f docker-compose.test.yml down
   ```