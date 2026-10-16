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
