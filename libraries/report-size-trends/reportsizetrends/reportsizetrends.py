import datetime
import json
import logging
import os
import pathlib
import sys
import time

from google.oauth2 import service_account
from googleapiclient import discovery

# import httplib2
# httplib2.debuglevel = 4

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)
logger_level = logging.WARNING


def main():
    report_size_trends = ReportSizeTrends(sketches_report_path=os.environ["INPUT_SKETCHES-REPORT-PATH"],
                                          google_key_file=os.environ["INPUT_GOOGLE-KEY-FILE"],
                                          spreadsheet_id=os.environ["INPUT_SPREADSHEET-ID"],
                                          sheet_name=os.environ["INPUT_SHEET-NAME"])

    report_size_trends.report_size_trends()


def set_verbosity(enable_verbosity):
    """Turn debug output on or off.

    Keyword arguments:
    enable_verbosity -- this will generally be controlled via the script's --verbose command line argument
                              (True, False)
    """
    # DEBUG: automatically generated output and all higher log level output
    # INFO: manually specified output and all higher log level output
    verbose_logging_level = logging.DEBUG

    if type(enable_verbosity) is not bool:
        raise TypeError
    if enable_verbosity:
        logger.setLevel(level=verbose_logging_level)
    else:
        logger.setLevel(level=logging.WARNING)


class ReportSizeTrends:
    """Methods for reporting memory usage to a Google Sheets spreadsheet

    Keyword arguments:
    sketches_report_path -- path of the folder containing the sketches report. Relative paths are assumed to be relative
                            to the workspace.
    google_key_file -- Google key file that gives write access to the Google Sheets API
    spreadsheet_id -- ID of the spreadsheet
    sheet_name -- name of the spreadsheet's sheet to use for the report
    """
    heading_row_number = "1"
    timestamp_column_letter = "A"
    timestamp_column_heading = "Commit Timestamp"
    commit_hash_column_letter = "B"
    commit_hash_column_heading = "Commit Hash"
    shared_data_first_column_letter = timestamp_column_letter
    shared_data_last_column_letter = commit_hash_column_letter
    shared_data_columns_headings_data = (
        "[[\"" + timestamp_column_heading + "\",\"" + commit_hash_column_heading + "\"]]"
    )

    # These are appended to the FQBN as the size data column headings
    flash_heading_indicator = " flash"
    ram_heading_indicator = " RAM"

    class ReportKeys:
        boards = "boards"
        board = "board"
        commit_hash = "commit_hash"
        commit_url = "commit_url"
        sizes = "sizes"
        name = "name"
        absolute = "absolute"
        current = "current"
        sketches = "sketches"

    def __init__(self, sketches_report_path, google_key_file, spreadsheet_id, sheet_name):
        absolute_sketches_report_path = absolute_path(sketches_report_path)
        if not absolute_sketches_report_path.exists():
            print("::error::Sketches report path:", sketches_report_path, "doesn't exist")
            sys.exit(1)
        # load the data from the sketches report
        sketches_report = get_sketches_report(sketches_report_path=absolute_sketches_report_path)
        self.commit_hash = sketches_report[self.ReportKeys.commit_hash]
        self.commit_url = sketches_report[self.ReportKeys.commit_url]
        self.board_reports = sketches_report[self.ReportKeys.boards]

        self.service = get_service(google_key_file=google_key_file)
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.sheet_id = self.get_sheet_id()

    def report_size_trends(self):
        """Add memory usage data to a Google Sheets spreadsheet"""
        heading_row_data = self.get_heading_row_data()

        if ("values" in heading_row_data) is False:
            # Fresh sheet, so fill in the shared data headings
            print("Initializing empty sheet")
            self.populate_shared_data_headings()

        for board_report in self.board_reports:
            fqbn = board_report[self.ReportKeys.board]

            print("::debug::Reporting for board:", fqbn)

            for sketch_report in board_report[self.ReportKeys.sketches]:
                print("::debug::Reporting for sketch:", sketch_report[self.ReportKeys.name])
                for size_report in sketch_report[self.ReportKeys.sizes]:
                    print("::debug::Reporting for memory type:", size_report[self.ReportKeys.name])
                    # Update the heading row data so it will reflect the changes made in each iteration
                    heading_row_data = self.get_heading_row_data()

                    self.report_size_trend(heading_row_data=heading_row_data, fqbn=fqbn, sketch_report=sketch_report,
                                           size_report=size_report)

    def get_heading_row_data(self):
        """Return the contents of the heading row"""
        spreadsheet_range = self.sheet_name + "!" + self.heading_row_number + ":" + self.heading_row_number
        request = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=spreadsheet_range)
        response = execute_google_api_request(request=request)
        logger.debug("heading_row_data: ")
        logger.debug(response)
        return response

    def report_size_trend(self, heading_row_data, fqbn, sketch_report, size_report):
        """Add data for a single FQBN, sketch, and memory type to the sheet."""
        data_column_letter = get_data_column_letter(heading_row_data=heading_row_data,
                                                    fqbn=fqbn,
                                                    sketch_name=sketch_report[self.ReportKeys.name],
                                                    size_name=size_report[self.ReportKeys.name])

        if not data_column_letter["populated"]:
            # Columns don't exist for this board, sketch, memory type yet, so create them

            print("::debug::Report column doesn't already exist, adding it")
            self.populate_data_column_heading(data_column_letter=data_column_letter["letter"],
                                              fqbn=fqbn,
                                              sketch_name=sketch_report[self.ReportKeys.name],
                                              size_name=size_report[self.ReportKeys.name])

        current_row = self.get_current_row()

        if not current_row["populated"]:
            # A row doesn't exist for this commit yet, so create one
            self.create_row(row_number=current_row["number"])

        self.write_memory_usage_data(
            column_letter=data_column_letter["letter"],
            row_number=current_row["number"],
            memory_usage=size_report[self.ReportKeys.current][self.ReportKeys.absolute]
        )

    def populate_shared_data_headings(self):
        """Add the headings to the shared data columns (timestamp, commit)"""
        spreadsheet_range = (
            self.sheet_name + "!" + self.shared_data_first_column_letter + self.heading_row_number + ":"
            + self.shared_data_last_column_letter + self.heading_row_number)
        request = self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id,
                                                              range=spreadsheet_range,
                                                              valueInputOption="RAW",
                                                              body={"values": json.loads(
                                                                  self.shared_data_columns_headings_data)})
        response = execute_google_api_request(request=request)
        logger.debug(response)

    def populate_data_column_heading(self, data_column_letter, fqbn, sketch_name, size_name):
        """Add the heading to the specified data column.

        Keyword arguments:
        data_column_letter -- letter of the data column to populate
        sketch_name -- the sketch path
        size_name -- the name of the memory type
        """
        logger.info("No data columns found for " + fqbn + ", " + sketch_name + ", " + size_name
                    + ". Adding column heading at column " + data_column_letter)

        # Append a column to the sheet to make sure there is space for the new column
        self.expand_sheet(dimension="COLUMNS")

        # Add the column heading
        spreadsheet_range = (self.sheet_name + "!" + data_column_letter + self.heading_row_number + ":"
                             + data_column_letter + self.heading_row_number)
        data_heading_data = ("[[\"" + fqbn + "\\n" + sketch_name + "\\n" + size_name + "\"]]")
        request = self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id,
                                                              range=spreadsheet_range,
                                                              valueInputOption="RAW",
                                                              body={"values": json.loads(data_heading_data)})
        response = execute_google_api_request(request=request)
        logger.debug(response)

    def expand_sheet(self, dimension):
        """A new sheet provides a limited number of columns and rows, so it's necessary to expand the size of the sheet.

        Keyword arguments:
        dimension -- whether to add a column or a row ("COLUMNS", "ROWS")
        """
        append_request_body = {
            "requests": [
                {
                    "appendDimension": {
                        "sheetId": self.sheet_id,
                        "dimension": dimension,
                        "length": 1
                    }
                }
            ]
        }
        request = self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=append_request_body)
        response = execute_google_api_request(request=request)
        logger.debug(response)

    def get_sheet_id(self):
        """While the sheet name is used in the A1 notation used in update value Google Sheets API requests, other
        requests require the sheet ID. Given a spreadsheet ID and sheet name, the sheet ID may be determined from the
        Google Sheets API.
        """
        sheet_id = None
        request = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id)
        spreadsheet_object = execute_google_api_request(request=request)
        for sheet in spreadsheet_object["sheets"]:
            if sheet["properties"]["title"] == self.sheet_name:
                sheet_id = sheet["properties"]["sheetId"]
                break

        if sheet_id is None:
            print("::error::Spreadsheet ID:",
                  self.spreadsheet_id,
                  "does not contain the sheet name:",
                  self.sheet_name,
                  "provided via the sheet-name input.")
            sys.exit(1)
        else:
            return sheet_id

    def get_current_row(self):
        """Return a dictionary for the current row:
        populated -- whether the shared data has already been added to the row
        number -- the row number
        """
        spreadsheet_range = (self.sheet_name + "!" + self.commit_hash_column_letter + ":"
                             + self.commit_hash_column_letter)
        request = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id,
                                                           range=spreadsheet_range)
        commit_hash_column_data = execute_google_api_request(request=request)
        logger.debug(commit_hash_column_data)

        populated = False
        index = 0
        for index, cell_text in enumerate(commit_hash_column_data["values"], start=1):
            if cell_text[0] == self.commit_hash:
                populated = True
                break

        if not populated:
            index += 1

        logger.info("Current row number: " + str(index))
        return {"populated": populated, "number": index}

    def create_row(self, row_number):
        """Add the shared data to the row

        Keyword arguments:
        row_number -- spreadsheet row number to create
        """
        logger.info("No row found for the commit hash: " + self.commit_hash + ". Creating a new row #"
                    + str(row_number))
        # Append a row to make sure there is space in the sheet for the new row
        # Append a column to the sheet to make sure there is space for the new column
        self.expand_sheet(dimension="ROWS")

        # Write the data to the row
        spreadsheet_range = (self.sheet_name + "!" + self.shared_data_first_column_letter + str(row_number)
                             + ":" + self.shared_data_last_column_letter + str(row_number))
        shared_data_columns_data = ("[[\"" + "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())
                                    + "\",\"=HYPERLINK(\\\"" + self.commit_url + "\\\",T(\\\""
                                    + self.commit_hash + "\\\"))\"]]")
        request = self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id,
                                                              range=spreadsheet_range,
                                                              valueInputOption="USER_ENTERED",
                                                              body={"values": json.loads(shared_data_columns_data)})
        response = execute_google_api_request(request=request)
        logger.debug(response)

    def write_memory_usage_data(self, column_letter, row_number, memory_usage):
        """Write memory usage data to the specified cell of the spreadsheet.

        Keyword arguments:
        column_letter -- letter of the column containing memory usage data for the board, sketch, memory type
        row_number -- number of the row to write to
        memory_usage -- memory usage
        """
        print("::debug::Writing memory usage value:", memory_usage)
        if type(memory_usage) is str:
            # The memory usage value may be "N/A". If so, it must be quoted so it can be made into valid JSON for the
            # Google Sheets API request
            memory_usage = "\"" + memory_usage + "\""

        spreadsheet_range = (self.sheet_name + "!" + column_letter + str(row_number) + ":"
                             + column_letter + str(row_number))
        size_data = "[[" + str(memory_usage) + "]]"
        request = self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id,
                                                              range=spreadsheet_range,
                                                              valueInputOption="RAW",
                                                              body={"values": json.loads(size_data)})
        response = execute_google_api_request(request=request)
        logger.debug(response)


def absolute_path(path):
    """Returns the absolute path equivalent. Relative paths are assumed to be relative to the workspace of the action's
    Docker container (the root of the repository).

    Keyword arguments:
    path -- the path to make absolute
    """
    path = pathlib.Path(path)
    if not path.is_absolute():
        # path is relative
        path = pathlib.Path(os.environ["GITHUB_WORKSPACE"], path)

    return path.resolve()


def get_sketches_report(sketches_report_path):
    """Return the data read from the JSON-formatted sketches report file

    Keyword arguments:
    path -- the path of the sketches report folder
    """
    sketches_report_file_path = next(sketches_report_path.glob("*.json"))
    with sketches_report_file_path.open() as sketches_report_file:
        sketches_report = json.load(sketches_report_file)

    return sketches_report


def get_service(google_key_file):
    """Return the Google API service object

    Keyword arguments:
    google_key_file -- contents of the Google private key file
    """
    credentials = service_account.Credentials.from_service_account_info(
        info=json.loads(google_key_file, strict=False), scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return discovery.build(serviceName='sheets', version='v4', credentials=credentials)


def execute_google_api_request(request):
    """Execute a Google API request and return the response.

    Keyword arguments:
    request -- request object
    """
    maximum_request_attempts = 3

    request_attempt_count = 0
    while True:
        request_attempt_count += 1
        try:
            return request.execute()
        except Exception as exception:
            if (
                request_attempt_count >= maximum_request_attempts
                or determine_request_retry(exception=exception) is False
            ):
                raise exception


def get_data_column_letter(heading_row_data, fqbn, sketch_name, size_name):
    """Return a dictionary containing the data column letter for this board, sketch, size type.
    populated -- whether the column headings have been added
    letter -- letter of the column containing memory usage data

    Keyword arguments:
    heading_row_data -- the contents of the heading row of the spreadsheet, as returned by get_heading_row_data()
    fqbn -- fully qualified board name of the board
    sketch_name -- the sketch path
    size_name -- the name of the memory type
    """
    populated = False
    index = 0
    for index, cell_text in enumerate(heading_row_data["values"][0]):
        if cell_text == fqbn + "\n" + sketch_name + "\n" + size_name:
            populated = True
            break

    if not populated:
        # Use the next column
        index += 1

    data_column_letter = get_spreadsheet_column_letters_from_number(column_number=index + 1)
    logger.info(size_name, "data column:", data_column_letter)
    return {"populated": populated, "letter": data_column_letter}


def determine_request_retry(exception):
    """Determine whether the exception warrants another attempt at the API request.
    If so, delay then return True. Otherwise, return False.

    Keyword arguments:
    exception -- the exception
    """
    # Retry urlopen after exceptions that start with the following strings
    request_retry_exceptions = [
        # https://developers.google.com/analytics/devguides/reporting/mcf/v3/limits-quotas#exceeding
        "HttpError: <HttpError 403",
        "HttpError: <HttpError 429"
    ]

    # Delay before retry (seconds)
    # https://developers.google.com/analytics/devguides/reporting/mcf/v3/limits-quotas#general_quota_limits
    request_retry_delay = 110

    exception_string = str(exception.__class__.__name__) + ": " + str(exception)
    retry_request = False
    for request_retry_exception in request_retry_exceptions:
        if str(exception_string).startswith(request_retry_exception):
            # These errors may only be temporary, retry
            print(exception_string)
            print("Waiting for Google API request quota reset")
            time.sleep(request_retry_delay)
            retry_request = True

    return retry_request


def get_spreadsheet_column_letters_from_number(column_number):
    """Convert spreadsheet column number to letter (e.g., 27 returns AA). https://stackoverflow.com/a/23862195

    Keyword arguments:
    column_number -- spreadsheet column number. This is 1 indexed to match the row numbering system.
    """
    column_letter = ""
    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26)
        column_letter = chr(65 + remainder) + column_letter

    return column_letter


# Only execute the following code if the script is run directly, not imported
if __name__ == '__main__':
    main()  # pragma: no cover
