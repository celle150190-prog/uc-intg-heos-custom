# Custom Denon AVR controls

This repository is an automatically maintained custom build of
[`mase1981/uc-intg-heos`](https://github.com/mase1981/uc-intg-heos). It starts
from the newest upstream GitHub release and applies the same focused patch to
every source update.

## Remote 3 behavior for Denon/Marantz AVRs

- The physical `+` and `-` volume buttons use one HEOS volume step (about one
  dB on Denon/Marantz AVR volume scales), instead of the upstream five-step
  change.
- The custom remote UI exposes `+1 dB` and `-1 dB` buttons.
- The physical Channel Up and Channel Down buttons control Subwoofer 1 Level
  Up and Down.
- The custom UI also exposes `Subwoofer 1 +` and `Subwoofer 1 -`.

Subwoofer commands use Denon/Marantz' documented network-control command
`PSSWL UP` / `PSSWL DOWN` over TCP port 23. Enable **Network Control** on the
AVR and make sure TCP port 23 is reachable from the Remote. The command is sent
only for players recognized as AVRs; HEOS speakers retain the upstream UI and
five-step volume behavior.

## Automatic source updates and releases

The [`Sync latest upstream and publish custom release`](.github/workflows/sync-and-release.yml)
workflow runs every day and can also be started manually from GitHub's Actions
tab. It:

1. reads the latest non-prerelease upstream release;
2. downloads that release's source tag;
3. applies `scripts/apply_denon_remote3_customization.py`;
4. commits the updated source to `main` and builds the Remote ARM64 archive;
5. creates or replaces the custom GitHub release.

If upstream changes the relevant code so that the patch is no longer safe to
apply, the workflow stops before committing or publishing a package. Update the
anchor strings in the script, test it against the new source, and run the
workflow again.

The custom package deliberately retains upstream's `driver_id` (`uc-intg-heos`)
so it updates the existing HEOS integration on the Remote instead of installing
a second integration. Install only one of the upstream or custom packages at a
time.

The upstream project is licensed under MPL-2.0; the changed source files remain
covered by that license.
