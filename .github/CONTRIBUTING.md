# Contributing to Commander Toolbox

Open an issue or pull request in [Commander Toolbox](https://github.com/Commanderx-code/commander-toolbox).
Describe the problem, affected distribution and expected behavior. For interface
issues, include the terminal name and a screenshot when useful.

## Local development

Fork this repository, clone your fork, and install a current Rust toolchain,
Python 3, ShellCheck and checkbashisms. Read [AGENTS.md](../AGENTS.md) and
[SPEC.md](../SPEC.md) for the repository conventions.

```sh
cargo run --locked --package linutil_tui
```

Utilities live under `core/tabs/`; custom installers live under
`core/tabs/commander/`. Add menu entries in the relevant `tab_data.toml`.
Keep changes focused, preserve existing configurations and use the shared
package-manager helpers. Test bootloader and service changes in a disposable VM.

## Validate changes

```sh
python3 -B -m unittest discover -s tests -v
cargo fmt --all --check
cargo test --locked --no-fail-fast --package linutil_core --package linutil_tui
cargo clippy --locked -- -Dwarnings
```

For shell changes, run ShellCheck and checkbashisms on the affected POSIX scripts.
For catalog changes, run `cargo xtask docgen` and include the generated walkthrough.
Run `git diff --check` before submitting.

Explain what changed, why, how it was tested, and any untested platform behavior
in the pull request. Preserve upstream attribution and third-party licenses.
