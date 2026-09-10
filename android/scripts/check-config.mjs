import { readFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const configUrl = new URL("../twa-config.json", import.meta.url);
let config;

try {
  config = JSON.parse(await readFile(configUrl, "utf8"));
} catch (error) {
  console.error(`Unable to read twa-config.json: ${error.message}`);
  process.exit(1);
}

const errors = [];
const requireValue = (condition, message) => {
  if (!condition) errors.push(message);
};

requireValue(config.packageId === "com.chourmovs.khollelab", "packageId must be com.chourmovs.khollelab");
requireValue(Number.isInteger(config.appVersionCode) && config.appVersionCode > 0, "appVersionCode must be a positive integer");
requireValue(typeof config.appVersion === "string" && config.appVersion.trim() !== "", "appVersion must be a non-empty version name");
requireValue(Number.isInteger(config.targetSdkVersion) && config.targetSdkVersion >= 36, "targetSdkVersion must be an integer >= 36");
requireValue(Number.isInteger(config.compileSdkVersion) && config.compileSdkVersion >= 36, "compileSdkVersion must be an integer >= 36");
requireValue(config.targetSdkVersion <= config.compileSdkVersion, "targetSdkVersion must not exceed compileSdkVersion");
requireValue(config.startUrl === "/", 'startUrl must be "/"');
requireValue(config.manifestPath === "/manifest.webmanifest", 'manifestPath must be "/manifest.webmanifest"');
requireValue(config.display === "standalone", 'display must be "standalone"');
requireValue(config.enableNotifications === false, "notification support must be disabled");
requireValue(config.fallbackType === "customtabs", 'fallbackType must be "customtabs"');

let origin;
if (process.env.KHOLLELAB_TWA_ORIGIN) {
  try {
    origin = new URL(process.env.KHOLLELAB_TWA_ORIGIN);
    requireValue(origin.protocol === "https:", "KHOLLELAB_TWA_ORIGIN must use HTTPS");
    requireValue(!origin.username && !origin.password, "KHOLLELAB_TWA_ORIGIN must not contain credentials");
    requireValue(origin.pathname === "/" && !origin.search && !origin.hash, "KHOLLELAB_TWA_ORIGIN must contain only an origin (no path, query, or fragment)");
  } catch {
    errors.push("KHOLLELAB_TWA_ORIGIN must be a valid URL");
  }
}

if (errors.length) {
  console.error("Android TWA configuration is invalid:\n" + errors.map((error) => `- ${error}`).join("\n"));
  process.exit(1);
}

console.log("Android TWA repository configuration is valid.");

if (process.argv.includes("--validate")) {
  if (!origin) {
    console.error("KHOLLELAB_TWA_ORIGIN is required for twa:validate (for example, https://example.org).");
    process.exit(1);
  }

  const manifestUrl = new URL(config.manifestPath, origin).href;
  console.log(`Validating ${manifestUrl}`);
  const executable = process.platform === "win32" ? "bubblewrap.cmd" : "bubblewrap";
  const bubblewrapPath = fileURLToPath(new URL(`../node_modules/.bin/${executable}`, import.meta.url));
  const result = spawnSync(bubblewrapPath, ["validate", "--url", manifestUrl], { stdio: "inherit" });
  if (result.error) console.error(`Unable to start Bubblewrap: ${result.error.message}`);
  process.exit(result.status ?? 1);
}
