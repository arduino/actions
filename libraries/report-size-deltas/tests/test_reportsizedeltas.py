import distutils.dir_util
import json
import pathlib
import tempfile
import unittest.mock
import urllib

import pytest

import reportsizedeltas

reportsizedeltas.set_verbosity(enable_verbosity=False)

test_data_path = pathlib.Path(__file__).resolve().parent.joinpath("data")
report_keys = reportsizedeltas.ReportSizeDeltas.ReportKeys()


def get_reportsizedeltas_object(repository_name="FooOwner/BarRepository",
                                artifact_name="foo-artifact-name",
                                token="foo token"):
    """Return a reportsizedeltas.ReportSizeDeltas object to use in tests.

    Keyword arguments:
    repository_name -- repository owner and name e.g., octocat/Hello-World
    artifact_name -- name of the workflow artifact that contains the memory usage data
    token -- GitHub access token
    """
    return reportsizedeltas.ReportSizeDeltas(repository_name=repository_name, artifact_name=artifact_name, token=token)


def test_set_verbosity():
    with pytest.raises(TypeError):
        reportsizedeltas.set_verbosity(enable_verbosity=2)
    reportsizedeltas.set_verbosity(enable_verbosity=True)
    reportsizedeltas.set_verbosity(enable_verbosity=False)


def test_report_size_deltas(mocker):
    artifact_download_url = "test_artifact_download_url"
    artifact_folder_object = "test_artifact_folder_object"
    sketches_reports = unittest.mock.sentinel.sketches_reports
    report = "foo report"
    json_data = [{"number": 1, "locked": True, "head": {"sha": "foo123", "ref": "asdf"}, "user": {"login": "1234"}},
                 {"number": 2, "locked": False, "head": {"sha": "foo123", "ref": "asdf"}, "user": {"login": "1234"}}]

    report_size_deltas = get_reportsizedeltas_object()

    mocker.patch("reportsizedeltas.ReportSizeDeltas.api_request",
                 autospec=True,
                 return_value={"json_data": json_data,
                               "additional_pages": True,
                               "page_count": 1})
    mocker.patch("reportsizedeltas.ReportSizeDeltas.report_exists", autospec=True, return_value=False)
    mocker.patch("reportsizedeltas.ReportSizeDeltas.get_artifact_download_url_for_sha",
                 autospec=True,
                 return_value=artifact_download_url)
    mocker.patch("reportsizedeltas.ReportSizeDeltas.get_artifact", autospec=True, return_value=artifact_folder_object)
    mocker.patch("reportsizedeltas.ReportSizeDeltas.get_sketches_reports", autospec=True, return_value=sketches_reports)
    mocker.patch("reportsizedeltas.ReportSizeDeltas.generate_report", autospec=True, return_value=report)
    mocker.patch("reportsizedeltas.ReportSizeDeltas.comment_report", autospec=True)

    # Test handling of locked PR
    mocker.resetall()

    report_size_deltas.report_size_deltas()

    report_size_deltas.comment_report.assert_called_once_with(report_size_deltas, pr_number=2, report_markdown=report)

    # Test handling of existing reports
    for pr_data in json_data:
        pr_data["locked"] = False
    reportsizedeltas.ReportSizeDeltas.report_exists.return_value = True
    mocker.resetall()

    report_size_deltas.report_size_deltas()

    report_size_deltas.comment_report.assert_not_called()

    # Test handling of no report artifact
    reportsizedeltas.ReportSizeDeltas.report_exists.return_value = False
    reportsizedeltas.ReportSizeDeltas.get_artifact_download_url_for_sha.return_value = None
    mocker.resetall()

    report_size_deltas.report_size_deltas()

    report_size_deltas.comment_report.assert_not_called()

    # Test handling of old sketches report artifacts
    reportsizedeltas.ReportSizeDeltas.get_artifact_download_url_for_sha.return_value = artifact_download_url
    reportsizedeltas.ReportSizeDeltas.get_sketches_reports.return_value = None
    mocker.resetall()

    report_size_deltas.report_size_deltas()

    report_size_deltas.comment_report.assert_not_called()

    # Test making reports
    reportsizedeltas.ReportSizeDeltas.get_sketches_reports.return_value = sketches_reports
    mocker.resetall()

    report_size_deltas.report_size_deltas()

    report_exists_calls = []
    get_artifact_download_url_for_sha_calls = []
    get_sketches_reports_calls = []
    generate_report_calls = []
    comment_report_calls = []
    for pr_data in json_data:
        report_exists_calls.append(
            unittest.mock.call(report_size_deltas, pr_number=pr_data["number"], pr_head_sha=json_data[0]["head"]["sha"])
        )
        get_artifact_download_url_for_sha_calls.append(
            unittest.mock.call(report_size_deltas,
                               pr_user_login=pr_data["user"]["login"],
                               pr_head_ref=pr_data["head"]["ref"],
                               pr_head_sha=pr_data["head"]["sha"])
        )
        get_sketches_reports_calls.append(
            unittest.mock.call(report_size_deltas, artifact_folder_object=artifact_folder_object)
        )
        generate_report_calls.append(
            unittest.mock.call(report_size_deltas,
                               sketches_reports=sketches_reports,
                               pr_head_sha=pr_data["head"]["sha"],
                               pr_number=pr_data["number"])
        )
        comment_report_calls.append(
            unittest.mock.call(report_size_deltas, pr_number=pr_data["number"], report_markdown=report)
        )
    report_size_deltas.report_exists.assert_has_calls(calls=report_exists_calls)
    report_size_deltas.get_artifact_download_url_for_sha.assert_has_calls(calls=get_artifact_download_url_for_sha_calls)
    report_size_deltas.get_artifact.assert_called_with(report_size_deltas, artifact_download_url=artifact_download_url)
    report_size_deltas.get_sketches_reports.assert_has_calls(calls=get_sketches_reports_calls)
    report_size_deltas.generate_report.assert_has_calls(calls=generate_report_calls)
    report_size_deltas.comment_report.assert_has_calls(calls=comment_report_calls)


def test_report_exists():
    repository_name = "test_name/test_repo"
    pr_number = 42
    pr_head_sha = "foo123"

    report_size_deltas = get_reportsizedeltas_object(repository_name=repository_name)

    json_data = [{"body": "foo123"}, {"body": report_size_deltas.report_key_beginning + pr_head_sha + "foo"}]
    report_size_deltas.api_request = unittest.mock.MagicMock(return_value={"json_data": json_data,
                                                                           "additional_pages": False,
                                                                           "page_count": 1})

    assert report_size_deltas.report_exists(pr_number=pr_number, pr_head_sha=pr_head_sha)

    report_size_deltas.api_request.assert_called_once_with(request="repos/" + repository_name + "/issues/"
                                                                   + str(pr_number) + "/comments",
                                                           page_number=1)

    assert not report_size_deltas.report_exists(pr_number=pr_number, pr_head_sha="asdf")


def test_get_artifact_download_url_for_sha():
    repository_name = "test_name/test_repo"
    pr_user_login = "test_pr_user_login"
    pr_head_ref = "test_pr_head_ref"
    pr_head_sha = "bar123"
    test_artifact_url = "test_artifact_url"
    run_id = "4567"

    report_size_deltas = get_reportsizedeltas_object(repository_name=repository_name)

    json_data = {"workflow_runs": [{"head_sha": "foo123", "id": "1234"}, {"head_sha": pr_head_sha, "id": run_id}]}
    report_size_deltas.api_request = unittest.mock.MagicMock(return_value={"json_data": json_data,
                                                                           "additional_pages": True,
                                                                           "page_count": 3})
    report_size_deltas.get_artifact_download_url_for_run = unittest.mock.MagicMock(return_value=None)

    # No SHA match
    assert report_size_deltas.get_artifact_download_url_for_sha(pr_user_login=pr_user_login,
                                                                pr_head_ref=pr_head_ref,
                                                                pr_head_sha="foosha") is None

    # Test pagination
    request = "repos/" + repository_name + "/actions/runs"
    request_parameters = ("actor=" + pr_user_login + "&branch=" + pr_head_ref + "&event=pull_request&status=completed")
    calls = [unittest.mock.call(request=request, request_parameters=request_parameters, page_number=1),
             unittest.mock.call(request=request, request_parameters=request_parameters, page_number=2),
             unittest.mock.call(request=request, request_parameters=request_parameters, page_number=3)]
    report_size_deltas.api_request.assert_has_calls(calls)

    # SHA match, but no artifact for run
    assert report_size_deltas.get_artifact_download_url_for_sha(pr_user_login=pr_user_login,
                                                                pr_head_ref=pr_head_ref,
                                                                pr_head_sha=pr_head_sha) is None

    report_size_deltas.get_artifact_download_url_for_run = unittest.mock.MagicMock(return_value=test_artifact_url)

    # SHA match, artifact match
    assert test_artifact_url == (
        report_size_deltas.get_artifact_download_url_for_sha(pr_user_login=pr_user_login,
                                                             pr_head_ref=pr_head_ref,
                                                             pr_head_sha=pr_head_sha)
    )

    report_size_deltas.get_artifact_download_url_for_run.assert_called_once_with(run_id=run_id)


def test_get_artifact_download_url_for_run():
    repository_name = "test_name/test_repo"
    artifact_name = "test_artifact_name"
    archive_download_url = "archive_download_url"
    run_id = "1234"

    report_size_deltas = get_reportsizedeltas_object(repository_name=repository_name,
                                                     artifact_name=artifact_name)

    json_data = {"artifacts": [{"name": artifact_name, "archive_download_url": archive_download_url},
                               {"name": "bar123", "archive_download_url": "wrong_artifact_url"}]}
    report_size_deltas.api_request = unittest.mock.MagicMock(return_value={"json_data": json_data,
                                                                           "additional_pages": False,
                                                                           "page_count": 1})

    # Artifact name match
    assert archive_download_url == report_size_deltas.get_artifact_download_url_for_run(run_id=run_id)

    report_size_deltas.api_request.assert_called_once_with(
        request="repos/" + repository_name + "/actions/runs/" + str(run_id)
                + "/artifacts",
        page_number=1)

    json_data = {"artifacts": [{"name": "foo123", "archive_download_url": "test_artifact_url"},
                               {"name": "bar123", "archive_download_url": "wrong_artifact_url"}]}
    report_size_deltas.api_request = unittest.mock.MagicMock(return_value={"json_data": json_data,
                                                                           "additional_pages": False,
                                                                           "page_count": 1})

    # No artifact name match
    assert report_size_deltas.get_artifact_download_url_for_run(run_id=run_id) is None


# # TODO
# def test_get_artifact():

@pytest.mark.parametrize(
    "sketches_reports_path, expected_sketches_reports",
    [
        (test_data_path.joinpath("size-deltas-reports-old"),
         []
         ),
        (
            test_data_path.joinpath("size-deltas-reports-new"),
            [
                {
                    report_keys.commit_hash: "d8fd302",
                    report_keys.commit_url: "https://example.com/foo",
                    report_keys.fqbn: "arduino:avr:leonardo",
                    report_keys.sizes: [
                        {
                            report_keys.delta: {
                                report_keys.absolute: {
                                    report_keys.maximum: -12,
                                    report_keys.minimum: -12
                                }
                            },
                            report_keys.name: "flash"
                        },
                        {
                            report_keys.delta: {
                                report_keys.absolute: {
                                    report_keys.maximum: 0,
                                    report_keys.minimum: 0
                                }
                            },
                            report_keys.name: "RAM for global variables"
                        }
                    ],
                    report_keys.sketch: [
                        {
                            report_keys.compilation_success: True,
                            report_keys.name: "examples/Bar",
                            report_keys.sizes: [
                                {
                                    report_keys.current: {
                                        report_keys.absolute: 3494
                                    },
                                    report_keys.delta: {
                                        report_keys.absolute: "N/A"
                                    },
                                    report_keys.name: "flash",
                                    "previous": {
                                        report_keys.absolute: "N/A"
                                    }
                                },
                                {
                                    report_keys.current: {
                                        report_keys.absolute: 153
                                    },
                                    report_keys.delta: {
                                        report_keys.absolute: "N/A"
                                    },
                                    report_keys.name: "RAM for global variables",
                                    "previous": {
                                        report_keys.absolute: "N/A"
                                    }
                                }
                            ]
                        },
                        {
                            report_keys.compilation_success: True,
                            report_keys.name: "examples/Foo",
                            report_keys.sizes: [
                                {
                                    report_keys.current: {
                                        report_keys.absolute: 3462
                                    },
                                    report_keys.delta: {
                                        report_keys.absolute: -12
                                    },
                                    report_keys.name: "flash",
                                    "previous": {
                                        report_keys.absolute: 3474
                                    }
                                },
                                {
                                    report_keys.current: {
                                        report_keys.absolute: 149
                                    },
                                    report_keys.delta: {
                                        report_keys.absolute: 0
                                    },
                                    report_keys.name: "RAM for global variables",
                                    "previous": {
                                        report_keys.absolute: 149
                                    }
                                }
                            ]
                        }
                    ]
                },
                {
                    report_keys.commit_hash: "d8fd302",
                    report_keys.commit_url: "https://example.com/foo",
                    report_keys.fqbn: "arduino:avr:uno",
                    report_keys.sizes: [
                        {
                            report_keys.delta: {
                                report_keys.absolute: {
                                    report_keys.maximum: -994,
                                    report_keys.minimum: -994
                                }
                            },
                            report_keys.name: "flash"
                        },
                        {
                            report_keys.delta: {
                                report_keys.absolute: {
                                    report_keys.maximum: -175,
                                    report_keys.minimum: -175
                                }
                            },
                            report_keys.name: "RAM for global variables"
                        }
                    ],
                    report_keys.sketch: [
                        {
                            report_keys.compilation_success: True,
                            report_keys.name: "examples/Bar",
                            report_keys.sizes: [
                                {
                                    report_keys.current: {
                                        report_keys.absolute: 1460
                                    },
                                    report_keys.delta: {
                                        report_keys.absolute: "N/A"
                                    },
                                    report_keys.name: "flash",
                                    "previous": {
                                        report_keys.absolute: "N/A"
                                    }
                                },
                                {
                                    report_keys.current: {
                                        report_keys.absolute: 190
                                    },
                                    report_keys.delta: {
                                        report_keys.absolute: "N/A"
                                    },
                                    report_keys.name: "RAM for global variables",
                                    "previous": {
                                        report_keys.absolute: "N/A"
                                    }
                                }
                            ]
                        },
                        {
                            report_keys.compilation_success: True,
                            report_keys.name: "examples/Foo",
                            report_keys.sizes: [
                                {
                                    report_keys.current: {
                                        report_keys.absolute: 444
                                    },
                                    report_keys.delta: {
                                        report_keys.absolute: -994
                                    },
                                    report_keys.name: "flash",
                                    "previous": {
                                        report_keys.absolute: 1438
                                    }
                                },
                                {
                                    report_keys.current: {
                                        report_keys.absolute: 9
                                    },
                                    report_keys.delta: {
                                        report_keys.absolute: -175
                                    },
                                    report_keys.name: "RAM for global variables",
                                    "previous": {
                                        report_keys.absolute: 184
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        )
    ]
)
def test_get_sketches_reports(sketches_reports_path, expected_sketches_reports):
    report_size_deltas = get_reportsizedeltas_object()

    artifact_folder_object = tempfile.TemporaryDirectory(prefix="test_reportsizedeltas-")
    try:
        distutils.dir_util.copy_tree(src=str(sketches_reports_path),
                                     dst=artifact_folder_object.name)
    except Exception:
        artifact_folder_object.cleanup()
        raise
    sketches_reports = report_size_deltas.get_sketches_reports(artifact_folder_object=artifact_folder_object)

    assert sketches_reports == expected_sketches_reports


def test_generate_report():
    sketches_report_path = test_data_path.joinpath("size-deltas-reports-new")
    pr_head_sha = "asdf123"
    pr_number = 42
    expected_deltas_report = (
        "**Memory usage change @[asdf123](https://github.com/FooOwner/BarRepository/pull/42/commits/asdf123)**\n\n"
        "FQBN|flash|RAM for global variables\n"
        "-|-|-\n"
        "arduino:avr:leonardo|:green_heart: -12 - -12|0 - 0\n"
        "arduino:avr:uno|:green_heart: -994 - -994|:green_heart: -175 - -175\n\n"
        "<details>\n"
        "<summary>Click for full report table</summary>\n\n"
        "FQBN|examples/Bar<br>flash|examples/Bar<br>RAM for global variables|examples/Foo<br>flash|examples/Foo<br>RAM "
        "for global variables\n"
        "-|-|-|-|-\n"
        "arduino:avr:leonardo|N/A|N/A|-12|0\n"
        "arduino:avr:uno|N/A|N/A|-994|-175\n\n"
        "</details>\n\n"
        "<details>\n"
        "<summary>Click for full report CSV</summary>\n\n"
        "```\n"
        "FQBN,examples/Bar<br>flash,examples/Bar<br>RAM for global variables,examples/Foo<br>flash,examples/Foo<br>RAM "
        "for global variables\n"
        "arduino:avr:leonardo,N/A,N/A,-12,0\n"
        "arduino:avr:uno,N/A,N/A,-994,-175\n"
        "```\n"
        "</details>"
    )

    report_size_deltas = get_reportsizedeltas_object()

    artifact_folder_object = tempfile.TemporaryDirectory(prefix="test_reportsizedeltas-")
    try:
        distutils.dir_util.copy_tree(src=str(sketches_report_path),
                                     dst=artifact_folder_object.name)
    except Exception:
        artifact_folder_object.cleanup()
        raise
    sketches_reports = report_size_deltas.get_sketches_reports(artifact_folder_object=artifact_folder_object)

    report = report_size_deltas.generate_report(sketches_reports=sketches_reports,
                                                pr_head_sha=pr_head_sha,
                                                pr_number=pr_number)
    assert report == expected_deltas_report


def test_comment_report():
    pr_number = 42
    report_markdown = "test_report_markdown"
    repository_name = "test_user/test_repo"

    report_size_deltas = get_reportsizedeltas_object(repository_name=repository_name)

    report_size_deltas.http_request = unittest.mock.MagicMock()

    report_size_deltas.comment_report(pr_number=pr_number, report_markdown=report_markdown)

    report_data = {"body": report_markdown}
    report_data = json.dumps(obj=report_data)
    report_data = report_data.encode(encoding="utf-8")

    report_size_deltas.http_request.assert_called_once_with(
        url="https://api.github.com/repos/" + repository_name + "/issues/"
            + str(pr_number) + "/comments",
        data=report_data)


def test_api_request():
    response_data = {"json_data": {"foo": "bar"},
                     "additional_pages": False,
                     "page_count": 1}
    request = "test_request"
    request_parameters = "test_parameters"
    page_number = 1

    report_size_deltas = get_reportsizedeltas_object()

    report_size_deltas.get_json_response = unittest.mock.MagicMock(return_value=response_data)

    assert response_data == report_size_deltas.api_request(request=request,
                                                           request_parameters=request_parameters,
                                                           page_number=page_number)
    report_size_deltas.get_json_response.assert_called_once_with(
        url="https://api.github.com/" + request + "?" + request_parameters
            + "&page=" + str(page_number) + "&per_page=100")


def test_get_json_response():
    response = {"headers": {"Link": None}, "body": "[]"}
    url = "test_url"

    report_size_deltas = get_reportsizedeltas_object()

    report_size_deltas.http_request = unittest.mock.MagicMock(return_value=response)

    # Empty body
    response_data = report_size_deltas.get_json_response(url=url)
    assert json.loads(response["body"]) == response_data["json_data"]
    assert not response_data["additional_pages"]
    assert 0 == response_data["page_count"]
    report_size_deltas.http_request.assert_called_once_with(url=url)

    response = {"headers": {"Link": None}, "body": "[42]"}
    report_size_deltas.http_request = unittest.mock.MagicMock(return_value=response)

    # Non-empty body, Link field is None
    response_data = report_size_deltas.get_json_response(url=url)
    assert json.loads(response["body"]) == response_data["json_data"]
    assert not response_data["additional_pages"]
    assert 1 == response_data["page_count"]

    response = {"headers": {"Link": '<https://api.github.com/repositories/919161/pulls?page=2>; rel="next", '
                                    '"<https://api.github.com/repositories/919161/pulls?page=4>; rel="last"'},
                "body": "[42]"}
    report_size_deltas.http_request = unittest.mock.MagicMock(return_value=response)

    # Non-empty body, Link field is populated
    response_data = report_size_deltas.get_json_response(url=url)
    assert json.loads(response["body"]) == response_data["json_data"]
    assert response_data["additional_pages"]
    assert 4 == response_data["page_count"]


def test_http_request():
    url = "test_url"
    data = "test_data"

    report_size_deltas = get_reportsizedeltas_object()

    report_size_deltas.raw_http_request = unittest.mock.MagicMock()

    report_size_deltas.http_request(url=url, data=data)

    report_size_deltas.raw_http_request.assert_called_once_with(url=url, data=data)


def test_raw_http_request():
    user_name = "test_user"
    token = "test_token"
    url = "test_url"
    data = "test_data"
    request = "test_request"

    report_size_deltas = get_reportsizedeltas_object(repository_name=user_name + "/FooRepositoryName",
                                                     token=token)

    urllib.request.Request = unittest.mock.MagicMock(return_value=request)
    report_size_deltas.handle_rate_limiting = unittest.mock.MagicMock()
    urllib.request.urlopen = unittest.mock.MagicMock()

    report_size_deltas.raw_http_request(url=url, data=data)

    urllib.request.Request.assert_called_once_with(url=url,
                                                   headers={"Authorization": "token " + token,
                                                            "User-Agent": user_name},
                                                   data=data)

    # URL != https://api.github.com/rate_limit
    report_size_deltas.handle_rate_limiting.assert_called_once()

    report_size_deltas.handle_rate_limiting.reset_mock()
    urllib.request.urlopen.reset_mock()

    url = "https://api.github.com/rate_limit"
    report_size_deltas.raw_http_request(url=url, data=data)

    # URL == https://api.github.com/rate_limit
    report_size_deltas.handle_rate_limiting.assert_not_called()

    urllib.request.urlopen.assert_called_once_with(url=request)


def test_handle_rate_limiting():
    report_size_deltas = get_reportsizedeltas_object()

    json_data = {"json_data": {"resources": {"core": {"remaining": 0, "reset": 1234, "limit": 42}}}}
    report_size_deltas.get_json_response = unittest.mock.MagicMock(return_value=json_data)

    with pytest.raises(expected_exception=SystemExit, match="0"):
        report_size_deltas.handle_rate_limiting()

    report_size_deltas.get_json_response.assert_called_once_with(url="https://api.github.com/rate_limit")

    json_data["json_data"]["resources"]["core"]["remaining"] = 42
    report_size_deltas.handle_rate_limiting()


@pytest.mark.slow(reason="Causes a delay")
def test_determine_urlopen_retry_true():
    assert reportsizedeltas.determine_urlopen_retry(
        exception=urllib.error.HTTPError(None, 502, "Bad Gateway", None, None))


def test_determine_urlopen_retry_false():
    assert not reportsizedeltas.determine_urlopen_retry(
        exception=urllib.error.HTTPError(None, 404, "Not Found", None, None))


def test_get_page_count():
    page_count = 4
    link_header = ('<https://api.github.com/repositories/919161/pulls?page=2>; rel="next", '
                   '"<https://api.github.com/repositories/919161/pulls?page=' + str(page_count) + '>; rel="last"')

    assert page_count == reportsizedeltas.get_page_count(link_header=link_header)


@pytest.mark.parametrize("minimum, maximum, expected_value",
                         [("N/A", "N/A", "N/A"),
                          (-1, 0, ":green_heart: -1 - 0"),
                          (0, 0, "0 - 0"),
                          (0, 1, ":small_red_triangle: 0 - +1"),
                          (1, 1, ":small_red_triangle: +1 - +1"),
                          (-1, 1, ":grey_question: -1 - +1")])
def test_get_summary_value(minimum, maximum, expected_value):
    assert reportsizedeltas.get_summary_value(minimum=minimum, maximum=maximum) == expected_value


def test_generate_markdown_table():
    assert reportsizedeltas.generate_markdown_table(
        row_list=[["FQBN", "Flash", "RAM"], ["foo:bar:baz", 42, 11]]
    ) == "FQBN|Flash|RAM\n-|-|-\nfoo:bar:baz|42|11\n"


def test_generate_csv_table():
    assert reportsizedeltas.generate_csv_table(row_list=[["FQBN", "Flash", "RAM"], ["foo:bar:baz", 42, 11]]) == (
        "FQBN,Flash,RAM\nfoo:bar:baz,42,11\n"
    )
