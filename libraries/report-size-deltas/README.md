# libraries/report-size-deltas action

This action comments on the pull request with a report on the change in memory usage of an example sketch. This should be run from a [scheduled workflow](https://help.github.com/en/actions/reference/workflow-syntax-for-github-actions#onschedule).

## DEPRECATION NOTICE

**WARNING: the action has been moved to https://github.com/arduino/report-size-deltas**

This unmaintained copy is kept only to provide provisional support for existing workflows, but will be removed soon.

See the migration guide:

https://github.com/arduino/report-size-deltas/releases/tag/v1.0.0

## Inputs

### `size-deltas-reports-artifact-name`

Name of the workflow artifact that contains the memory usage data, as specified to the actions/upload-artifact action via the name argument. Default "size-deltas-reports".

### `github-token`

GitHub access token used to comment the memory usage comparison results to the PR thread. Default [`GITHUB_TOKEN`](https://help.github.com/en/actions/configuring-and-managing-workflows/authenticating-with-the-github_token).

## Example usage

```yaml
on:
  schedule:
    - cron:  '*/5 * * * *'
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: arduino/actions/libraries/report-size-deltas@master
```
