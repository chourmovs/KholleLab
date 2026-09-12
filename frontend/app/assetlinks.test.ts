import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const assetLinksPath = join(
  process.cwd(),
  "public/.well-known/assetlinks.json",
);

describe("Digital Asset Links", () => {
  it("publishes the Google Play app signing identity for the Android TWA", () => {
    expect(existsSync(assetLinksPath)).toBe(true);

    const assetLinks = JSON.parse(readFileSync(assetLinksPath, "utf8"));

    expect(assetLinks).toEqual([
      {
        relation: ["delegate_permission/common.handle_all_urls"],
        target: {
          namespace: "android_app",
          package_name: "com.chourmovs.khollelab",
          sha256_cert_fingerprints: [
            "AC:75:DB:82:9D:63:3C:FB:96:08:49:7E:B5:44:61:96:A4:4C:69:41:C6:E0:8B:F7:DB:3B:43:CA:06:25:EB:0B",
          ],
        },
      },
    ]);
  });
});
