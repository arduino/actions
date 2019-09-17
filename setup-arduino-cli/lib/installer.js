"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (Object.hasOwnProperty.call(mod, k)) result[k] = mod[k];
    result["default"] = mod;
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
// Load tempDirectory before it gets wiped by tool-cache
let tempDirectory = process.env["RUNNER_TEMP"] || "";
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const util = __importStar(require("util"));
const restm = __importStar(require("typed-rest-client/RestClient"));
const semver = __importStar(require("semver"));
if (!tempDirectory) {
    let baseLocation;
    if (process.platform === "win32") {
        // On windows use the USERPROFILE env variable
        baseLocation = process.env["USERPROFILE"] || "C:\\";
    }
    else {
        if (process.platform === "darwin") {
            baseLocation = "/Users";
        }
        else {
            baseLocation = "/home";
        }
    }
    tempDirectory = path.join(baseLocation, "actions", "temp");
}
const core = __importStar(require("@actions/core"));
const tc = __importStar(require("@actions/tool-cache"));
let osPlat = os.platform();
let osArch = os.arch();
function getArduinoCli(version) {
    return __awaiter(this, void 0, void 0, function* () {
        // resolve the version number
        const targetVersion = yield computeVersion(version);
        if (targetVersion) {
            version = targetVersion;
        }
        // look if the binary is cached
        let toolPath;
        toolPath = tc.find("arduino-cli", version);
        // if not: download, extract and cache
        if (!toolPath) {
            toolPath = yield downloadRelease(version);
            core.debug("CLI cached under " + toolPath);
        }
        core.addPath(toolPath);
    });
}
exports.getArduinoCli = getArduinoCli;
function downloadRelease(version) {
    return __awaiter(this, void 0, void 0, function* () {
        // Download
        let fileName = getFileName(version);
        let downloadUrl = util.format("https://github.com/Arduino/arduino-cli/releases/download/%s/%s", version, fileName);
        let downloadPath = null;
        try {
            downloadPath = yield tc.downloadTool(downloadUrl);
        }
        catch (error) {
            core.debug(error);
            throw `Failed to download version ${version}: ${error}`;
        }
        // Extract
        let extPath = null;
        if (osPlat == "win32") {
            extPath = yield tc.extractZip(downloadPath);
        }
        else {
            extPath = yield tc.extractTar(downloadPath);
        }
        // Install into the local tool cache - node extracts with a root folder that matches the fileName downloaded
        return yield tc.cacheDir(extPath, "arduino-cli", version);
    });
}
function getFileName(version) {
    const arch = osArch == "x64" ? "64bit" : "32bit";
    let platform = "";
    let ext = "";
    switch (osPlat) {
        case "win32":
            platform = "Windows";
            ext = "zip";
            break;
        case "linux":
            platform = "Linux";
            ext = "tar.gz";
            break;
        case "darwin":
            platform = "macOS";
            ext = "tar.gz";
            break;
    }
    return util.format("arduino-cli_%s_%s_%s.%s", version, platform, arch, ext);
}
// Retrieve a list of versions scraping tags from the Github API
function fetchVersions() {
    return __awaiter(this, void 0, void 0, function* () {
        let rest = new restm.RestClient("setup-arduino-cli");
        let tags = (yield rest.get("https://api.github.com/repos/Arduino/arduino-cli/git/refs/tags")).result || [];
        return tags
            .filter(tag => tag.ref.match(/\d+\.[\w\.]+/g))
            .map(tag => tag.ref.replace("refs/tags/", ""));
    });
}
// Compute an actual version starting from the `version` configuration param.
function computeVersion(version) {
    return __awaiter(this, void 0, void 0, function* () {
        // strip trailing .x chars
        if (version.endsWith(".x")) {
            version = version.slice(0, version.length - 2);
        }
        const allVersions = yield fetchVersions();
        const possibleVersions = allVersions.filter(v => v.startsWith(version));
        const versionMap = new Map();
        possibleVersions.forEach(v => versionMap.set(normalizeVersion(v), v));
        const versions = Array.from(versionMap.keys())
            .sort(semver.rcompare)
            .map(v => versionMap.get(v));
        core.debug(`evaluating ${versions.length} versions`);
        if (versions.length === 0) {
            throw new Error("unable to get latest version");
        }
        core.debug(`matched: ${versions[0]}`);
        return versions[0];
    });
}
// Make partial versions semver compliant.
function normalizeVersion(version) {
    const preStrings = ["beta", "rc", "preview"];
    const versionPart = version.split(".");
    if (versionPart[1] == null) {
        //append minor and patch version if not available
        // e.g. 2 -> 2.0.0
        return version.concat(".0.0");
    }
    else {
        // handle beta and rc
        // e.g. 1.10beta1 -? 1.10.0-beta1, 1.10rc1 -> 1.10.0-rc1
        if (preStrings.some(el => versionPart[1].includes(el))) {
            versionPart[1] = versionPart[1]
                .replace("beta", ".0-beta")
                .replace("rc", ".0-rc")
                .replace("preview", ".0-preview");
            return versionPart.join(".");
        }
    }
    if (versionPart[2] == null) {
        //append patch version if not available
        // e.g. 2.1 -> 2.1.0
        return version.concat(".0");
    }
    else {
        // handle beta and rc
        // e.g. 1.8.5beta1 -> 1.8.5-beta1, 1.8.5rc1 -> 1.8.5-rc1
        if (preStrings.some(el => versionPart[2].includes(el))) {
            versionPart[2] = versionPart[2]
                .replace("beta", "-beta")
                .replace("rc", "-rc")
                .replace("preview", "-preview");
            return versionPart.join(".");
        }
    }
    return version;
}
