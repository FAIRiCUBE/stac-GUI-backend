from http import HTTPStatus

import pytest
import requests_mock


@pytest.fixture()
def requests_mocker():
    with requests_mock.Mocker() as requests_mocker:
        yield requests_mocker


@pytest.fixture()
def remote_backend_url() -> str:
    return "https://www.example.com"


@pytest.fixture()
def mock_remote_job_status(requests_mocker, remote_backend_url):
    requests_mocker.get(f"{remote_backend_url}/jobs/foo-bar", json={"jobID": 1})


@pytest.fixture()
def mock_remote_job_results(requests_mocker, remote_backend_url):
    requests_mocker.get(
        f"{remote_backend_url}/jobs/foo-bar/results",
        content=b"a",
        headers={"Content-Type": "custom/stuff"},
    )


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
