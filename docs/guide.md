# Commander Toolbox guide

[Back to the project overview](../README.md)

## Build and run

With Rust/Cargo installed, clone and run as your normal user:

```sh
git clone https://github.com/Commanderx-code/commander-toolbox.git
cd commander-toolbox
cargo run --locked --package linutil_tui
```

For a standalone build:

```sh
cargo build --locked --release --package linutil_tui
./target/release/commander-toolbox
```

This project preserves the original Linutil history and MIT license. The inherited `start.sh`, `startdev.sh`,
package installers and release automation still belong to upstream; use the
local Cargo commands above until a separate release channel is configured.
The upstream installer/updater menu entries are removed so they cannot replace
this build with the stock application through the menu.

## Custom entries

| Location | Entry | Behavior |
| --- | --- | --- |
| Applications Setup > Design Tools | DaVinci Resolve - Native / Davincibox | Install Resolve directly or in a dependency container on Fedora/Arch or Debian/Ubuntu; see the [Resolve guide](resolve.md). |
| Applications Setup | Myfish Shell Setup | Open the submenu for native Fish, Bash or Zsh, or Guided Setup to choose the backend interactively. |
| Applications Setup | Dotfiles | Open the submenu and select Neovim, Fastfetch, Starship, Konsole profile/colors or optional Ghostty profile, with backups. |
| Applications Setup > Grub Theme | Commander GRUB Theme | Installs your CachyOS-based theme while preserving current kernel/disk settings. |
| Applications Setup | SDDM Theme | Installs the dedicated `sddm/` SilentSDDM Revan preset, previews it, then asks before activation. |
| System Setup > Debian | Nala Package Manager | Install Nala and add an interactive `apt` alias for Bash, Zsh or Fish, with backups. |
| System Setup | Commander Topgrade | Replaces the default Topgrade action with your adapted config and an optional update run. |
| Security | AppArmor Setup and Status | Installs tools/profiles and starts AppArmor on supported systems with an already-enabled kernel. |
| Security | Fedora SELinux Tools and Status | Installs policy/management tools and reports status without changing enforcement mode. |

The custom installers target conventional Arch/Garuda, Fedora and Debian/Ubuntu
systems. They reject OSTree/Atomic systems. Feature-specific checks may narrow
support further. Python 3 is required for configuration installers; Git is
installed through the native package manager when missing.

Myfish and dotfiles are downloaded at explicit Git commit IDs recorded in
`core/tabs/commander/common.sh`. Downloads live under
`$XDG_DATA_HOME/commander-linutil/sources` (normally `~/.local/share/...`).
Cached revisions and local edits are checked before reuse. Update the pins
when adopting a reviewed revision of your repositories.

## DaVinci Resolve

The two Resolve entries are under **Applications Setup > Design Tools**. Native
installation uses distro packages; Davincibox builds a separate runtime environment.
Davincibox also accepts Debian, Ubuntu and derivatives. Both require the official Linux `.run` installer and a working host GPU driver.
The installers include library compatibility launchers and dependency checks.

See the [Resolve guide](resolve.md) for GPU prerequisites, license acceptance,
container disk requirements, recovery and the video/CTT references. GPU playback
has not been validated on real hardware across the supported distros.

## Configuration ownership and portability

- Myfish owns shell installation. Dotfiles installation is component-based;
  it does not activate your complete Garuda Home Manager profile, Restic
  services, machine settings, or system snapshots. Fastfetch is installed when missing; install other application packages
  separately. Neovim's plugins and Konsole's configured font may need their
  normal first-run setup.
- User configuration files/directories receive adjacent timestamped backups.
  Symlink-managed destinations (including Home Manager) are rejected: update
  their owning configuration instead. A failed copy restores the previous target.
- Topgrade starts from your template. Garuda keeps `garuda_update`; other distros
  use autodetection. Update confirmation is enabled. Machine-specific flake
  arguments and repository paths are omitted; add editable repositories to
  your installed `topgrade.toml` as needed. Pinned installer sources are not
  automatically updated by Topgrade.
- Fastfetch installs ImageMagick (`imagemagick` on Arch/Debian/Ubuntu,
  `ImageMagick` and `ImageMagick-libs` on Fedora), installs Fastfetch if missing,
  and checks the selected binary for ImageMagick backend support. Direct PNG
  protocols can work without that compiled backend; Sixel/encoded Kitty need it.
  The installer copies the pinned dotfiles layout: labeled colored boxes, a Board
  row, Pac-Man colors, the Arch PNG, and both Revan images as optional backups.
  A user launcher and shell shortcut select the current distro PNG on every run
  and choose a compatible terminal protocol. The layout stays the same across
  distros; an unrecognized distribution uses a system-provided or generic Linux PNG.
  No image download is needed at runtime. Kitty/Ghostty use Kitty graphics,
  Konsole/WezTerm use iTerm graphics, and Foot/MLTerm use Sixel. Terminals without
  a recognized image protocol show the details without an ASCII logo.
  Image support must be available in the terminal and Fastfetch build;
  [Fastfetch's logo documentation](https://github.com/fastfetch-cli/fastfetch/wiki/Logo-options)
  describes the requirements. Explicit `--config` and logo options override
  automatic selection. Reopen the terminal after installation. The installer
  backs up the existing Fastfetch configuration, launcher and shell startup file.
  Remove the marked shell shortcut and restore those backups to undo installation.
- GRUB requires an existing installation and its menu generator/syntax checker.
  Themes include your custom theme, Catppuccin Mocha, Dracula, Tela, Vimix,
  and seven presets from ChrisTitusTech/bootloader-themes.
  Assets are fetched at pinned commits and installed under the active GRUB boot
  directory, so a separate `/boot` can access them. Tela/Vimix offer 1080p, 2K
  and 4K asset sizes. The installer enables graphical terminal output; explicit
  `GRUB_TERMINAL` settings and conflicting appearance drop-ins require manual
  resolution first. Existing kernel, disk, timeout and boot-entry settings stay.
  It retains previous theme directories, backs up defaults and boot menu, generates a temporary boot menu,
  checks syntax, and replaces the live menu only on success. Failed generation
  restores the previous defaults. Fedora uses `/boot/grub2/grub.cfg`, never the
  EFI stub. **Restore Default GRUB Appearance** clears custom theme/background
  settings and selects the plain console menu; it does not recover an original
  distro-branded theme or reinstall the bootloader. Theme files remain available
  if you want to reapply one.
- SDDM requires 0.21+, the Qt6 greeter, an existing SDDM setup and a graphical
  desktop session. The preview must work before activation. A late drop-in is
  installed; `/etc/sddm.conf`, when present, is also backed up and its theme
  settings updated because it takes precedence. SDDM is never restarted.
  Existing theme, fonts and configuration get adjacent backups; copied assets
  can remain after a cancelled preview.
- AppArmor does not edit boot arguments. If the kernel has not enabled it,
  follow your distro's setup instructions and reboot first. Fedora keeps
  SELinux. Myfish's native backend avoids its automatic Nix installer's
  documented SELinux restriction.

Theme files remain in the source dotfiles repository and retain their own
licenses; SilentSDDM is GPL-3.0-or-later. This fork downloads the assets rather
than relicensing them as MIT.

## Validation

```sh
python3 -B -m unittest discover -s tests -v
cargo test --locked --no-fail-fast --package linutil_core
cargo xtask docgen
shellcheck -x -P . core/tabs/commander/*.sh
checkbashisms core/tabs/commander/*.sh
git diff --check
```

Installer tests use fixtures and temporary directories. Actual boot menu,
login-screen and security-service changes still require VM testing on each
target distro before considering them production-tested.

### Debian Nala setup

The Debian submenu follows Arch and is visible only on Debian. Nala comes from
[Debian's repositories](https://packages.debian.org/stable/admin/nala).
The installer adds an interactive `apt` alias to your login shell configuration
(`.bashrc`, `$ZDOTDIR/.zshrc` or `.zshrc`, or Fish's configuration directory).
Open a new terminal after installation. Re-running does not duplicate the block.
Symlink-managed configuration is preserved and must be updated through its owner.

Use `apt search PACKAGE` or `apt list --installed` through Nala, and
`sudo nala install PACKAGE` for elevated operations. `sudo apt` and `/usr/bin/apt`
still invoke original APT. The installer does not replace executables or remove
APT, which Nala depends on. Linutil's shared package-manager detection already
prefers Nala when installed. Remove the marked alias block (or the dedicated Fish
file) to restore the previous interactive command behavior.

### Running commands

Highlight an executable entry and press Enter to open its confirmation prompt.
Press Y for Run / Install, or N/Escape to cancel. Both actions are displayed
inside the popup. Previews (P) and descriptions (D) close with Enter or Q;
then press Enter on the selected entry to run it. Installer-specific prompts
such as APPLY appear after the command starts.

### Additional GRUB theme sources

- [Catppuccin](https://github.com/catppuccin/grub): Mocha preset, MIT.
- [Dracula](https://github.com/dracula/grub): dark/purple theme, MIT.
- [Vince's GRUB2 themes](https://github.com/vinceliuice/grub2-themes): Tela and
  Vimix, GPL-3.0. Their asset composition follows the upstream installer, without
  executing its root-level configuration changes. Upstream licenses are copied
  with the downloaded themes. Source commits are pinned in `common.sh`.

- [Chris Titus Tech's bootloader themes](https://github.com/ChrisTitusTech/bootloader-themes):
  CyberRe, Cyberpunk, Shodan, Fallout, DedSec, Minegrub (Minecraft), and BSOL. Uses the bundled theme assets at a pinned commit, without
  running the upstream installer. Shodan fonts are also placed beside its
  theme file for GRUB font discovery. Minegrub uses the bundled static layout.
  Vimix comes from Vince's repository with selectable resolution assets.
  Restore Default works with all these themes.

These are established theme projects, not a claim of a precise popularity
ranking. Live boot appearance still needs VM or real-machine validation.
