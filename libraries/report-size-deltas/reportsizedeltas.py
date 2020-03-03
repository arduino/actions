import json
import logging
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    set_verbosity(enable_verbosity=False)

    report_size_deltas = ReportSizeDeltas(repository_name=os.environ["GITHUB_REPOSITORY"],
                                          artifact_name=os.environ["INPUT_SIZE-DELTAS-REPORTS-ARTIFACT-NAME"],
                                          token=os.environ["INPUT_GITHUB-TOKEN"])

    report_size_deltas.report_size_deltas()


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


class ReportSizeDeltas:
    """Methods for creating and submitting the memory usage change reports

    Keyword arguments:
    repository_name -- repository owner and name e.g., octocat/Hello-World
    artifact_name -- name of the workflow artifact that contains the memory usage data
    token -- GitHub access token
    """
    report_key_beginning = "**Memory usage change @["

    def __init__(self, repository_name, artifact_name, token):
        self.repository_name = repository_name
        self.artifact_name = artifact_name
        self.token = token

    def report_size_deltas(self):
        """Scan the repository's pull requests to see if any need reports and return a list of the reports submitted"""
        # Get the repository's pull requests
        logger.debug("Getting PRs for " + self.repository_name)
        report_list = []
        page_number = 1
        page_count = 1
        while page_number <= page_count:
            api_data = self.api_request(request="repos/" + self.repository_name + "/pulls",
                                        page_number=page_number)
            prs_data = api_data["json_data"]
            for pr_data in prs_data:
                # Note: closed PRs are not listed in the API response
                pr_number = pr_data["number"]
                pr_head_sha = pr_data["head"]["sha"]
                logger.debug("Processing pull request #" + str(pr_number) + ", head SHA: " + pr_head_sha)
                # When a PR is locked, only collaborators may comment. The automatically generated GITHUB_TOKEN will
                # likely be used, which is owned by the github-actions bot, who doesn't have collaborator status. So
                # locking the thread would cause the job to fail.
                if pr_data["locked"]:
                    logger.debug("PR locked, skipping")
                    continue

                if self.report_exists(pr_number=pr_number,
                                      pr_head_sha=pr_head_sha):
                    # Go on to the next PR
                    logger.debug("Report already exists")
                    continue

                artifact_download_url = self.get_artifact_download_url_for_sha(pr_user_login=pr_data["user"]["login"],
                                                                               pr_head_ref=pr_data["head"]["ref"],
                                                                               pr_head_sha=pr_head_sha)
                if artifact_download_url is None:
                    # Go on to the next PR
                    logger.debug("No artifact found")
                    continue

                artifact_folder_object = self.get_artifact(artifact_download_url=artifact_download_url)

                report = self.generate_report(artifact_folder_object=artifact_folder_object,
                                              pr_head_sha=pr_head_sha,
                                              pr_number=pr_number)

                self.comment_report(pr_number=pr_number, report_markdown=report["markdown"])

                report_list = report_list + [{"pr_number": pr_number, "report": report["data"]}]

            page_number += 1
            page_count = api_data["page_count"]

        return report_list

    def report_exists(self, pr_number, pr_head_sha):
        """Return whether a report has already been commented to the pull request thread for the latest workflow run

        Keyword arguments:
        pr_number -- number of the pull request to check
        pr_head_sha -- PR's head branch hash
        """
        # Get the pull request's comments
        page_number = 1
        page_count = 1
        while page_number <= page_count:
            api_data = self.api_request(request="repos/" + self.repository_name + "/issues/" + str(pr_number) +
                                                "/comments",
                                        page_number=page_number)

            comments_data = api_data["json_data"]
            for comment_data in comments_data:
                # Check if the comment is a report for the PR's head SHA
                if comment_data["body"].startswith(self.report_key_beginning + pr_head_sha):
                    return True

            page_number += 1
            page_count = api_data["page_count"]

        # No reports found for the PR's head SHA
        return False

    def get_artifact_download_url_for_sha(self, pr_user_login, pr_head_ref, pr_head_sha):
        """Return the report artifact download URL associated with the given head commit hash

        Keyword arguments:
        pr_user_login -- user name of the PR author (used to reduce number of GitHub API requests)
        pr_head_ref -- name of the PR head branch (used to reduce number of GitHub API requests)
        pr_head_sha -- hash of the head commit in the PR branch
        """
        # Get the repository's workflow runs
        page_number = 1
        page_count = 1
        while page_number <= page_count:
            api_data = self.api_request(request="repos/" + self.repository_name + "/actions/runs",
                                        request_parameters="actor=" + pr_user_login + "&branch=" + pr_head_ref +
                                                           "&event=pull_request&status=completed",
                                        page_number=page_number)
            runs_data = api_data["json_data"]

            # Find the runs with the head SHA of the PR (there may be multiple runs)
            for run_data in runs_data["workflow_runs"]:
                if run_data["head_sha"] == pr_head_sha:
                    # Check if this run has the artifact we're looking for
                    artifact_download_url = self.get_artifact_download_url_for_run(run_id=run_data["id"])
                    if artifact_download_url is not None:
                        return artifact_download_url

            page_number += 1
            page_count = api_data["page_count"]

        # No matching artifact found
        return None

    def get_artifact_download_url_for_run(self, run_id):
        """Return the report artifact download URL associated with the given GitHub Actions workflow run

        Keyword arguments:
        run_id -- GitHub Actions workflow run ID
        """
        # Get the workflow run's artifacts
        page_number = 1
        page_count = 1
        while page_number <= page_count:
            api_data = self.api_request(request="repos/" + self.repository_name + "/actions/runs/" +
                                                str(run_id) + "/artifacts",
                                        page_number=page_number)
            artifacts_data = api_data["json_data"]

            for artifact_data in artifacts_data["artifacts"]:
                # The artifact is identified by a specific name
                if artifact_data["name"] == self.artifact_name:
                    return artifact_data["archive_download_url"]

            page_number += 1
            page_count = api_data["page_count"]

        # No matching artifact found
        return None

    def get_artifact(self, artifact_download_url):
        """Download and unzip the artifact and return an object for the temporary directory containing it

        Keyword arguments:
        artifact_download_url -- URL to download the artifact from GitHub
        """
        # Create temporary folder
        artifact_folder_object = tempfile.TemporaryDirectory(prefix="reportsizedeltas-")
        try:
            # Download artifact
            with open(file=artifact_folder_object.name + "/" + self.artifact_name + ".zip", mode="wb") as out_file:
                with self.raw_http_request(url=artifact_download_url) as fp:
                    out_file.write(fp.read())

            # Unzip artifact
            artifact_zip_file = artifact_folder_object.name + "/" + self.artifact_name + ".zip"
            with zipfile.ZipFile(file=artifact_zip_file, mode="r") as zip_ref:
                zip_ref.extractall(path=artifact_folder_object.name)
            os.remove(artifact_zip_file)

            return artifact_folder_object

        except Exception:
            artifact_folder_object.cleanup()
            raise

    def generate_report(self, artifact_folder_object, pr_head_sha, pr_number):
        """Parse the artifact files and returns a dictionary:
        markdown -- Markdown formatted report text
        data -- list containing all the report data

        Keyword arguments:
        artifact_folder_object -- object containing the data about the temporary folder that stores the markdown files
        """
        with artifact_folder_object as artifact_folder:
            report_markdown = (self.report_key_beginning + pr_head_sha + "]" +
                               "(https://github.com/" + self.repository_name + "/pull/" + str(pr_number) +
                               "/commits/" + pr_head_sha + ")**\n\n")
            report_markdown = report_markdown + "FQBN | Flash Usage | RAM For Global Variables\n---|---|---"
            reports_data = []
            for report_filename in sorted(os.listdir(path=artifact_folder)):
                with open(file=artifact_folder + "/" + report_filename) as report_file:
                    report_data = json.load(report_file)
                    reports_data = reports_data + [report_data]
                    report_markdown = (report_markdown + "\n" +
                                       report_data["fqbn"] +
                                       generate_value_cell(report_data["flash_delta"]) +
                                       generate_value_cell(report_data["ram_delta"]))

        logger.debug("Report:\n" + report_markdown)
        return {"markdown": report_markdown, "data": reports_data}

    def comment_report(self, pr_number, report_markdown):
        """Submit the report as a comment on the PR thread

        Keyword arguments:
        pr_number -- pull request number to submit the report to
        report_markdown -- Markdown formatted report
        """
        report_data = {"body": report_markdown}
        report_data = json.dumps(obj=report_data)
        report_data = report_data.encode(encoding="utf-8")
        url = ("https://api.github.com/repos/" +
               self.repository_name +
               "/issues/" +
               str(pr_number) +
               "/comments")

        self.http_request(url=url, data=report_data)

    def api_request(self, request, request_parameters="", page_number=1):
        """Do a GitHub API request. Return a dictionary containing:
        json_data -- JSON object containing the response
        additional_pages -- indicates whether more pages of results remain (True, False)
        page_count -- total number of pages of results

        Keyword arguments:
        request -- the section of the URL following https://api.github.com/
        request_parameters -- GitHub API request parameters (see: https://developer.github.com/v3/#parameters)
                              (default value: "")
        page_number -- Some responses will be paginated. This argument specifies which page should be returned.
                       (default value: 1)
        """
        return self.get_json_response(url="https://api.github.com/" + request + "?" + request_parameters + "&page=" +
                                          str(page_number) + "&per_page=100")

    def get_json_response(self, url):
        """Load the specified URL and return a dictionary:
        json_data -- JSON object containing the response
        additional_pages -- indicates whether more pages of results remain (True, False)
        page_count -- total number of pages of results

        Keyword arguments:
        url -- the URL to load
        """
        try:
            response_data = self.http_request(url=url)
            try:
                json_data = json.loads(response_data["body"])
            except json.decoder.JSONDecodeError as exception:
                # Output some information on the exception
                logger.warning(str(exception.__class__.__name__) + ": " + str(exception))
                # pass on the exception to the caller
                raise exception

            if not json_data:
                # There was no HTTP error but an empty list was returned (e.g. pulls API request when the repo
                # has no open PRs)
                page_count = 0
                additional_pages = False
            else:
                page_count = 1
                additional_pages = False

                if response_data["headers"]["Link"] is not None:
                    # Get the pagination data
                    if response_data["headers"]["Link"].find(">; rel=\"next\"") != -1:
                        additional_pages = True
                    for link in response_data["headers"]["Link"].split(","):
                        if link[-13:] == ">; rel=\"last\"":
                            link = re.split("[?&>]", link)
                            for parameter in link:
                                if parameter[:5] == "page=":
                                    page_count = int(parameter.split("=")[1])
                                    break
                            break

            return {"json_data": json_data, "additional_pages": additional_pages, "page_count": page_count}
        except Exception as exception:
            raise exception

    def http_request(self, url, data=None):
        """Make a request and return a dictionary:
        read -- the response
        info -- headers
        url -- the URL of the resource retrieved

        Keyword arguments:
        url -- the URL to load
        data -- data to pass with the request
                (default value: None)
        """
        with self.raw_http_request(url=url, data=data) as response_object:
            return {"body": response_object.read().decode(encoding="utf-8", errors="ignore"),
                    "headers": response_object.info(),
                    "url": response_object.geturl()}

    def raw_http_request(self, url, data=None):
        """Make a request and return an object containing the response.

        Keyword arguments:
        url -- the URL to load
        data -- data to pass with the request
                (default value: None)
        """
        # Maximum times to retry opening the URL before giving up
        maximum_urlopen_retries = 3

        logger.info("Opening URL: " + url)

        # GitHub recommends using user name as User-Agent (https://developer.github.com/v3/#user-agent-required)
        headers = {"Authorization": "token " + self.token, "User-Agent": self.repository_name.split("/")[0]}
        request = urllib.request.Request(url=url, headers=headers, data=data)

        retry_count = 0
        while retry_count <= maximum_urlopen_retries:
            retry_count += 1
            try:
                # The rate limit API is not subject to rate limiting
                if not url.startswith("https://api.github.com/rate_limit"):
                    self.handle_rate_limiting()
                return urllib.request.urlopen(url=request)
            except Exception as exception:
                if not determine_urlopen_retry(exception=exception):
                    raise exception

        # Maximum retries reached without successfully opening URL
        raise TimeoutError("Maximum number of URL load retries exceeded")

    def handle_rate_limiting(self):
        """Check whether the GitHub API request limit has been reached.
        If so, exit with exit status 0.
        """
        rate_limiting_data = self.get_json_response(url="https://api.github.com/rate_limit")["json_data"]
        # GitHub has two API types, each with their own request limits and counters.
        # "search" applies only to api.github.com/search.
        # "core" applies to all other parts of the API.
        # Since this code only uses the "core" API, only those values are relevant
        logger.debug("GitHub core API request allotment: " + str(rate_limiting_data["resources"]["core"]["limit"]))
        logger.debug("Remaining API requests: " + str(rate_limiting_data["resources"]["core"]["remaining"]))
        logger.debug("API request count reset time: " + str(rate_limiting_data["resources"]["core"]["reset"]))

        if rate_limiting_data["resources"]["core"]["remaining"] == 0:
            # GitHub uses a fixed rate limit window of 60 minutes. The window starts when the API request count goes
            # from 0 to 1. 60 minutes after the start of the window, the request count is reset to 0.
            logger.warning("GitHub API request quota has been reached. Try again later.")
            sys.exit(0)


def determine_urlopen_retry(exception):
    """Determine whether the exception warrants another attempt at opening the URL.
    If so, delay then return True. Otherwise, return False.

    Keyword arguments:
    exception -- the exception
    """
    # Retry urlopen after exceptions that start with the following strings
    urlopen_retry_exceptions = [
        # urllib.error.HTTPError: HTTP Error 403: Forbidden
        "HTTPError: HTTP Error 403",
        # urllib.error.HTTPError: HTTP Error 502: Bad Gateway
        "HTTPError: HTTP Error 502",
        # urllib.error.HTTPError: HTTP Error 503: Service Unavailable
        # caused by rate limiting
        "HTTPError: HTTP Error 503",
        # http.client.RemoteDisconnected: Remote end closed connection without response
        "RemoteDisconnected",
        # ConnectionResetError: [Errno 104] Connection reset by peer
        "ConnectionResetError",
        # ConnectionRefusedError: [WinError 10061] No connection could be made because the target machine actively
        # refused it
        "ConnectionRefusedError",
        # urllib.error.URLError: <urlopen error [WinError 10061] No connection could be made because the target
        # machine actively refused it>
        "<urlopen error [WinError 10061] No connection could be made because the target machine actively refused "
        "it>"
    ]

    # Delay before retry (seconds)
    urlopen_retry_delay = 30

    exception_string = str(exception.__class__.__name__) + ": " + str(exception)
    logger.info(exception_string)
    for urlopen_retry_exception in urlopen_retry_exceptions:
        if str(exception_string).startswith(urlopen_retry_exception):
            # These errors may only be temporary, retry
            logger.warning("Temporarily unable to open URL (" + str(exception) + "), retrying")
            time.sleep(urlopen_retry_delay)
            return True

    # Other errors are probably permanent so give up
    if str(exception_string).startswith("urllib.error.HTTPError: HTTP Error 401"):
        # Give a nice hint as to the cause of this error
        logger.error(exception)
        logger.info("HTTP Error 401 may be caused by providing an incorrect GitHub personal access token.")
    return False


def generate_value_cell(value):
    """Return the Markdown formatted text for a memory change data cell in the report table

    Keyword arguments:
    value -- amount of memory change
    """
    size_decrease_emoji = ":green_heart:"
    size_increase_emoji = ":small_red_triangle:"

    cell = " | "
    if value == "N/A":
        pass
    elif value > 0:
        cell = cell + size_increase_emoji + " +"
    elif value < 0:
        cell = cell + size_decrease_emoji + " "
    else:
        pass

    return cell + str(value)


# Only execute the following code if the script is run directly, not imported
if __name__ == "__main__":
    main()
