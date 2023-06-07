// example usage: node ./env_installer/construct.js linux x86_64
import { spawn } from "child_process";
import * as url from "url";
import path from "path";
import fs from "fs";
import yaml from "js-yaml";

const __dirname = url.fileURLToPath(new URL(".", import.meta.url));
const platform = process.env.TAURI_PLATFORM || process.argv[2];
const arch = process.env.TAURI_ARCH || process.argv[3];

const buildConfigFile = fs.readFileSync(
  path.resolve(__dirname, "construct.yaml"),
  "utf8"
);
let buildConfig = yaml.load(buildConfigFile);

const appName = buildConfig.name || process.argv[4];
const appVersion = buildConfig.version || process.argv[5];

let platformName = "";
let platformBuildName = "";

switch (platform) {
  case "macos":
    platformName = "osx";
    platformBuildName = "MacOSX";
    break;
  case "windows":
    platformName = "win";
    platformBuildName = "Windows";
    break;
  case "linux":
    platformName = platform;
    platformBuildName = "Linux";
    break;
  default:
    platformName = platform;
}

let platformArch = "";
switch (arch) {
  case "x86":
    platformArch = "32";
    break;
  case "x86_64":
    platformArch = "64";
    break;
  case "aarch64":
    platformArch = "arm64";
    break;
  default:
    platformArch = arch;
}

console.log(`Check if installer for ${platformName}-${platformArch} exists`);

let ext = platform === "windows" ? "exe" : "sh";

let installerPath = `../src-tauri/${appName}-${appVersion}-${platformBuildName}-${arch}.${ext}`;

console.log("Installer path:", installerPath);

// check if the installer file exists
const installerExists = fs.existsSync(path.resolve(__dirname, installerPath));

if (installerExists) {
  console.log(
    `Installer for ${platformName}-${platformArch} already exists. Skipping build.`
  );
  process.exit(0);
}

console.log(`Building installer for ${platformName}-${platformArch}`);

spawn(
  "constructor",
  [
    __dirname,
    `--platform=${platformName}-${platformArch}`,
    "--output-dir",
    path.resolve(__dirname, "../src-tauri"),
  ],
  { stdio: "inherit" }
);
