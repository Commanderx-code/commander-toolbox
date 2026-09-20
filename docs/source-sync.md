# Automatic source updates

Toolbox watches **Commanderx-code/dotfiles** and **Commanderx-code/Myfish**. The
[Sync source repositories workflow](https://github.com/Commanderx-code/commander-toolbox/actions/workflows/sync-sources.yml)
runs at minutes 17 and 47 of each hour, on Toolbox pushes to `main`, and through
**Run workflow**. Scheduled runs can be delayed by GitHub.

For each source it reads the current `main` commit, then checks that commit's
`check.yml` push workflow. Only a completed successful run is accepted. A failed,
cancelled, missing or unfinished run leaves that source's previous pin in place;
an API error fails the sync instead of selecting an unchecked version.

The workflow imports each accepted `toolbox.json`, regenerates the Myfish and
Dotfiles submenus, runs Python and Rust core tests, generates the walkthrough,
and builds Toolbox. Only after those steps succeed does it commit and push the
new pins and menu. A concurrent human push stops publication without force-pushing.

The same workflow publishes a draft release, uploads the binary and SHA-256
checksum, then exposes the completed release. It performs publication itself
because a push using GitHub's built-in bot token does not start another push
workflow. Failed publication can be retried manually or by the next scheduled run.

## What updates automatically

- Changes to supported dotfiles configuration and Myfish's installer are included
  when their tested commit becomes the new source pin.
- New `config` entries in a source's `toolbox.json` become menu entries with generated
  installers. Removing one of these entries removes it from future builds, without
  deleting an existing user's installed configuration.
- Third-party theme repositories retain their separately reviewed pins. Config Bible
  and unrelated GitHub repositories are not executable sources for this workflow.

The generic installer reads native package names and config source/target paths.
It asks for `APPLY`, validates the whole plan, installs packages, then copies files
with backups. Destination symlinks, including Home Manager-managed files, are refused
before package installation. Targets are relative to XDG config. Directory copies
replace whole destination directories after backing them up. A multi-file install
is not atomic; earlier copied files retain their backups if a later copy fails.
No shell commands can be embedded in a `config` entry. System services, boot changes
and unusual installation procedures need a dedicated built-in Toolbox handler.

See the source guides for the complete catalog example:

- [Dotfiles publishing guide](https://github.com/Commanderx-code/dotfiles/blob/main/TOOLBOX.md)
- [Myfish publishing guide](https://github.com/Commanderx-code/Myfish/blob/main/TOOLBOX.md)

## Getting the update on your machine

Use Toolbox's **Toolbox Updater** action, or update your checkout and
rebuild normally. Alternatively, download `commander-toolbox-linux-x86_64` and
`SHA256SUMS` from [releases](https://github.com/Commanderx-code/commander-toolbox/releases).
These automated binaries are built on Ubuntu 22.04 for Linux x86_64 with glibc 2.35
or newer. Other architectures can build from the updated source checkout.

Running binaries do not reload embedded menus. Restart the updated Toolbox and
select the desired installer to apply changes. Personal configs and running tools
are never changed merely because a source commit was pushed.

## Maintenance and validation

The workflow uses Toolbox's built-in `GITHUB_TOKEN` for its own commits/releases
and reads the public source repositories; no cross-repository secret is required.
Only allowlisted repositories are queried. New repositories require an explicit
integration and a required CI workflow, not just an arbitrary URL in a catalog.

GitHub can disable schedules in public repos after 60 days without repository
activity. Re-enable this workflow in Actions when necessary. **Run workflow** is
also available to check immediately or retry a failed build/publication.

Local checks:

```sh
python3 -B scripts/sync-sources.py --render  # offline, from embedded catalogs
python3 -B -m unittest discover -s tests -v
cargo test --locked --package linutil_core
cargo xtask docgen
git diff --check
```

Running `python3 -B scripts/sync-sources.py` without `--render` queries GitHub and
updates source pins/catalogs in your checkout. It never commits, pushes, publishes
or installs tools by itself. Review existing local changes before using it.
