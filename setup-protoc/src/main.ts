import * as core from "@actions/core";
import * as installer from "./installer";

async function run() {
  try {
    let version = core.getInput("version");
    let includePreReleases = core.getInput("include-pre-releses");
    await installer.getProtoc(version, includePreReleases);

  } catch (error) {
    core.setFailed(error.message);
  }
}

run();
