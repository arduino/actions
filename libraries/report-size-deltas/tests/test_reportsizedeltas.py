import distutils.dir_util
import unittest.mock

from reportsizedeltas import *


# noinspection PyUnresolvedReferences
class TestReportsizedeltas(unittest.TestCase):
    # NOTE: the tests are run in order sorted by method name, not in the order below

    set_verbosity(enable_verbosity=False)

    # @unittest.skip("")
    def test_set_verbosity(self):
        with self.assertRaises(TypeError):
            set_verbosity(enable_verbosity=2)
        set_verbosity(enable_verbosity=True)
        set_verbosity(enable_verbosity=False)

    # @unittest.skip("")
    def test_report_size_deltas(self):
        repository_name = "test_name/test_repo"
        artifact_download_url = "test_artifact_download_url"
        artifact_folder_object = "test_artifact_folder_object"
        report = {"markdown": "test_markdown", "data": "test_data"}

        report_size_deltas = ReportSizeDeltas(repository_name=repository_name, artifact_name="foo", token="foo")

        json_data = [{"number": 1, "locked": True, "head": {"sha": "foo123", "ref": "asdf"}, "user": {"login": "1234"}},
                     {"number": 2, "locked": True, "head": {"sha": "foo123", "ref": "asdf"},
                      "user": {"login": "1234"}}]
        report_size_deltas.api_request = unittest.mock.MagicMock(return_value={"json_data": json_data,
                                                                               "additional_pages": True,
                                                                               "page_count": 1})

        # Test handling of locked PR
        self.assertEqual([], report_size_deltas.report_size_deltas())
        calls = [unittest.mock.call(request="repos/" + repository_name + "/pulls",
                                    page_number=1)]
        report_size_deltas.api_request.assert_has_calls(calls)

        # Test handling of existing reports
        report_size_deltas.report_exists = unittest.mock.MagicMock(return_value=True)

        for pr_data in json_data:
            pr_data["locked"] = False

        self.assertEqual([], report_size_deltas.report_size_deltas())

        calls = []
        for pr_data in json_data:
            calls = calls + [unittest.mock.call(pr_number=pr_data["number"], pr_head_sha=json_data[0]["head"]["sha"])]

        report_size_deltas.report_exists.assert_has_calls(calls)

        # Test handling of no report artifact
        report_size_deltas.report_exists = unittest.mock.MagicMock(return_value=False)

        report_size_deltas.get_artifact_download_url_for_sha = unittest.mock.MagicMock(return_value=None)

        self.assertEqual([], report_size_deltas.report_size_deltas())

        calls = []
        for pr_data in json_data:
            calls = calls + [unittest.mock.call(pr_user_login=pr_data["user"]["login"],
                                                pr_head_ref=pr_data["head"]["ref"],
                                                pr_head_sha=pr_data["head"]["sha"])]

        report_size_deltas.get_artifact_download_url_for_sha.assert_has_calls(calls)

        # Test making reports
        report_size_deltas.get_artifact_download_url_for_sha = unittest.mock.MagicMock(
            return_value=artifact_download_url)

        report_size_deltas.get_artifact = unittest.mock.MagicMock(return_value=artifact_folder_object)

        report_size_deltas.generate_report = unittest.mock.MagicMock(return_value=report)

        report_size_deltas.comment_report = unittest.mock.MagicMock()

        report_list = []
        for pr_data in json_data:
            report_list = report_list + [{"pr_number": pr_data["number"], "report": report["data"]}]
        self.assertEqual(report_list, report_size_deltas.report_size_deltas())

    # @unittest.skip("")
    def test_report_exists(self):
        repository_name = "test_name/test_repo"
        artifact_name = "test_artifact_name"
        pr_number = 42
        pr_head_sha = "foo123"

        report_size_deltas = ReportSizeDeltas(repository_name=repository_name, artifact_name=artifact_name, token="foo")

        json_data = [{"body": "foo123"}, {"body": report_size_deltas.report_key_beginning + pr_head_sha + "foo"}]
        report_size_deltas.api_request = unittest.mock.MagicMock(return_value={"json_data": json_data,
                                                                               "additional_pages": False,
                                                                               "page_count": 1})

        self.assertTrue(report_size_deltas.report_exists(pr_number=pr_number, pr_head_sha=pr_head_sha))

        report_size_deltas.api_request.assert_called_once_with(request="repos/" + repository_name + "/issues/"
                                                                       + str(pr_number) + "/comments",
                                                               page_number=1)

        self.assertFalse(report_size_deltas.report_exists(pr_number=pr_number, pr_head_sha="asdf"))

    # @unittest.skip("")
    def test_get_artifact_download_url_for_sha(self):
        repository_name = "test_name/test_repo"
        pr_user_login = "test_pr_user_login"
        pr_head_ref = "test_pr_head_ref"
        pr_head_sha = "bar123"
        test_artifact_url = "test_artifact_url"
        run_id = "4567"

        report_size_deltas = ReportSizeDeltas(repository_name=repository_name, artifact_name="foo", token="foo")

        json_data = {"workflow_runs": [{"head_sha": "foo123", "id": "1234"}, {"head_sha": pr_head_sha, "id": run_id}]}
        report_size_deltas.api_request = unittest.mock.MagicMock(return_value={"json_data": json_data,
                                                                               "additional_pages": True,
                                                                               "page_count": 3})
        report_size_deltas.get_artifact_download_url_for_run = unittest.mock.MagicMock(return_value=None)

        # No SHA match
        self.assertEqual(None, report_size_deltas.get_artifact_download_url_for_sha(pr_user_login=pr_user_login,
                                                                                    pr_head_ref=pr_head_ref,
                                                                                    pr_head_sha="foosha"))

        # Test pagination
        request = "repos/" + repository_name + "/actions/runs"
        request_parameters = ("actor=" + pr_user_login + "&branch=" + pr_head_ref
                              + "&event=pull_request&status=completed")
        calls = [unittest.mock.call(request=request, request_parameters=request_parameters, page_number=1),
                 unittest.mock.call(request=request, request_parameters=request_parameters, page_number=2),
                 unittest.mock.call(request=request, request_parameters=request_parameters, page_number=3)]
        report_size_deltas.api_request.assert_has_calls(calls)

        # SHA match, but no artifact for run
        self.assertEqual(None, report_size_deltas.get_artifact_download_url_for_sha(pr_user_login=pr_user_login,
                                                                                    pr_head_ref=pr_head_ref,
                                                                                    pr_head_sha=pr_head_sha))

        report_size_deltas.get_artifact_download_url_for_run = unittest.mock.MagicMock(return_value=test_artifact_url)

        # SHA match, artifact match
        self.assertEqual(test_artifact_url,
                         report_size_deltas.get_artifact_download_url_for_sha(pr_user_login=pr_user_login,
                                                                              pr_head_ref=pr_head_ref,
                                                                              pr_head_sha=pr_head_sha))

        report_size_deltas.get_artifact_download_url_for_run.assert_called_once_with(run_id=run_id)

    # @unittest.skip("")
    def test_get_artifact_download_url_for_run(self):
        repository_name = "test_name/test_repo"
        artifact_name = "test_artifact_name"
        archive_download_url = "archive_download_url"
        run_id = "1234"

        report_size_deltas = ReportSizeDeltas(repository_name=repository_name, artifact_name=artifact_name, token="foo")

        json_data = {"artifacts": [{"name": artifact_name, "archive_download_url": archive_download_url},
                                   {"name": "bar123", "archive_download_url": "wrong_artifact_url"}]}
        report_size_deltas.api_request = unittest.mock.MagicMock(return_value={"json_data": json_data,
                                                                               "additional_pages": False,
                                                                               "page_count": 1})

        # Artifact name match
        self.assertEqual(archive_download_url, report_size_deltas.get_artifact_download_url_for_run(run_id=run_id))

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
        self.assertEqual(None, report_size_deltas.get_artifact_download_url_for_run(run_id=run_id))

    # # TODO
    # def test_get_artifact(self):

    # @unittest.skip("")
    def test_generate_report(self):
        pr_head_sha = "asdf123"
        pr_number = 42
        repository_name = "test_user/test_repo"

        report_size_deltas = ReportSizeDeltas(repository_name=repository_name, artifact_name="foo", token="foo")

        artifact_folder_object = tempfile.TemporaryDirectory(prefix="test_reportsizedeltas-")
        try:
            distutils.dir_util.copy_tree(src=os.path.dirname(os.path.realpath(__file__)) + "/data/size-deltas-reports",
                                         dst=artifact_folder_object.name)
        except Exception:
            artifact_folder_object.cleanup()
            raise

        report = report_size_deltas.generate_report(artifact_folder_object=artifact_folder_object,
                                                    pr_head_sha=pr_head_sha, pr_number=pr_number)
        report_markdown = (
                report_size_deltas.report_key_beginning + pr_head_sha
                + "](https://github.com/" + repository_name + "/pull/" + str(pr_number) + "/commits/" + pr_head_sha
                + ")**\n\n"
                "FQBN | Flash Usage | RAM For Global Variables\n"
                "---|---|---\n"
                "adafruit:samd:adafruit_feather_m0 | 0 | N/A\n"
                "arduino:samd:mkrgsm1400 | N/A | N/A\n"
                "arduino:samd:mkrnb1500 | :green_heart: -24 | 0\n"
                "esp8266:esp8266:huzzah | :small_red_triangle: +32 | :small_red_triangle: +16")
        self.assertEqual(report_markdown, report["markdown"])

        report_data = [{'flash': 10580,
                        'flash_delta': 0,
                        'fqbn': 'adafruit:samd:adafruit_feather_m0',
                        'previous_flash': 10580,
                        'previous_ram': 'N/A',
                        'ram': 'N/A',
                        'ram_delta': 'N/A',
                        'sketch': 'examples/ConnectionHandlerDemo'},
                       {'flash': 51636,
                        'flash_delta': 'N/A',
                        'fqbn': 'arduino:samd:mkrgsm1400',
                        'previous_flash': 'N/A',
                        'previous_ram': 'N/A',
                        'ram': 5104,
                        'ram_delta': 'N/A',
                        'sketch': 'examples/ConnectionHandlerDemo'},
                       {'flash': 50940,
                        'flash_delta': -24,
                        'fqbn': 'arduino:samd:mkrnb1500',
                        'previous_flash': 50964,
                        'previous_ram': 5068,
                        'ram': 5068,
                        'ram_delta': 0,
                        'sketch': 'examples/ConnectionHandlerDemo'},
                       {'flash': 274620,
                        'flash_delta': 32,
                        'fqbn': 'esp8266:esp8266:huzzah',
                        'previous_flash': 274588,
                        'previous_ram': 27480,
                        'ram': 27496,
                        'ram_delta': 16,
                        'sketch': 'examples/ConnectionHandlerDemo'}]
        self.assertEqual(report_data, report["data"])

    # @unittest.skip("")
    def test_comment_report(self):
        pr_number = 42
        report_markdown = "test_report_markdown"
        repository_name = "test_user/test_repo"

        report_size_deltas = ReportSizeDeltas(repository_name=repository_name, artifact_name="foo", token="foo")

        report_size_deltas.http_request = unittest.mock.MagicMock()

        report_size_deltas.comment_report(pr_number=pr_number, report_markdown=report_markdown)

        report_data = {"body": report_markdown}
        report_data = json.dumps(obj=report_data)
        report_data = report_data.encode(encoding="utf-8")

        report_size_deltas.http_request.assert_called_once_with(
            url="https://api.github.com/repos/" + repository_name + "/issues/"
                + str(pr_number) + "/comments",
            data=report_data)

    # @unittest.skip("")
    def test_api_request(self):
        response_data = {"json_data": {"foo": "bar"},
                         "additional_pages": False,
                         "page_count": 1}
        request = "test_request"
        request_parameters = "test_parameters"
        page_number = 1

        report_size_deltas = ReportSizeDeltas(repository_name="foo", artifact_name="foo", token="foo")

        report_size_deltas.get_json_response = unittest.mock.MagicMock(return_value=response_data)

        self.assertEqual(response_data, report_size_deltas.api_request(request=request,
                                                                       request_parameters=request_parameters,
                                                                       page_number=page_number))
        report_size_deltas.get_json_response.assert_called_once_with(
            url="https://api.github.com/" + request + "?" + request_parameters
                + "&page=" + str(page_number) + "&per_page=100")

    # @unittest.skip("")
    def test_get_json_response(self):
        response = {"headers": {"Link": None}, "body": "[]"}
        url = "test_url"

        report_size_deltas = ReportSizeDeltas(repository_name="foo", artifact_name="foo", token="foo")

        report_size_deltas.http_request = unittest.mock.MagicMock(return_value=response)

        # Empty body
        response_data = report_size_deltas.get_json_response(url=url)
        self.assertEqual(json.loads(response["body"]), response_data["json_data"])
        self.assertFalse(response_data["additional_pages"])
        self.assertEqual(0, response_data["page_count"])
        report_size_deltas.http_request.assert_called_once_with(url=url)

        response = {"headers": {"Link": None}, "body": "[42]"}
        report_size_deltas.http_request = unittest.mock.MagicMock(return_value=response)

        # Non-empty body, Link field is None
        response_data = report_size_deltas.get_json_response(url=url)
        self.assertEqual(json.loads(response["body"]), response_data["json_data"])
        self.assertFalse(response_data["additional_pages"])
        self.assertEqual(1, response_data["page_count"])

        response = {"headers": {"Link": '<https://api.github.com/repositories/919161/pulls?page=2>; rel="next", '
                                        '"<https://api.github.com/repositories/919161/pulls?page=4>; rel="last"'},
                    "body": "[42]"}
        report_size_deltas.http_request = unittest.mock.MagicMock(return_value=response)

        # Non-empty body, Link field is populated
        response_data = report_size_deltas.get_json_response(url=url)
        self.assertEqual(json.loads(response["body"]), response_data["json_data"])
        self.assertTrue(response_data["additional_pages"])
        self.assertEqual(4, response_data["page_count"])

    # @unittest.skip("")
    def test_http_request(self):
        url = "test_url"
        data = "test_data"

        report_size_deltas = ReportSizeDeltas(repository_name="foo", artifact_name="foo", token="foo")

        report_size_deltas.raw_http_request = unittest.mock.MagicMock()

        report_size_deltas.http_request(url=url, data=data)

        report_size_deltas.raw_http_request.assert_called_once_with(url=url, data=data)

    # @unittest.skip("")
    def test_raw_http_request(self):
        user_name = "test_user"
        repo_name = "test_repo"
        token = "test_token"
        url = "test_url"
        data = "test_data"
        request = "test_request"

        report_size_deltas = ReportSizeDeltas(repository_name=user_name + "/" + repo_name, artifact_name="foo",
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

    # @unittest.skip("")
    def test_handle_rate_limiting(self):
        report_size_deltas = ReportSizeDeltas(repository_name="foo", artifact_name="foo", token="foo")

        json_data = {"json_data": {"resources": {"core": {"remaining": 0, "reset": 1234, "limit": 42}}}}
        report_size_deltas.get_json_response = unittest.mock.MagicMock(return_value=json_data)

        # noinspection PyTypeChecker
        with self.assertRaises(SystemExit) as cm:
            report_size_deltas.handle_rate_limiting()
        self.assertEqual(cm.exception.code, 0)

        report_size_deltas.get_json_response.assert_called_once_with(url="https://api.github.com/rate_limit")

        json_data["json_data"]["resources"]["core"]["remaining"] = 42
        report_size_deltas.handle_rate_limiting()

    @unittest.skip("disabled because it causes a delay")
    def test_determine_urlopen_retry_true(self):
        self.assertTrue(determine_urlopen_retry(exception=urllib.error.HTTPError(None, 502, "Bad Gateway", None, None)))

    # @unittest.skip("")
    def test_determine_urlopen_retry_false(self):
        self.assertFalse(determine_urlopen_retry(exception=urllib.error.HTTPError(None, 404, "Not Found", None, None)))

    # @unittest.skip("")
    def test_generate_value_cell(self):
        self.assertEqual(" | :small_red_triangle: +42", generate_value_cell(42))
        self.assertEqual(" | 0", generate_value_cell(0))
        self.assertEqual(" | :green_heart: -42", generate_value_cell(-42))
        self.assertEqual(" | N/A", generate_value_cell("N/A"))


if __name__ == '__main__':
    unittest.main()
