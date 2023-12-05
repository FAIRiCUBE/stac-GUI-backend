from fastapi.testclient import TestClient
import pytest

from fairicube_catalog_backend import app


@pytest.fixture
def client():
    return TestClient(app)
