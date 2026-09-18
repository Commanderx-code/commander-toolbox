# DaVinci Resolve

Open **Applications Setup > Design Tools** and select **DaVinci Resolve - Native**
or **DaVinci Resolve - Davincibox**.

Native targets Fedora and Arch-family installations. Davincibox additionally
accepts Debian, Ubuntu and derivatives identified through `ID_LIKE` (including
Linux Mint). Both require x86_64 and a graphical X11/XWayland session. Atomic/OSTree systems are not supported by this integration.
Runtime checks still apply if your launcher exposes all catalog entries.

## Before installing

1. Download the Linux Free or Studio ZIP from [Blackmagic Design](https://www.blackmagicdesign.com/products/davinciresolve).
2. Extract it, and supply the full path to `DaVinci_Resolve_*_Linux.run` when asked.
   Paths containing spaces are supported. The toolbox does not redistribute Resolve.
3. Install a compatible host GPU driver and reboot if necessary. Choose NVIDIA,
   AMD ROCm or Intel OpenCL when prompted. ROCm and Intel compute support depend
   on the GPU generation. NVIDIA must pass `nvidia-smi`.
4. Read Blackmagic's license before confirming: the installation runs unattended
   with license acceptance after you type `APPLY`. Studio requires your own license.

## Choose a method

| | Native | Davincibox |
| --- | --- | --- |
| Application location | Host `/opt/resolve` | `/opt/resolve` inside `commander-resolve` |
| Dependencies | Fedora/Arch packages | Fedora-based container dependencies |
| Host additions | Runtime libraries and OpenCL packages | Podman, Distrobox, Git; NVIDIA Container Toolkit when needed |
| Disk use | Installer and application | Also a container image and build cache; allow several extra GB |
| Launch | DaVinci Resolve (Commander) | Same desktop entry, entering the container |

Native installs use Blackmagic's installer directly, not an AUR package. Do not
mix this with an AUR-managed installation. Existing native installations or a
container of the same name are refused rather than overwritten. Back up projects
before upgrades or removals. Installing a second method replaces the backed-up
Commander launcher to select that method; it does not remove the first installation.

## Debian and Ubuntu

Choose **DaVinci Resolve - Davincibox**. The toolbox refreshes APT metadata and
installs Podman, Distrobox, Git, uidmap, slirp4netns and fuse-overlayfs using APT
or Nala. Your enabled repositories must provide these packages; older releases
may need a newer distribution release. Resolve's libraries stay in the Fedora
container. Native Debian/Ubuntu installation is not implemented.

For NVIDIA, the installer offers the official toolkit APT repository with a
repository-specific signing key, then installs the toolkit. Existing standard
NVIDIA toolkit source lists are respected. CDI devices and a working host driver
are still required. For AMD, `rocm-podman-support` is installed if available;
otherwise check device permissions if the GPU cannot be accessed. Host GPU
access can require render/video group membership and logging out and back in.

These paths have mocked installer coverage, not real Debian/Ubuntu GPU validation.
Davincibox describes these distributions as community-supported.

## Dependencies and compatibility

Native package names are mapped separately for Fedora and Arch. Package-manager
prompts remain interactive; there is no automatic package removal or partial
Arch database refresh. The Fedora NVIDIA OpenCL packages must be available from
your already-configured driver repository. Missing packages stop installation.

The container is built locally from a pinned revision of
[Davincibox](https://github.com/zelikos/davincibox) recorded in
`core/tabs/commander/common.sh`. Its Fedora base and distro packages can change
between builds. AMD/Intel use the OpenCL image; NVIDIA uses CDI device passthrough.
On Fedora, the script offers to add [NVIDIA Container Toolkit's signed repository](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
when the toolkit is missing, then installs it. This needs a separate `APPLY`.
The script checks CDI device registration and stops with instructions if devices
are missing. It does not replace GPU kernel drivers or disable SELinux.

The installer extracts the AppImage before running it, avoiding a FUSE dependency.
The vendor package-name check is bypassed only after dependency installation.
The Commander launcher preloads system GLib/GObject/GIO/GModule/GdkPixbuf libraries
and selects Qt's X11 backend, following the library-conflict approach described by
[ArchWiki](https://wiki.archlinux.org/title/DaVinci_Resolve) and Davincibox.
Bundled libraries are not removed or overwritten. Use the **Commander** launcher
to receive these fixes; the vendor's native launcher is unchanged.

This covers common installation and GLib/Qt launch issues, not every Resolve
release, GPU, optional hardware panel, scripting dependency or companion program.
Linux codec restrictions, especially in the Free edition, still apply.
## Video and CTT reference

The supplied [Resolve 21 Fedora video](https://www.youtube.com/watch?v=DYFuZF7PaeM)
shows installing compatibility packages, bypassing vendor package-name checks,
and moving four bundled GLib-family libraries aside. The Commander launcher
addresses that library conflict through preloading, preserving the bundled files.
It additionally covers GThread/GdkPixbuf and checks for missing linked libraries
before publishing a success launcher.

[ChrisTitusTech/resolve-linux](https://github.com/ChrisTitusTech/resolve-linux),
reviewed at `0e9e5a28e26d63d890748817aae97d6aebec1bc0`, provides a similar preload
wrapper and Fedora library diagnostics. Its Fedora/Intel dependency lists informed
the runtime package coverage here. Its FFmpeg conversion and backup tools are
separate utilities; this installer does not execute those scripts.

The video also configures RPM Fusion, changes the host FFmpeg packages and installs
NVIDIA kernel drivers. This integration requires a working host driver first and
does not replace the host multimedia stack. Those system-wide changes are not a
universal fix for Resolve's own codec restrictions.

## Launch and maintenance

Run `~/.local/bin/commander-resolve`, or use **DaVinci Resolve (Commander)**.
Launchers and the runtime script receive timestamped adjacent backups; symlink-managed
destinations are refused. They live in `~/.local/bin`,
`$XDG_DATA_HOME/applications` and `$XDG_DATA_HOME/commander-toolbox` respectively
(`~/.local/share` by default).

A failed install can leave installed dependency packages or a partial container.
The script stops without publishing a success launcher; it does not delete the
container automatically. Inspect it with `podman logs commander-resolve` or
`distrobox enter --name commander-resolve`. Save projects before removing it.
Run `~/.local/bin/commander-resolve --check` for a linked-library check after a
successful installation. If the final check failed, resolve the reported package
dependencies before reinstalling; the vendor install may already be present.
For native removal, use Blackmagic's installed uninstaller. For container removal,
use `distrobox rm commander-resolve` after backing up needed data. Restore launcher
backups if switching to a previous setup. Containers share your home directory;
they are not security sandboxes or backups.

Installer orchestration and launcher generation are tested with mocks and temporary
files. Actual GPU acceleration, video playback and installation require testing
with Blackmagic's installer on each supported distribution.
