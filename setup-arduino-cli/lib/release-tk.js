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
const core = __importStar(require("@actions/core"));
const restm = __importStar(require("typed-rest-client/RestClient"));
const semver = __importStar(require("semver"));
// Compute an actual version starting from the `version` configuration param.
function computeVersion(version, repo) {
    return __awaiter(this, void 0, void 0, function* () {
        // strip leading `v` char (will be re-added later in case)
        let prefix = "";
        if (version.startsWith("v")) {
            version = version.slice(1, version.length);
            prefix = "v";
        }
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
        return prefix + versions[0];
    });
}
// Retrieve a list of versions scraping tags from the Github API
function fetchVersions(repo) {
    return __awaiter(this, void 0, void 0, function* () {
        let rest = new restm.RestClient("setup-taskfile");
        let tags = (yield rest.get("https://api.github.com/repos/go-task/task/git/refs/tags")).result || [];
        return tags
            .filter(tag => tag.ref.match(/v\d+\.[\w\.]+/g))
            .map(tag => tag.ref.replace("refs/tags/v", ""));
    });
}
