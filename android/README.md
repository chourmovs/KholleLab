# Android / Trusted Web Activity workspace

This directory contains **packaging configuration and pinned tooling only**. The Bubblewrap Android project is generated locally in `android/generated/`; it and all build/signing outputs are ignored by Git.

> **Digital Asset Links are deliberately deferred.** Do not create `frontend/public/.well-known/assetlinks.json` yet. The final association must use the SHA-256 fingerprint of the relevant Google Play App Signing certificate, which can differ from the local upload certificate. Add it only after the first Play bundle is uploaded and the final App Signing fingerprint is available in Play Console.

## Windows / PowerShell workflow

1. Install a supported Node.js release if needed.
2. Open PowerShell and install the pinned dependencies:

   ```powershell
   cd android
   npm ci
   ```

3. Set the real production HTTPS **origin** (no path), then check and validate:

   ```powershell
   $env:KHOLLELAB_TWA_ORIGIN="https://example.org"
   npm run check
   npm run twa:validate
   npm run twa:doctor
   ```

   `https://example.org` is an example only; replace it with the established production origin. The validator checks `$env:KHOLLELAB_TWA_ORIGIN/manifest.webmanifest` and never assumes a hostname.

4. Initialize Bubblewrap locally (do not run this as part of a repository change):

   ```powershell
   npx bubblewrap init `
     --manifest="$env:KHOLLELAB_TWA_ORIGIN/manifest.webmanifest" `
     --directory="./generated"
   ```

   Equivalent Bash syntax:

   ```bash
   export KHOLLELAB_TWA_ORIGIN="https://example.org"
   npx bubblewrap init \
     --manifest="$KHOLLELAB_TWA_ORIGIN/manifest.webmanifest" \
     --directory="./generated"
   ```

5. After initialization, verify the generated Gradle configuration:

   ```powershell
   npm run check:generated
   ```

## Required Bubblewrap answers

Use these exact values when prompted:

| Prompt | Required answer |
| --- | --- |
| Application ID | `com.chourmovs.khollelab` |
| Application name | `KholleLab` |
| Launcher name | `KholleLab` |
| Version name | `1.0.0` |
| Version code | `1` |
| Display mode | `standalone` |
| Orientation | default / unrestricted |
| Theme color | `#10271E` |
| Background color | `#10271E` |
| Notifications | No |
| Package for ChromeOS only | No |
| Meta Quest | No |
| Signing key | **CREATE LOCALLY ONLY** |

Play Billing and location delegation are disabled for this release. The fallback is `customtabs`; compile SDK and target SDK must both be at least 36.

## Signing and generated-file safety

Bubblewrap initialization generates local Android files and may generate a signing keystore. Never commit `generated/`, a keystore, private key, password, certificate private material, Gradle binary artifacts, APK/AAB/APKS files, or generated images. Do not record a real keystore path or password in documentation or configuration.

Back up the upload signing key privately and securely; losing it can prevent future uploads. The upload certificate is not necessarily the certificate Google Play uses to sign distributed installs, which is why no certificate fingerprint or `assetlinks.json` is included here.
