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


@pytest.fixture(autouse=True)
def mock_catalog_url():
    with mock.patch(
        "open_science_catalog_backend.config.RESOURCE_CATALOG_METADATA_URL",
        new="https://catalog.test",
    ):
        yield


@pytest.fixture()
def mock_catalog_response_found(respx_mock):
    respx_mock.get("https://catalog.test").respond(
        json={
            "type": "FeatureCollection",
            "features": [
                {
                    "id": "python-sleeper",
                    "type": "Feature",
                    "associations": [
                        {
                            "href": "https://cwl-server.test",
                            "name": "Python sleeper",
                            "description": "Run a Python sleeper for between min and max seconds randomly",
                            "type": "application/x-yaml",
                            "rel": "application/x-yaml",
                        },
                        {
                            "href": "https://foo.test",
                            "name": "Python sleeper",
                            "description": "Run a Python sleeper for between min and max seconds randomly",
                            "type": "application/x-yaml",
                            "rel": "application/x-yaml",
                        },
                    ],
                }
            ],
        }
    )


@pytest.fixture()
def mock_process_deploy(respx_mock, remote_backend_url):
    respx_mock.post(remote_backend_url + "/processes")


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


@pytest.fixture()
def mock_remote_process_get_found(requests_mock, remote_backend_url):
    return requests_mock.get(
        f"{remote_backend_url}/processes/python-sleeper-0_0_2",
        json={"remote-process-get-result": 3},
    )


@pytest.fixture()
def mock_remote_process_get_not_found(requests_mock, remote_backend_url):
    return requests_mock.get(
        f"{remote_backend_url}/processes/python-sleeper-0_0_2",
        status_code=HTTPStatus.NOT_FOUND,
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


def test_get_process_triggers_deploy(
    client,
    mock_catalog_response_found,
    mock_process_deploy,
    mock_remote_process_get_not_found,
) -> None:
    response = client.get("/processing/mailuefterl/processes/python-sleeper-0_0_2")
    # this is only not found because the mock backend also returns not found after deploy
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_process_doesnt_deploy_again_if_already_deployed(
    client,
    mock_catalog_response_found,
    mock_remote_process_get_found,
) -> None:
    response = client.get("/processing/mailuefterl/processes/python-sleeper-0_0_2")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["remote-process-get-result"] == 3


# TODO: job list
# TODO: process execution
# TODO: process list
