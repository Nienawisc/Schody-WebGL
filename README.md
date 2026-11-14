# Schody WebGL

Public test build of Schody. This repository contains the published WebGL game and public statistics tooling; Unity source code stays in the private development repository.

The private build workflow publishes the latest successful build to `gh-pages`.

Test site: https://nienawisc.github.io/Schody-WebGL/

## Lucky Roomber public statistics

The `master` branch also contains a small statistics-card generator for the Lucky Roomber itch.io page. It publishes aggregate-only PNG and JSON files without modifying the WebGL build or the `gh-pages` branch.

Read [the setup, SQL export and itch.io embedding instructions](statistics/README.md). The initial snapshot deliberately contains no fabricated counts. Updating `statistics/snapshot.json` starts the **Update public statistics** workflow; obtaining the Unity SQL result is a manual step.
