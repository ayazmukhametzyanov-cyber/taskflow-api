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
