# setup-arduino-cli

This action makes the `arduino-cli` tool available to Workflows.

## Usage

To get the latest stable version of `arduino-cli` just add this step:

```yaml
- name: Install Arduino CLI
  uses: Arduino/actions/setup-arduino-cli@master
```

If you want to pin a major or minor version you can use the `.x` wildcard:

```yaml
- name: Install Arduino CLI
  uses: Arduino/actions/setup-arduino-cli@master
  with:
    version: '0.x'
```

To pin the exact version:

```yaml
- name: Install Arduino CLI
  uses: Arduino/actions/setup-arduino-cli@master
  with:
    version: '0.5.0'
```

## Development

To work on the codebase you have to install all the dependencies:

```sh
# npm install
```

To run the tests:

```sh
# npm run test
```

## Release

We check in the `node_modules` to provide runtime dependencies to the system
using the Action, so be careful not to `git add` all the development dependencies
you might have under your local `node_modules`. To release a new version of the
Action the workflow should be the following:

1. `npm install` to add all the dependencies, included development.
1. `npm run test` to see everything works as expected.
1. `npm build` to build the Action under the `./lib` folder.
1. `rm -rf node_modules` to remove all the dependencies.
1. `npm install --production` to add back **only** the runtime dependencies.
1. `git add lib node_modules` to check in the code that matters.
1. open a PR and request a review.
