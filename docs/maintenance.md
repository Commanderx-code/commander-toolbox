# Maintenance and recovery

## Toolbox Maintenance

Open **Utilities → Toolbox Maintenance**. These tools require Python 3.

- **System Diagnostics** reports the distribution, virtualization, disk space,
  GPU drivers, OpenCL/Vulkan tools, Secure Boot and graphics-device permissions.
  Missing tools are skipped without installing anything. You can save a report
  under `$XDG_STATE_HOME/commander-toolbox/diagnostics` (default
  `~/.local/state/commander-toolbox/diagnostics`). A successful report does not
  guarantee Resolve compatibility.
- **Config Backup Restore** lists timestamped `.commander-backup-*` backups in
  your home directory and configuration, local executable and application-data
  directories. Select a backup and confirm its destination. Your current config
  gets another backup, and the selected backup is preserved. Symlink-managed
  configurations and backups containing symlinks require manual restoration.
  This tool does not restore system or bootloader files.
- **Toolbox Updater** fetches the official repository's `main` branch and builds
  a release executable. It requires Git, Cargo and a clean local checkout;
  local edits, untracked files, detached HEADs and branches with local commits
  are refused. It never resets or discards your work. A failed build leaves
  the checkout updated but does not replace your installed executable.
  An existing script launcher is preserved; check that it points to the updated
  checkout. Otherwise, optional installation into `~/.local/bin` backs up the
  previous executable. Restart the toolbox to use the new version.
- **Installation History** lists action names and exit results. Failed actions
  stop a queued batch; later actions remain marked as not started. A running
  marker left by an interrupted session is not reported as success.

History is stored in private directories under
`$XDG_STATE_HOME/commander-toolbox/history` (default `~/.local/state`). It records
names and results automatically, without recording typed input or command bodies.
Set `COMMANDER_TOOLBOX_HISTORY=0` before starting the toolbox to disable recording.
If the directory is unwritable or symlink-managed, recording is skipped.

Press **L** after an action finishes to save its terminal output. The history
viewer can open saved logs. Output may include private information; review it
before sharing. Saved logs contain the terminal buffer retained by the interface,
not necessarily all output from a long-running command. With history disabled,
the existing temporary-log location is used. Logs and history are not pruned
automatically; remove old run directories manually when no longer needed.

## Driverless printers

Open **Utilities → Printers → Driverless Printer Setup**. This installs CUPS and
Avahi packages and enables their services on conventional systemd installations
of Fedora, Arch and Debian/Ubuntu. It lists discoverable IPP printers, then asks
for an `ipp://` or `ipps://` URI and a new queue name. Confirm the preview to
create an IPP Everywhere queue without sharing it or changing your default.
Existing queues are preserved.

Compatible Brother, HP, Epson, Canon and other network printers can use this
path; support depends on the printer model's IPP Everywhere/AirPrint capability.
Older models and USB-only printers may still need vendor-specific setup.
Discovery depends on your network and firewall; the script does not change
firewall rules. You can enter the printer's URI manually if discovery fails.
Manage or remove the queue through your desktop's printer settings or CUPS.

See the [CUPS administration guide](https://openprinting.github.io/cups/doc/admin.html)
for IPP Everywhere queue setup.

## Resolve maintenance

Open **Applications Setup → Design Tools → DaVinci Resolve Maintenance** to:

- Check the native runtime or inspect/check the `commander-resolve` container.
- Recreate native or container launchers with configuration backups.
- Remove the dedicated container after typing `REMOVE commander-resolve`.
- Read native uninstall guidance without automatically deleting a native install.

Export or back up your Resolve projects before removing a container. Its local
filesystem is deleted; shared home files and host GPU drivers remain. The desktop
launcher remains and will not launch until Resolve is installed again. Dependency
checks do not validate GPU acceleration, codecs or actual playback. See the
[Resolve guide](resolve.md) for prerequisites and installation methods.

Automated tests cover backup preservation, updater safeguards, command results,
launcher generation and mocked printer operations. Real printer discovery and
printing, GPU operation and distro-specific package installation require testing
on the target machine.
