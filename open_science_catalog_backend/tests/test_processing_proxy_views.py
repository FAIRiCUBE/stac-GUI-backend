from http import HTTPStatus
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def mock_remote_backend_config():
    with mock.patch(
        "open_science_catalog_backend.config.REMOTE_PROCESSING_BACKEND_MAPPING",
        new={"mailuefterl": "https://remote-backend.test"},
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
            "id": "python-sleeper",
            "type": "Feature",
            "properties": {
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
            },
        }
    )


@pytest.fixture()
def mock_cwl_server(respx_mock):
    respx_mock.get("https://cwl-server.test").respond(
        content="""#!/usr/bin/env cwl-runner
$graph:

- class: Workflow
  doc: Run a Python sleeper for between min and max seconds randomly
  id: python-sleeper
  inputs:
    min_sleep_seconds:
      doc: Min sleeping seconds
      label: Min sleeping seconds
      type: string
    max_sleep_seconds:
      doc: Max sleeping seconds
      label: Max sleeping seconds
      type: string
    ignored_product:
      doc: Ignored product
      label: Product
      type: Directory
  label: Python sleeper
  outputs:
  - id: sleeper_output
    type: Directory
    outputSource:
    - sleeper/log_output
    """
    )


@pytest.fixture()
def mock_process_deploy(respx_mock):
    respx_mock.post("https://remote-backend.test/processes").respond(
        headers={
            "Location": "/osc/wps3/processes/python-sleeper-0_0_2",
        }
    )


@pytest.fixture()
def mock_remote_job_status(requests_mock):
    return requests_mock.get(
        "https://remote-backend.test/jobs/foo-bar", json={"jobID": 1}
    )


@pytest.fixture()
def mock_remote_job_results(requests_mock):
    return requests_mock.get(
        "https://remote-backend.test/jobs/foo-bar/results",
        content=b"a",
        headers={"Content-Type": "custom/stuff"},
    )


@pytest.fixture()
def mock_remote_process_get_found(requests_mock):
    return requests_mock.get(
        "https://remote-backend.test/processes/python-sleeper-0_0_2",
        json={"remote-process-get-result": 3},
    )


@pytest.fixture()
def mock_remote_process_execute(requests_mock):
    return requests_mock.post(
        "https://remote-backend.test/processes/python-sleeper-0_0_2/execution",
        json={"remote-process-post-result": 5},
    )


def test_forwarded_request_sets_host_header(client, mock_remote_job_status):
    client.get("/processing/mailuefterl/jobs/foo-bar")
    assert mock_remote_job_status.last_request.headers["host"] == "remote-backend.test"


def test_job_status_can_be_fetched(client, mock_remote_job_status):
    response = client.get("/processing/mailuefterl/jobs/foo-bar")

    assert response.status_code == HTTPStatus.OK
    assert "jobID" in response.json()


def test_job_results_can_be_fetched(client, mock_remote_job_results):
    response = client.get("/processing/mailuefterl/jobs/foo-bar/results")

    assert response.status_code == HTTPStatus.OK
    assert response.content == b"a"
    assert response.headers["Content-Type"] == "custom/stuff"


def test_execute_process_also_deploys(
    client,
    mock_catalog_response_found,
    mock_process_deploy,
    mock_remote_process_execute,
) -> None:
    response = client.post(
        "/processing/mailuefterl/processes/python-sleeper/execution",
        headers={"X-User-ID": "abc"},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["remote-process-post-result"] == 5


def test_get_applications_view_forwards_from_catalog(
    client,
    mock_catalog_response_found,
    mock_cwl_server,
) -> None:
    response = client.get("/applications/python-sleeper")
    assert response.status_code == HTTPStatus.OK
    response.json()["$graph"][0]["id"] == "python-sleeper"
