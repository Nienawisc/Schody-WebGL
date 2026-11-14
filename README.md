# Schody WebGL

Public test build of Schody. This repository contains the published WebGL game and public statistics tooling; Unity source code stays in the private development repository.

The private build workflow publishes the latest successful build to `gh-pages`.

Test site: https://nienawisc.github.io/Schody-WebGL/

## Lucky Roomber public statistics

The `master` branch contains a dependency-free SVG statistics-card generator for the Lucky Roomber itch.io page. It publishes aggregate-only SVG and JSON files without modifying the WebGL build or the `gh-pages` branch.

Read [the setup and itch.io embedding instructions](statistics/README.md) and [the automation options](statistics/AUTOMATION.md). The initial snapshot contains no fabricated counts. Update `statistics/snapshot.json`, paste the aggregate JSON into **Update public statistics > Run workflow**, or submit a Unity CSV/JSON export with `python statistics/submit_stats.py report.csv` after signing in to GitHub CLI. Fetching the Unity report is still manual; the workflow automates validation, rendering and publication.
