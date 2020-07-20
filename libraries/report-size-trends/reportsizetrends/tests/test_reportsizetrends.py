import datetime
import json
import os
import pathlib
import unittest.mock

import google.oauth2
import googleapiclient
import googleapiclient.errors
import pytest

import reportsizetrends


# Stub
class Service:
    _ = 0

    def spreadsheets(self):
        self._ = 42
        return Service()

    def values(self):
        self._ = 42
        return Service()

    def get(self):
        pass

    def update(self):
        pass

    # noinspection PyPep8Naming
    def batchUpdate(self):  # noqa: N802
        pass

    def execute(self):
        pass


reportsizetrends.set_verbosity(enable_verbosity=False)


def get_reportsizetrends_object(fqbn="foo:bar:baz",
                                commit_hash="foohash",
                                commit_url="https://example.com/foo",
                                sketch_reports=None,
                                sketches_report_path="foo-sketches-report-path",
                                google_key_file="foo-key-file",
                                spreadsheet_id="foo-spreadsheet-id",
                                sheet_name="foo-sheet-name",
                                sheet_id="42"):
    # This system is needed to avoid sketches_data having a mutable default argument
    if sketch_reports is None:
        sketch_reports = {
            reportsizetrends.ReportSizeTrends.ReportKeys.sketches: [
                {
                    reportsizetrends.ReportSizeTrends.ReportKeys.name: "FooSketch",
                    reportsizetrends.ReportSizeTrends.ReportKeys.sizes: [
                        {
                            reportsizetrends.ReportSizeTrends.ReportKeys.name: "Foo memory type",
                            reportsizetrends.ReportSizeTrends.ReportKeys.current: {
                                reportsizetrends.ReportSizeTrends.ReportKeys.absolute: 123
                            }
                        }
                    ]
                }
            ]
        }

    sketches_report = {reportsizetrends.ReportSizeTrends.ReportKeys.board: fqbn,
                       reportsizetrends.ReportSizeTrends.ReportKeys.commit_hash: commit_hash,
                       reportsizetrends.ReportSizeTrends.ReportKeys.commit_url: commit_url}

    # Merge the dictionaries
    sketches_report = {**sketches_report, **sketch_reports}

    os.environ["GITHUB_WORKSPACE"] = "/foo/github-workspace"
    with unittest.mock.patch("pathlib.Path.exists", autospec=True, return_value=True):
        with unittest.mock.patch("reportsizetrends.get_sketches_report", autospec=True, return_value=sketches_report):
            with unittest.mock.patch("reportsizetrends.get_service",
                                     autospec=True,
                                     return_value=Service()):
                with unittest.mock.patch("reportsizetrends.ReportSizeTrends.get_sheet_id",
                                         autospec=True,
                                         return_value=sheet_id):
                    report_size_trends_object = reportsizetrends.ReportSizeTrends(
                        sketches_report_path=sketches_report_path,
                        google_key_file=google_key_file,
                        spreadsheet_id=spreadsheet_id,
                        sheet_name=sheet_name)

    return report_size_trends_object


def test_set_verbosity():
    with pytest.raises(TypeError):
        reportsizetrends.set_verbosity(enable_verbosity=2)
    reportsizetrends.set_verbosity(enable_verbosity=True)
    reportsizetrends.set_verbosity(enable_verbosity=False)


def test_main(monkeypatch, mocker):
    sketches_report_path = "foo/sketches_report_path"
    google_key_file = "foo keyfile"
    spreadsheet_id = "foo spreadsheet id"
    sheet_name = "foo sheet name"

    class ReportSizeTrends:
        def report_size_trends(self):
            pass

    monkeypatch.setenv("INPUT_SKETCHES-REPORT-PATH", sketches_report_path)
    monkeypatch.setenv("INPUT_GOOGLE-KEY-FILE", google_key_file)
    monkeypatch.setenv("INPUT_SPREADSHEET-ID", spreadsheet_id)
    monkeypatch.setenv("INPUT_SHEET-NAME", sheet_name)

    mocker.patch("reportsizetrends.ReportSizeTrends", autospec=True, return_value=ReportSizeTrends())
    mocker.patch.object(ReportSizeTrends, "report_size_trends")

    reportsizetrends.main()

    reportsizetrends.ReportSizeTrends.assert_called_once_with(
        sketches_report_path=sketches_report_path,
        google_key_file=google_key_file,
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name)
    ReportSizeTrends.report_size_trends.assert_called_once()


@pytest.mark.parametrize("report_path_exists", [True, False])
def test_reportsizetrends(capsys, monkeypatch, mocker, report_path_exists):
    fqbn = "foo:bar:baz"
    commit_hash = "foohash"
    commit_url = "https://example.com/foo"
    sketch_reports = unittest.mock.sentinel.sketch_reports
    sketches_report = {reportsizetrends.ReportSizeTrends.ReportKeys.board: fqbn,
                       reportsizetrends.ReportSizeTrends.ReportKeys.commit_hash: commit_hash,
                       reportsizetrends.ReportSizeTrends.ReportKeys.commit_url: commit_url,
                       reportsizetrends.ReportSizeTrends.ReportKeys.sketches: sketch_reports}
    sketches_report_path = "foo/sketches-report-path"
    google_key_file = "foo-key-file"
    service = unittest.mock.sentinel.service
    spreadsheet_id = "foo-spreadsheet-id"
    sheet_name = "foo-sheet-name"
    sheet_id = unittest.mock.sentinel.sheet_id

    monkeypatch.setenv("GITHUB_WORKSPACE", "/foo/github-workspace")

    mocker.patch("pathlib.Path.exists", autospec=True, return_value=report_path_exists)
    mocker.patch("reportsizetrends.get_sketches_report", autospec=True, return_value=sketches_report)
    mocker.patch("reportsizetrends.get_service", autospec=True, return_value=service)
    mocker.patch("reportsizetrends.ReportSizeTrends.get_sheet_id", autospec=True, return_value=sheet_id)

    if report_path_exists is False:
        with pytest.raises(expected_exception=SystemExit, match="1"):
            reportsizetrends.ReportSizeTrends(sketches_report_path=sketches_report_path,
                                              google_key_file=google_key_file,
                                              spreadsheet_id=spreadsheet_id,
                                              sheet_name=sheet_name)
        assert capsys.readouterr().out.strip() == ("::error::Sketches report path: " + sketches_report_path
                                                   + " doesn't exist")
    else:
        report_size_trends = reportsizetrends.ReportSizeTrends(sketches_report_path=sketches_report_path,
                                                               google_key_file=google_key_file,
                                                               spreadsheet_id=spreadsheet_id,
                                                               sheet_name=sheet_name)

        reportsizetrends.get_sketches_report.assert_called_once_with(
            sketches_report_path=reportsizetrends.absolute_path(sketches_report_path)
        )
        reportsizetrends.get_service.assert_called_once_with(google_key_file=google_key_file)
        assert report_size_trends.fqbn == fqbn
        assert report_size_trends.commit_hash == commit_hash
        assert report_size_trends.commit_url == commit_url
        assert report_size_trends.sketch_reports == sketch_reports
        assert report_size_trends.service == service
        assert report_size_trends.spreadsheet_id == spreadsheet_id
        assert report_size_trends.sheet_name == sheet_name
        assert report_size_trends.sheet_id == sheet_id


@pytest.mark.parametrize("heading_row_data", [{}, {"values": "foo"}])
def test_report_size_trends(mocker, heading_row_data):
    report_size_trends = get_reportsizetrends_object()

    mocker.patch("reportsizetrends.ReportSizeTrends.get_heading_row_data", autospec=True, return_value=heading_row_data)
    mocker.patch("reportsizetrends.ReportSizeTrends.populate_shared_data_headings", autospec=True)
    mocker.patch("reportsizetrends.ReportSizeTrends.report_size_trend", autospec=True)

    # There will always be at least one call one call of get_heading_row_data()
    get_heading_row_data_calls = [unittest.mock.call()]
    report_size_trend_calls = []
    for sketch_report in report_size_trends.sketch_reports:
        for size_report in sketch_report[reportsizetrends.ReportSizeTrends.ReportKeys.sizes]:
            get_heading_row_data_calls.append(unittest.mock.call())
            report_size_trend_calls.append(unittest.mock.call(report_size_trends,
                                                              heading_row_data=heading_row_data,
                                                              sketch_report=sketch_report,
                                                              size_report=size_report))

    report_size_trends.report_size_trends()

    if "values" not in heading_row_data:
        report_size_trends.populate_shared_data_headings.assert_called_once()
    else:
        report_size_trends.populate_shared_data_headings.assert_not_called()

    report_size_trends.report_size_trend.assert_has_calls(report_size_trend_calls)


def test_get_heading_row_data(mocker):
    spreadsheet_id = "test_spreadsheet_id"
    sheet_name = "test_sheet_name"
    report_size_trends = get_reportsizetrends_object(spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
    request = unittest.mock.sentinel.request
    heading_row_data = "test_heading_row_data"

    mocker.patch.object(Service, "get", return_value=request)
    mocker.patch("reportsizetrends.execute_google_api_request", autospec=True, return_value=heading_row_data)

    assert heading_row_data == report_size_trends.get_heading_row_data()
    spreadsheet_range = (sheet_name + "!" + report_size_trends.heading_row_number + ":"
                         + report_size_trends.heading_row_number)
    Service.get.assert_called_once_with(spreadsheetId=spreadsheet_id, range=spreadsheet_range)
    reportsizetrends.execute_google_api_request.assert_called_once_with(request=request)


@pytest.mark.parametrize("data_column_letter_populated", [False, True])
@pytest.mark.parametrize("current_row_populated", [False, True])
def test_report_size_trend(mocker, data_column_letter_populated, current_row_populated):
    current_row = {"populated": current_row_populated, "number": 42}
    data_column_letter = {"populated": data_column_letter_populated, "letter": "A"}
    heading_row_data = unittest.mock.sentinel.heading_row_data
    report_keys = reportsizetrends.ReportSizeTrends.ReportKeys()

    report_size_trends = get_reportsizetrends_object()

    sketch_report = report_size_trends.sketch_reports[0]
    size_report = sketch_report[report_keys.sizes][0]

    mocker.patch("reportsizetrends.ReportSizeTrends.get_data_column_letter",
                 autospec=True,
                 return_value=data_column_letter)
    mocker.patch("reportsizetrends.ReportSizeTrends.populate_data_column_heading", autospec=True)
    mocker.patch("reportsizetrends.ReportSizeTrends.get_current_row", autospec=True, return_value=current_row)
    mocker.patch("reportsizetrends.ReportSizeTrends.create_row", autospec=True)
    mocker.patch("reportsizetrends.ReportSizeTrends.write_memory_usage_data", autospec=True)

    report_size_trends.report_size_trend(heading_row_data=heading_row_data,
                                         sketch_report=sketch_report,
                                         size_report=size_report)

    if not data_column_letter["populated"]:
        report_size_trends.populate_data_column_heading.assert_called_once_with(
            report_size_trends,
            data_column_letter=data_column_letter["letter"],
            sketch_name=sketch_report[report_keys.name],
            size_name=size_report[report_keys.name]
        )
    else:
        report_size_trends.populate_data_column_heading.assert_not_called()

    report_size_trends.get_current_row.assert_called_once()

    if not current_row["populated"]:
        report_size_trends.create_row.assert_called_once_with(report_size_trends, row_number=current_row["number"])
    else:
        report_size_trends.create_row.assert_not_called()

    report_size_trends.write_memory_usage_data.assert_called_once_with(
        report_size_trends,
        column_letter=data_column_letter["letter"],
        row_number=current_row["number"],
        memory_usage=size_report[report_keys.current][report_keys.absolute]
    )


def test_populate_shared_data_headings(mocker):
    spreadsheet_id = "test_spreadsheet_id"
    sheet_name = "test_sheet_name"
    request = unittest.mock.sentinel.request
    report_size_trends = get_reportsizetrends_object(spreadsheet_id=spreadsheet_id, sheet_name=sheet_name, )

    mocker.patch.object(Service, "update", return_value=request)
    mocker.patch("reportsizetrends.execute_google_api_request", autospec=True)

    report_size_trends.populate_shared_data_headings()
    spreadsheet_range = (
        sheet_name + "!" + report_size_trends.shared_data_first_column_letter
        + report_size_trends.heading_row_number + ":" + report_size_trends.shared_data_last_column_letter
        + report_size_trends.heading_row_number
    )
    Service.update.assert_called_once_with(
        spreadsheetId=spreadsheet_id,
        range=spreadsheet_range,
        valueInputOption="RAW",
        body={"values": json.loads(
            report_size_trends.shared_data_columns_headings_data)}
    )
    reportsizetrends.execute_google_api_request.assert_called_once_with(request=request)


@pytest.mark.parametrize("size_name, expected_populated, expected_letter",
                         [("bar size name", False, "C"),
                          ("foo size name", True, "B")])
def test_get_data_column_letter(size_name, expected_populated, expected_letter):
    fqbn = "test_fqbn"
    sketch_name = "foo/SketchName"
    heading_row_data_size_name = "foo size name"

    report_size_trends = get_reportsizetrends_object(fqbn=fqbn)
    heading_row_data = {"values": [["foo",
                                    report_size_trends.fqbn + "\n"
                                    + sketch_name + "\n"
                                    + heading_row_data_size_name]]}
    column_letter = report_size_trends.get_data_column_letter(heading_row_data=heading_row_data,
                                                              sketch_name=sketch_name,
                                                              size_name=size_name)
    assert column_letter["populated"] is expected_populated
    assert expected_letter == column_letter["letter"]


def test_populate_data_column_heading(mocker):
    spreadsheet_id = "test_spreadsheet_id"
    sheet_name = "test_sheet_name"
    fqbn = "test_fqbn"
    report_size_trends = get_reportsizetrends_object(spreadsheet_id=spreadsheet_id, sheet_name=sheet_name, fqbn=fqbn)

    request = unittest.mock.sentinel.request
    data_column_letter = "A"
    sketch_name = "foo/SketchName"
    size_name = "foo size name"

    mocker.patch("reportsizetrends.ReportSizeTrends.expand_sheet", autospec=True)
    mocker.patch.object(Service, "update", return_value=request)
    mocker.patch("reportsizetrends.execute_google_api_request", autospec=True)

    report_size_trends.populate_data_column_heading(data_column_letter=data_column_letter,
                                                    sketch_name=sketch_name,
                                                    size_name=size_name)
    spreadsheet_range = (sheet_name + "!" + data_column_letter + report_size_trends.heading_row_number + ":"
                         + data_column_letter + report_size_trends.heading_row_number)
    data_heading_data = ("[[\"" + report_size_trends.fqbn + "\\n" + sketch_name + "\\n" + size_name + "\"]]")
    report_size_trends.expand_sheet.assert_called_once_with(report_size_trends, dimension="COLUMNS")
    Service.update.assert_called_once_with(spreadsheetId=spreadsheet_id,
                                           range=spreadsheet_range,
                                           valueInputOption="RAW",
                                           body={"values": json.loads(data_heading_data)})
    reportsizetrends.execute_google_api_request.assert_called_once_with(request=request)


def test_expand_sheet(mocker):
    spreadsheet_id = unittest.mock.sentinel.spreadsheet_id
    sheet_id = unittest.mock.sentinel.sheet_id
    dimension = unittest.mock.sentinel.dimension

    report_size_trends = get_reportsizetrends_object(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)

    request = unittest.mock.sentinel.request

    mocker.patch.object(Service, "batchUpdate", return_value=request)
    mocker.patch("reportsizetrends.execute_google_api_request", autospec=True)

    report_size_trends.expand_sheet(dimension=dimension)

    Service.batchUpdate.assert_called_once_with(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "appendDimension": {
                        "sheetId": sheet_id,
                        "dimension": dimension,
                        "length": 1
                    }
                }
            ]
        }
    )
    reportsizetrends.execute_google_api_request.assert_called_once_with(request=request)


@pytest.mark.parametrize("spreadsheet_object_sheets, expected_sheet_id",
                         [([{"properties": {"title": "SheetName", "sheetId": 42}}], 42),
                          ([{"properties": {"title": "NotSheetName", "sheetId": 42}}], None)])
def test_get_sheet_id(mocker, spreadsheet_object_sheets, expected_sheet_id):
    spreadsheet_id = unittest.mock.sentinel.spreadsheet_id
    sheet_name = "SheetName"

    report_size_trends = get_reportsizetrends_object(spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)

    request = unittest.mock.sentinel.request

    mocker.patch.object(Service, "get", return_value=request)
    mocker.patch("reportsizetrends.execute_google_api_request",
                 autospec=True,
                 return_value={"sheets": spreadsheet_object_sheets})

    if expected_sheet_id is None:
        with pytest.raises(expected_exception=SystemExit, match="1"):
            report_size_trends.get_sheet_id()
    else:
        assert report_size_trends.get_sheet_id() == expected_sheet_id

    Service.get.assert_called_once_with(spreadsheetId=spreadsheet_id)
    reportsizetrends.execute_google_api_request.assert_called_once_with(request=request)


def test_get_current_row(mocker):
    spreadsheet_id = "test_spreadsheet_id"
    sheet_name = "test_sheet_name"
    commit_hash = "test_commit_hash"
    report_size_trends = get_reportsizetrends_object(spreadsheet_id=spreadsheet_id,
                                                     sheet_name=sheet_name,
                                                     commit_hash=commit_hash)

    request = unittest.mock.sentinel.request

    mocker.patch.object(Service, "get", return_value=request)
    mocker.patch("reportsizetrends.execute_google_api_request",
                 autospec=True,
                 return_value={"values": [["foo"], [commit_hash]]})

    assert {"populated": True, "number": 2} == report_size_trends.get_current_row()
    spreadsheet_range = (sheet_name + "!" + report_size_trends.commit_hash_column_letter + ":"
                         + report_size_trends.commit_hash_column_letter)
    Service.get.assert_called_once_with(spreadsheetId=spreadsheet_id, range=spreadsheet_range)
    reportsizetrends.execute_google_api_request.assert_called_once_with(request=request)
    reportsizetrends.execute_google_api_request.return_value = {"values": [["foo"], ["bar"]]}
    assert {"populated": False, "number": 3} == report_size_trends.get_current_row()


def test_create_row(mocker):
    spreadsheet_id = "test_spreadsheet_id"
    sheet_name = "test_sheet_name"
    commit_url = "test_commit_url"
    report_size_trends = get_reportsizetrends_object(spreadsheet_id=spreadsheet_id,
                                                     sheet_name=sheet_name,
                                                     commit_url=commit_url)
    request = unittest.mock.sentinel.request
    row_number = 42

    mocker.patch("reportsizetrends.ReportSizeTrends.expand_sheet", autospec=True)
    mocker.patch.object(Service, "update", return_value=request)
    mocker.patch("reportsizetrends.execute_google_api_request", autospec=True)

    report_size_trends.create_row(row_number=row_number)
    spreadsheet_range = (sheet_name + "!" + report_size_trends.shared_data_first_column_letter + str(row_number)
                         + ":" + report_size_trends.shared_data_last_column_letter + str(row_number))
    shared_data_columns_data = ("[[\"" + '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
                                + "\",\"=HYPERLINK(\\\"" + commit_url
                                + "\\\",T(\\\"" + report_size_trends.commit_hash + "\\\"))\"]]")
    report_size_trends.expand_sheet.assert_called_once_with(report_size_trends, dimension="ROWS")
    Service.update.assert_called_once_with(spreadsheetId=spreadsheet_id,
                                           range=spreadsheet_range,
                                           valueInputOption="USER_ENTERED",
                                           body={"values": json.loads(shared_data_columns_data)})
    reportsizetrends.execute_google_api_request.assert_called_once_with(request=request)


@pytest.mark.parametrize("memory_usage", [11, "N/A"])
def test_write_memory_usage_data(mocker, memory_usage):
    spreadsheet_id = "test_spreadsheet_id"
    sheet_name = "test_sheet_name"
    report_size_trends = get_reportsizetrends_object(spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)

    request = unittest.mock.sentinel.request
    column_letter = "A"
    row_number = 42

    mocker.patch.object(Service, "update", return_value=request)
    mocker.patch("reportsizetrends.execute_google_api_request", autospec=True)

    report_size_trends.write_memory_usage_data(column_letter=column_letter,
                                               row_number=row_number,
                                               memory_usage=memory_usage)
    spreadsheet_range = (sheet_name + "!" + column_letter + str(row_number) + ":"
                         + column_letter + str(row_number))
    if type(memory_usage) is str:
        memory_usage = "\"" + memory_usage + "\""
    size_data = "[[" + str(memory_usage) + "]]"
    Service.update.assert_called_once_with(spreadsheetId=spreadsheet_id,
                                           range=spreadsheet_range,
                                           valueInputOption="RAW",
                                           body={"values": json.loads(size_data)})
    reportsizetrends.execute_google_api_request.assert_called_once_with(request=request)


def test_get_sketches_report():
    sketches_report_path = pathlib.Path(__file__).resolve().parent.joinpath("testdata", "sketches-report")
    sketches_report = reportsizetrends.get_sketches_report(sketches_report_path=sketches_report_path)
    assert sketches_report == {
        "fqbn": "foo:bar:baz",
        "commit_hash": "foohash",
        "commit_url": "https://example.com/foo",
        "sketch": "FooSketch",
        "flash": 123,
        "ram": 42
    }


@pytest.mark.parametrize("path, expected_absolute_path", [("/asdf", "/asdf"), ("asdf", "/fooWorkspace/asdf")])
def test_absolute_path(monkeypatch, path, expected_absolute_path):
    monkeypatch.setenv("GITHUB_WORKSPACE", "/fooWorkspace")

    assert reportsizetrends.absolute_path(path=path) == pathlib.Path(expected_absolute_path).resolve()
    assert reportsizetrends.absolute_path(path=pathlib.Path(path)) == pathlib.Path(expected_absolute_path).resolve()


def test_get_service(mocker):
    google_key_file = unittest.mock.sentinel.google_key_file
    info = unittest.mock.sentinel.info
    credentials = unittest.mock.sentinel.credentials
    service = unittest.mock.sentinel.service

    mocker.patch("json.loads", autospec=True, return_value=info)
    mocker.patch("google.oauth2.service_account.Credentials.from_service_account_info", autospec=True,
                 return_value=credentials)
    mocker.patch("googleapiclient.discovery.build", autospec=True, return_value=service)

    assert reportsizetrends.get_service(google_key_file) == service

    json.loads.assert_called_once_with(google_key_file, strict=False)
    google.oauth2.service_account.Credentials.from_service_account_info.assert_called_once_with(
        info=info, scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    googleapiclient.discovery.build.assert_called_once_with(serviceName='sheets', version='v4', credentials=credentials)


def test_execute_google_api_request(mocker):
    response = unittest.mock.sentinel.response

    # Test successful request
    mocker.patch("test_reportsizetrends.Service.execute", return_value=response)

    request = Service()

    assert reportsizetrends.execute_google_api_request(request=request) == response
    request.execute.assert_called_once()

    # Test non-recoverable request exception
    mocker.resetall()
    request.execute.side_effect = Exception()
    mocker.patch("reportsizetrends.determine_request_retry", autospec=True, return_value=False)

    with pytest.raises(expected_exception=Exception):
        reportsizetrends.execute_google_api_request(request=request)

    # Test recoverable request exception, but retry attempts exceeded
    mocker.resetall()
    reportsizetrends.determine_request_retry.return_value = True

    with pytest.raises(expected_exception=Exception):
        reportsizetrends.execute_google_api_request(request=request)

    service_execute_calls = []
    maximum_request_attempts = 3
    for _ in range(0, maximum_request_attempts):
        service_execute_calls.append(unittest.mock.call())
    request.execute.assert_has_calls(calls=service_execute_calls)


@pytest.mark.parametrize("http_error, expected_retry", [(429, True), (42, False)])
def test_determine_request_retry(mocker, http_error, expected_retry):
    class Response:
        reason = "foo reason"
        status = http_error

    mocker.patch("time.sleep", autospec=True)
    assert reportsizetrends.determine_request_retry(
        exception=googleapiclient.errors.HttpError(resp=Response(), content=bytes(b""))
    ) == expected_retry


@pytest.mark.parametrize("column_number, expected_column_letter", [(1, "A"), (27, "AA")])
def test_get_spreadsheet_column_letters_from_number(column_number, expected_column_letter):
    assert reportsizetrends.get_spreadsheet_column_letters_from_number(
        column_number=column_number) == expected_column_letter
