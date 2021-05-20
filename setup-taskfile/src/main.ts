import * as core from "@actions/core";
import * as installer from "./installer";

core.warning(
  "This version of the action is deprecated. Use arduino/setup-task. See https://github.com/arduino/setup-task"
);

async function run() {
  try {
    let version = core.getInput("version");
    let repoToken = core.getInput("repo-token");
    if (!version) {
      version = "2.x";
    }

    if (version) {
      await installer.getTask(version, repoToken);
    }
  } catch (error) {
    core.setFailed(error.message);
  }
}

run();
