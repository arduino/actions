import io = require("@actions/io");
import path = require("path");
import os = require("os");
import fs = require("fs");
import nock = require("nock");

const toolDir = path.join(__dirname, "runner", "tools");
const tempDir = path.join(__dirname, "runner", "temp");
const dataDir = path.join(__dirname, "testdata");
const IS_WINDOWS = process.platform === "win32";

process.env["RUNNER_TEMP"] = tempDir;
process.env["RUNNER_TOOL_CACHE"] = toolDir;
import * as installer from "../src/installer";

describe("installer tests", () => {
  beforeEach(async function() {
    await io.rmRF(toolDir);
    await io.rmRF(tempDir);
    await io.mkdirP(toolDir);
    await io.mkdirP(tempDir);
  });

  afterAll(async () => {
    try {
      await io.rmRF(toolDir);
      await io.rmRF(tempDir);
    } catch {
      console.log("Failed to remove test directories");
    }
  });

  it("Downloads version of protoc if no matching version is installed", async () => {
    await installer.getProtoc("3.9.0");
    const protocDir = path.join(toolDir, "protoc", "3.9.0", os.arch());

    expect(fs.existsSync(`${protocDir}.complete`)).toBe(true);

    if (IS_WINDOWS) {
      expect(fs.existsSync(path.join(protocDir, "bin", "protoc.exe"))).toBe(
        true
      );
    } else {
      expect(fs.existsSync(path.join(protocDir, "bin", "protoc"))).toBe(true);
    }
  }, 100000);

  describe("Gets the latest release of protoc", () => {
    beforeEach(() => {
      nock("https://api.github.com")
        .get("/repos/protocolbuffers/protobuf/git/refs/tags")
        .replyWithFile(200, path.join(dataDir, "tags.json"));
    });

    afterEach(() => {
      nock.cleanAll();
      nock.enableNetConnect();
    });

    it("Gets the latest 3.7.x version of protoc using 3.7 and no matching version is installed", async () => {
      await installer.getProtoc("3.7");
      const protocDir = path.join(toolDir, "protoc", "3.7.1", os.arch());

      expect(fs.existsSync(`${protocDir}.complete`)).toBe(true);
      if (IS_WINDOWS) {
        expect(fs.existsSync(path.join(protocDir, "bin", "protoc.exe"))).toBe(
          true
        );
      } else {
        expect(fs.existsSync(path.join(protocDir, "bin", "protoc"))).toBe(true);
      }
    }, 100000);

    it("Gets latest version of protoc using 3.x and no matching version is installed", async () => {
      await installer.getProtoc("3.x");
      const protocDir = path.join(toolDir, "protoc", "3.9.1", os.arch());

      expect(fs.existsSync(`${protocDir}.complete`)).toBe(true);
      if (IS_WINDOWS) {
        expect(fs.existsSync(path.join(protocDir, "bin", "protoc.exe"))).toBe(
          true
        );
      } else {
        expect(fs.existsSync(path.join(protocDir, "bin", "protoc"))).toBe(true);
      }
    }, 100000);
  });

  describe("Gets the latest release of protoc with broken latest rc tag", () => {
    beforeEach(() => {
      nock("https://api.github.com")
        .get("/repos/protocolbuffers/protobuf/git/refs/tags")
        .replyWithFile(200, path.join(dataDir, "tags-broken-rc-tag.json"));
    });

    afterEach(() => {
      nock.cleanAll();
      nock.enableNetConnect();
    });

    it("Gets latest version of protoc using 3.x with a broken rc tag, but filtering pre-releases", async () => {
      await installer.getProtoc("3.x");
      const protocDir = path.join(toolDir, "protoc", "3.9.1", os.arch());

      expect(fs.existsSync(`${protocDir}.complete`)).toBe(true);
      if (IS_WINDOWS) {
        expect(fs.existsSync(path.join(protocDir, "bin", "protoc.exe"))).toBe(
          true
        );
      } else {
        expect(fs.existsSync(path.join(protocDir, "bin", "protoc"))).toBe(true);
      }
    }, 100000);
  });
});
