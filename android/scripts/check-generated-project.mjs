import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const generatedDirectory = fileURLToPath(new URL("../generated/", import.meta.url));

async function findGradleFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (entry.name === ".gradle" || entry.name === "build") continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await findGradleFiles(path));
    else if (/\.gradle(?:\.kts)?$/.test(entry.name)) files.push(path);
  }
  return files;
}

let files;
try {
  files = await findGradleFiles(generatedDirectory);
} catch (error) {
  if (error.code === "ENOENT") {
    console.error("android/generated/ does not exist; local Bubblewrap initialization has not yet been performed.");
    process.exit(1);
  }
  console.error(`Unable to inspect android/generated/: ${error.message}`);
  process.exit(1);
}

if (!files.length) {
  console.error("No Gradle configuration files were found in android/generated/. Run Bubblewrap initialization first.");
  process.exit(1);
}

const source = (await Promise.all(files.map((file) => readFile(file, "utf8")))).join("\n");
const captureNumbers = (name) => [...source.matchAll(new RegExp(`\\b${name}\\s*(?:=\\s*)?(\\d+)`, "g"))].map((match) => Number(match[1]));
const errors = [];

if (!/\bapplicationId\s*(?:=\s*)?["']com\.chourmovs\.khollelab["']/.test(source)) errors.push('applicationId "com.chourmovs.khollelab" was not found');
const compileSdks = [...captureNumbers("compileSdkVersion"), ...captureNumbers("compileSdk")];
if (!compileSdks.some((value) => value >= 36)) errors.push("compileSdk/compileSdkVersion >= 36 was not found");
const targetSdks = [...captureNumbers("targetSdkVersion"), ...captureNumbers("targetSdk")];
if (!targetSdks.some((value) => value >= 36)) errors.push("targetSdk/targetSdkVersion >= 36 was not found");
if (!/\bversionCode\s*(?:=\s*)?1\b/.test(source)) errors.push("versionCode 1 was not found");
if (!/\bversionName\s*(?:=\s*)?["']1\.0\.0["']/.test(source)) errors.push('versionName "1.0.0" was not found');

if (errors.length) {
  console.error("Generated Android project is invalid:\n" + errors.map((error) => `- ${error}`).join("\n"));
  process.exit(1);
}

console.log("Generated Android project configuration is valid.");
