<p align="center">
  <img src="docs/assets/banner.svg" alt="Commander Toolbox - Your Linux setup, in one place." width="960">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Linux-5eead4?style=flat-square" alt="Linux">
  <img src="https://img.shields.io/badge/interface-Terminal-86bbd8?style=flat-square" alt="Terminal interface">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-5e81ac?style=flat-square" alt="MIT license"></a>
  <a href="https://github.com/ChrisTitusTech/linutil"><img src="https://img.shields.io/badge/based_on-Linutil-a7b5c8?style=flat-square" alt="Based on Linutil"></a>
</p>

<p align="center">
  Set up your shell, bring your dotfiles, and make Linux feel like home.<br>
  A personalized toolbox built on Chris Titus Tech's Linutil.
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#what-you-get">Features</a> ·
  <a href="#platform-support">Platforms</a> ·
  <a href="docs/guide.md">Full guide</a> ·
  <a href="https://github.com/Commanderx-code/commander-toolbox/issues">Report an issue</a>
</p>

## What you get

Commander Toolbox brings personal setup tools into Linutil's terminal interface.
Choose individual components from organized menus, inspect their descriptions,
and confirm each installation before it runs.

| | Included |
| :--- | :--- |
| **A familiar shell** | Myfish setup for Fish, Bash and Zsh, with native packages or guided setup. |
| **Your configurations** | Individual Neovim, Fastfetch, Starship, Konsole and Ghostty configurations from Commander dotfiles. |
| **A visual system overview** | Fastfetch with automatic distro PNG logos, image dependencies and terminal detection. |
| **Boot and login themes** | Twelve GRUB themes, a plain GRUB restore option, and the Revan SDDM theme. |
| **Video editing** | Native or Davincibox setup for DaVinci Resolve on Fedora and Arch, with dependency installation and a compatibility launcher. |
| **Everyday maintenance** | A personalized Topgrade configuration and Debian Nala setup with an interactive `apt` alias. |
| **Security tools** | AppArmor setup on supported systems and SELinux tools for Fedora. |

The wider Linutil application and system-tool catalog remains available alongside
these custom menus.

## Quick start

You need **Git and a current Rust/Cargo toolchain**. Run as your normal user;
installers request elevated access when needed.

```sh
git clone https://github.com/Commanderx-code/commander-toolbox.git
cd commander-toolbox
cargo run --locked --package linutil_tui
```

**In the toolbox:** open a submenu, highlight an installable entry and press
**Enter**. Press **Y** to run or install; **N** or **Escape** cancels. Use **D**
for a description and **P** for a script preview. Some installers also ask you
to type `APPLY` before changing settings.

<details>
<summary><strong>Build a standalone executable</strong></summary>

```sh
cargo build --locked --release --package linutil_tui
./target/release/commander-toolbox
```

To install it for your user:

```sh
mkdir -p ~/.local/bin
install -m 755 target/release/commander-toolbox ~/.local/bin/commander-toolbox
```

Ensure `~/.local/bin` is on your `PATH`, then run `commander-toolbox`.

</details>

Use these source-build instructions for this fork. The inherited upstream
bootstrap scripts and package installers still target Linutil.

## Make it yours

| Open this menu | Choose your setup |
| :--- | :--- |
| **Applications Setup → Myfish Shell Setup** | Fish, Bash, Zsh or the guided installer. |
| **Applications Setup → Dotfiles** | Install only the application configurations you want. |
| **Applications Setup → Grub Theme** | Pick a theme or restore the plain GRUB menu. |
| **Applications Setup → SDDM Theme** | Preview the login theme before activation. |
| **System Setup → Debian → Nala Package Manager** | Add Nala and shell aliases while keeping the original APT executable. |
| **Security** | Select AppArmor or Fedora SELinux tools for your system. |

GRUB choices include **Commander, Catppuccin Mocha, Dracula, Tela, Vimix,
CyberRe, Cyberpunk, Shodan, Fallout, DedSec, Minegrub and BSOL**.
Tela and Vimix offer 1080p, 2K and 4K assets.

Fastfetch chooses the distro logo each time it runs. PNG display requires an
image-capable terminal and a compatible Fastfetch build. Reopen your terminal
after installation. [Image support and configuration details →](docs/guide.md#configuration-ownership-and-portability)

## Platform support

The custom installers target conventional Linux installations:

| Family | Package manager | Notes |
| :--- | :--- | :--- |
| Arch / Garuda | pacman | Native shell setup; Garuda-specific Topgrade updates. |
| Debian / Ubuntu | apt / Nala | The Nala setup menu itself is Debian-only. |
| Fedora | dnf | Native shell setup and SELinux tooling. |

Compatibility is checked per utility. Custom installers reject OSTree/Atomic
systems. GRUB needs an existing GRUB installation; SDDM needs an existing Qt6
setup with SDDM 0.21 or later. Configuration tools require Python 3.

Automated checks cover configuration rendering, installer fixtures and the Rust
interface. Boot appearance, login screens and security-service changes still need
VM or real-machine validation on each target distribution.

## Backups and recovery

Custom configuration installers create timestamped backups and preserve
symlink-managed configurations, including Home Manager files. GRUB changes retain
previous theme assets and validate the generated boot menu before replacing it.
**Restore Default GRUB Appearance** returns to a plain menu; it does not reinstall
GRUB or recover a distro's original branding.

[Read the full guide](docs/guide.md) for component behavior, backup locations,
Nala alias removal and theme requirements.

## Documentation and development

- [DaVinci Resolve setup](docs/resolve.md) — native and container installation requirements.
- [Full setup guide](docs/guide.md) — installation details, compatibility and recovery.
- [Command catalog](docs/content/userguide/walkthrough.md) — available utility entries.
- [Technical specification](SPEC.md) — architecture and behavior requirements.
- [Contributing](.github/CONTRIBUTING.md) — development workflow and validation.

## Credits and license

Built on [Chris Titus Tech's Linutil](https://github.com/ChrisTitusTech/linutil),
with the original history and [MIT license](LICENSE) retained. The interface
currently retains upstream logo artwork and internal Rust crate names.

Personal setup comes from [Myfish](https://github.com/Commanderx-code/Myfish)
and [Commander dotfiles](https://github.com/Commanderx-code/dotfiles).
Downloaded themes and logos retain their own licenses;
[theme sources and credits](docs/guide.md#additional-grub-theme-sources) are
listed in the guide.
