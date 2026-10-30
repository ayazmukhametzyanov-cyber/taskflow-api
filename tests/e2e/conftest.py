import socket
import threading
import time

import httpx
import pytest
import uvicorn

from app.main import app


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def server(database):
    """Настоящий uvicorn на свободном порту: запросы идут по сети, как у клиента."""
    port = free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    instance = uvicorn.Server(config)
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10
    while not instance.started:
        assert thread.is_alive(), "сервер завершился при запуске"
        assert time.monotonic() < deadline, "сервер не поднялся за 10 секунд"
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    instance.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def http(server, clean_db):
    # trust_env=False: системный прокси не должен перехватывать запросы к localhost
    with httpx.Client(base_url=server, timeout=10, trust_env=False) as client:
        yield client
