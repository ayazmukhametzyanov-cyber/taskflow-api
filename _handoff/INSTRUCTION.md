# Как добавить тесты в taskflow-api

В архиве `tests_for_taskflow_api.zip` лежат тесты (unit, БД, интеграционные, e2e), настройка pytest
и тестовая база для Docker. Код приложения менять не нужно.

Нужны: Python 3.12, Docker Desktop (запущенный) и git.

## 1. Подготовка

```bash
git pull
git switch -c add-tests
```

## 2. Положить файлы

Распаковать архив **в корень репозитория** (рядом с `app/`, `alembic/`, `README.md`).
Появятся `tests/`, `pyproject.toml`, `requirements-dev.txt`, `docker-compose.test.yml`.

Два файла архива не копируются, а дописываются в существующие:

- `gitignore_add.txt` - добавить его содержимое в конец `.gitignore`;
- `README_tests_section.md` - добавить его содержимое в конец `README.md`.

Затем эти два файла из корня репозитория удалить (в нём они не нужны).

PowerShell:

```powershell
Get-Content gitignore_add.txt | Add-Content .gitignore
Get-Content README_tests_section.md -Encoding UTF8 | Add-Content README.md -Encoding UTF8
Remove-Item gitignore_add.txt, README_tests_section.md
```

## 3. Запустить тесты

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
docker compose -f docker-compose.test.yml up -d
pytest
```

Ожидаемый результат: `181 passed`, `Total coverage: 100.00%`.
Если порт 5433 занят, поменять его в `docker-compose.test.yml` и задать `TEST_DATABASE_URL`
с тем же портом.

Остановить тестовую базу после прогона: `docker compose -f docker-compose.test.yml down`.

## 4. Закоммитить

```bash
git status
git add pyproject.toml requirements-dev.txt docker-compose.test.yml .gitignore README.md tests
git commit -m "test: pytest, покрытие 100%: unit, db, integration, e2e"
git push -u origin add-tests
```

Проверить в `git status`, что в коммит не попали `.venv/`, `.coverage` и `.env`.
Дальше - открыть Pull Request из ветки `add-tests` или влить ветку в `main`, как принято в курсе.
