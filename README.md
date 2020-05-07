# Arduino GitHub Actions

**WARNING**: This repository is used for Arduino's development of experimental
[GitHub Actions](https://github.com/features/actions). They are unstable and not
fully tested. Use at your own risk!

Actions will be moved to dedicated repositories when they are ready for
production usage.

Usage information can be found in their respective folders.

* [libraries/compile-examples](./libraries/compile-examples) uses Arduino CLI to
do compilation testing of your Arduino library.

* [libraries/report-size-deltas](./libraries/report-size-deltas) comments on
pull requests to provide a report of the resulting change in memory usage to the
Arduino library's example sketch .

* [libraries/spell-check](./libraries/spell-check) checks the files of your
repository for commonly misspelled words.

* [setup-taskfile](./setup-taskfile) makes [Taskfile](https://taskfile.dev/#/)
available to your Workflows.

---
**Note**: Several actions previously hosted in this experimental repository have
reached stable status and been moved to dedicated repositories:

* [arduino/setup-arduino-cli](https://github.com/arduino/setup-arduino-cli) makes the
[Arduino CLI](https://github.com/Arduino/arduino-cli)
available to your Workflows.

* [arduino/setup-protoc](https://github.com/arduino/setup-protoc) makes the
[protobuf compiler](https://github.com/protocolbuffers/protobuf)
available to your Workflows.
