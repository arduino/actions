# actions

This repository contains custom GitHub Actions used across Arduino's codebase.
Usage informations for each Action can be found in their respective folders.

* [setup-arduino-cli](./setup-arduino-cli) makes the
[Arduino CLI](https://github.com/Arduino/arduino-cli)
available to your Workflows.

* [setup-protoc](./setup-protoc) makes the
[protobuf compiler](https://github.com/protocolbuffers/protobuf)
available to your Workflows.

* [setup-taskfile](./setup-taskfile) makes [`task`](https://taskfile.dev/#/)
available to your Workflows.

* [libraries/compile-examples](./libraries/compile-examples) compile all the examples in an Arduino Library

* [libraries/spell-check](./libraries/spell-check) run spell checker on Arduino Library source and examples
