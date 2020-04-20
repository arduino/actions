# Arduino GitHub Actions

A set of GitHub Actions officially provided and maintained by Arduino. Usage
informations can be found in their respective folders.

* [libraries/compile-examples](./libraries/compile-examples) uses Arduino CLI to
do compilation testing of your Arduino library.

* [libraries/report-size-deltas](./libraries/report-size-deltas) comments on
pull requests to provide a report of the resulting change in memory usage to the
Arduino library's example sketch .

* [libraries/spell-check](./libraries/spell-check) checks the files of your
repository for commonly misspelled words.

* [setup-arduino-cli](https://github.com/arduino/setup-arduino-cli) makes the
[Arduino CLI](https://github.com/Arduino/arduino-cli)
available to your Workflows.
  * **WARNING**: The `arduino/actions/setup-arduino-cli` action contained in this
  repository is deprecated. Please use the actively maintained
  `arduino/setup-arduino-cli` action at the link above.

* [setup-protoc](https://github.com/arduino/setup-protoc) makes the
[protobuf compiler](https://github.com/protocolbuffers/protobuf)
available to your Workflows.
  * **WARNING**: The `arduino/actions/setup-protoc` action contained in this
  repository is deprecated. Please use the actively maintained
  `arduino/setup-protoc` action at the link above.

* [setup-taskfile](./setup-taskfile) makes [Taskfile](https://taskfile.dev/#/)
available to your Workflows.
