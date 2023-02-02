from http import HTTPStatus
from unittest import mock

import pytest


@pytest.fixture()
def remote_backend_url() -> str:
    return "https://www.example.com"


@pytest.fixture(autouse=True)
def mock_remote_backend_config(remote_backend_url):
    with mock.patch(
        "open_science_catalog_backend.config.REMOTE_PROCESSING_BACKEND_MAPPING",
        new={"mailuefterl": remote_backend_url},
    ):
        yield


@pytest.fixture()
def mock_remote_job_status(requests_mock, remote_backend_url):
    return requests_mock.get(f"{remote_backend_url}/jobs/foo-bar", json={"jobID": 1})


@pytest.fixture()
def mock_remote_job_results(requests_mock, remote_backend_url):
    return requests_mock.get(
        f"{remote_backend_url}/jobs/foo-bar/results",
        content=b"a",
        headers={"Content-Type": "custom/stuff"},
    )


def test_forwarded_request_sets_host_header(client, mock_remote_job_status):
    client.get("/processing/mailuefterl/jobs/foo-bar")
    assert mock_remote_job_status.last_request.headers["host"] == "www.example.com"


def test_job_status_can_be_fetched(client, mock_remote_job_status):
    response = client.get("/processing/mailuefterl/jobs/foo-bar")

    assert response.status_code == HTTPStatus.OK
    assert "jobID" in response.json()


def test_job_results_can_be_fetched(client, mock_remote_job_results):
    response = client.get("/processing/mailuefterl/jobs/foo-bar/results")

    assert response.status_code == HTTPStatus.OK
    assert response.content == b"a"
    assert response.headers["Content-Type"] == "custom/stuff"


# TODO: job list
# TODO: process description
# TODO: process execution
# TODO: process list
