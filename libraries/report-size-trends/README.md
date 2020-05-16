# libraries/report-size-trends action

This action records the memory usage of the sketch specified to the [`arduino/actions/libraries/compile-examples` action](../compile-examples)'s [`size-report-sketch` input](../compile-examples/README.md#size-report-sketch) to a Google Sheets spreadsheet.

## Inputs

### `sketches-report-path`

Path that contains the JSON formatted sketch data report, as specified to the `arduino/actions/libraries/compile-examples` action's [sketches-report-path input](../compile-examples/README.md#sketches-report-path). Default `"size-deltas-reports"`.

### `keyfile`

**Required** Contents of the Google key file used to update the size trends report Google Sheets spreadsheet. This should be defined using a [GitHub secret](https://help.github.com/en/actions/configuring-and-managing-workflows/creating-and-storing-encrypted-secrets).
1. Open https://console.developers.google.com/project
1. Click the "Create Project" button.
1. In the "Project name" field, enter the name you want for your project.
1. You don't need to select anything from the "Location" menu.
1. Click the button with the three horizontal lines at the top left corner of the window.
1. Hover the mouse pointer over "APIs & Services".
1. Click "Library".
1. Make sure the name of the project you created is selected from the dropdown menu at the top of the window.
1. Click 'Google Sheets API".
1. Click the "Enable" button.
1. Click the "Create Credentials" button.
1. From the "Which API are you using?" menu, select "Google Sheets API".
1. From the "Where will you be calling the API from?" menu, select "Other non-UI".
1. From the "What data will you be accessing?" options, select "Application data".
1. From the "Are you planning to use this API with App Engine or Compute Engine?" options, select "No, I’m not using them".
1. Click the "What credentials do I need?" button.
1. In the "Service account name" field, enter the name you want to use for the service account.
1. From the "Role" menu, select "Project > Editor".
1. From the "Key type" options, select "JSON".
1. Click the "Continue" button. The .json file containing your private key will be downloaded. Save this somewhere safe.
1. Open the downloaded file.
1. Copy the entire contents of the file to the clipboard.
1. Open the GitHub page of the repository you are configuring the GitHub Actions workflow for.
1. Click the "Settings" tab.
1. From the menu on the left side of the window, click "Secrets".
1. Click the "Add a new secret" link.
1. In the "Name" field, enter the variable name you want to use for your secret. This will be used for the `size-trends-report-key-file` argument of the `compile-examples` action in your workflow configuration file. For example, if you named the secret `GOOGLE_KEY_FILE`, you would reference it in your workflow configuration as `${{ secrets.GOOGLE_KEY_FILE }}`.
1. In the "Value" field, paste the contents of the key file.
1. Click the "Add secret" button.
1. Open the downloaded key file again.
1. Copy the email address shown in the `client_email` field.
1. Open Google Sheets: https://docs.google.com/spreadsheets
1. Under "Start a new spreadsheet", click "Blank".
1. Click the "Share" button at the top right corner of the window.
1. If you haven't already, give your spreadsheet a name.
1. Paste the `client_email` email address into the "Enter names or email addresses..." field.
1. Uncheck the box next to "Notify people".
1. Click the "OK" button.
1. In the "Skip sending invitations?" dialog, click the "OK" button.

### `size-trends-report-spreadsheet-id`

**Required** The ID of the Google Sheets spreadsheet to write the memory usage trends data to. The URL of your spreadsheet will look something like:
```
https://docs.google.com/spreadsheets/d/15WOp3vp-6AnTnWlNWaNWNl61Fe_j8UJhIKE0rVdV-7U/edit#gid=0
```
In this example, the spreadsheet ID is `15WOp3vp-6AnTnWlNWaNWNl61Fe_j8UJhIKE0rVdV-7U`.

### `size-trends-report-sheet-name`

The sheet name in the Google Sheets spreadsheet used for the memory usage trends report. Default `"Sheet1"`.

## Example usage

```yaml
- uses: arduino/actions/libraries/compile-examples@master
  with:
    size-report-sketch: Foobar
# Publish size trends report on each push to the master branch
- if: github.event_name == 'push' && github.ref == 'refs/heads/master'
  uses: arduino/actions/libraries/report-size-trends@master
  with:
    keyfile: ${{ secrets.GOOGLE_KEY_FILE }}
    size-trends-report-spreadsheet-id: 15WOp3vp-6AnTnWlNWaNWNl61Fe_j8UJhIKE0rVdV-7U
```
