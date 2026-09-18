import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'core/tabs/commander'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('resolve_launcher', TOOLS / 'resolve-launcher.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class ResolveTests(unittest.TestCase):
    def test_launcher_quotes_paths_and_preserves_backups(self):
        with tempfile.TemporaryDirectory(prefix='resolve space ') as tmp:
            home = Path(tmp)
            data = home / 'data'
            launcher.install('native', home, data)
            path = home / '.local/bin/commander-resolve'
            old = path.read_text()
            self.assertIn(shlex.quote(str(data / 'commander-toolbox/resolve-runtime.sh')), old)
            launcher.install('container', home, data)
            self.assertEqual(next(path.parent.glob('*.commander-backup-*')).read_text(), old)
            self.assertIn('DBX_CONTAINER_MANAGER=podman', path.read_text())
            self.assertEqual(subprocess.run(['sh', '-n', str(path)]).returncode, 0)
            self.assertTrue(os.access(path, os.X_OK))

    def test_symlink_refused_before_any_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / '.local').symlink_to(home / 'managed')
            with self.assertRaises(ValueError):
                launcher.install('native', home, home / 'data')
            self.assertFalse((home / 'data').exists())

    def run_installer(self, mode='native', distro='fedora', failure=False, cancel=False, device=True, gpu='2', runtime_failure=False):
        with tempfile.TemporaryDirectory(prefix='resolve test ') as tmp:
            root = Path(tmp)
            for name in ('resolve.sh', 'resolve-launcher.py', 'configure.py'):
                shutil.copy2(TOOLS / name, root / name)
            # GPU/ELF checks are mocked; this fixture never runs the real vendor binary.
            helper = root / 'resolve-launcher.py'
            helper.write_text(helper.read_text().replace("if __name__ == '__main__':",
                "NATIVE = '#!/bin/sh\\nexit " + ("1" if runtime_failure else "0") + "\\n'\nif __name__ == '__main__':"))
            script = (root / 'resolve.sh').read_text().replace('/opt/resolve', str(root / 'opt/resolve'))
            (root / 'resolve.sh').write_text(script)
            (root / 'common.sh').write_text('''checkDistro() { DTYPE=$TEST_DISTRO; }
commander_init() { PACKAGER=$TEST_MANAGER; ESCALATION_TOOL=env; }
checkCommandRequirements() { :; }
command_exists() { command -v "$1" >/dev/null; }
confirm() { read -r answer; [ "$answer" = APPLY ] || exit 1; }
install_packages() { printf '%s\\n' "$*" >> "$HOME/packages"; }
fetch_source() { source_dir=$HOME; }
''')
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            (bin_dir / 'nvidia-smi').write_text('#!/bin/sh\nexit 0\n')
            (bin_dir / 'nvidia-ctk').write_text('#!/bin/sh\necho nvidia.com/gpu=all\n')
            (bin_dir / 'clinfo').write_text('#!/bin/sh\n' + ('echo "Device #0: Test GPU"\n' if device else 'exit 0\n'))
            (bin_dir / 'podman').write_text('''#!/bin/sh
printf '%s\n' "$*" >> "$HOME/containers"
[ "$1" != container ]
''')
            (bin_dir / 'distrobox').write_text('''#!/bin/sh -e
printf '%s\n' "$*" >> "$HOME/containers"
[ "$1" = enter ] || exit 0
shift 3
[ "$1" != -- ] || shift
[ "$1" != sudo ] || shift
exec "$@"
''')
            for p in bin_dir.iterdir():
                p.chmod(0o755)
            installer = root / 'DaVinci_Resolve_20.3_Linux.run'
            app = '#!/bin/sh\nexit 1\n' if failure else (
                '#!/bin/sh -e\nmkdir -p "$HOME/opt/resolve/bin"\ntouch "$HOME/opt/resolve/bin/resolve"\nchmod +x "$HOME/opt/resolve/bin/resolve"\n')
            installer.write_text("#!/bin/sh -e\nmkdir squashfs-root\nprintf %s " + shlex.quote(app) + ' > squashfs-root/AppRun\nchmod +x squashfs-root/AppRun\n')
            result = subprocess.run(['sh', '-e', './resolve.sh', mode], cwd=root,
                input=f'{installer}\n{gpu}\n' + ('NO\n' if cancel else 'APPLY\n'), text=True, capture_output=True,
                env=dict(os.environ, HOME=str(root), XDG_DATA_HOME=str(root / 'data'), DISPLAY=':1',
                         TEST_DISTRO=distro, TEST_MANAGER='pacman' if distro == 'arch' else 'dnf',
                         PATH=str(bin_dir) + ':' + os.environ['PATH']))
            successful = not (failure or runtime_failure or cancel or distro == 'debian' or (mode == 'native' and not device))
            self.assertEqual(result.returncode == 0, successful, result.stdout + result.stderr)
            self.assertEqual((root / '.local/bin/commander-resolve').exists(), successful)
            self.assertEqual(list(root.glob('.commander-resolve.*')), [])
            if successful and mode == 'native':
                packages = (root / 'packages').read_text()
                if gpu == '2':
                    self.assertIn('rocm-opencl-runtime' if distro == 'arch' else 'rocm-opencl', packages)
                elif gpu == '3':
                    self.assertIn('intel-compute-runtime', packages)
                else:
                    self.assertIn('opencl-nvidia' if distro == 'arch' else 'libnvidia-opencl.so.1', packages)
            if cancel or distro == 'debian':
                self.assertFalse((root / 'packages').exists())

    def test_fedora_native(self):
        self.run_installer()

    def test_arch_native(self):
        self.run_installer(distro='arch')

    def test_container(self):
        self.run_installer(mode='container')

    def test_vendor_failure_does_not_publish_launcher(self):
        self.run_installer(failure=True)
        self.run_installer(mode='container', failure=True)

    def test_unsupported_cancel_and_missing_gpu(self):
        self.run_installer(distro='debian')
        self.run_installer(cancel=True)
        self.run_installer(device=False)

    def test_nvidia_and_intel_paths(self):
        self.run_installer(gpu='1')
        self.run_installer(distro='arch', gpu='1')
        self.run_installer(mode='container', gpu='1')
        self.run_installer(gpu='3')

    def test_failed_library_check_does_not_publish_launcher(self):
        self.run_installer(runtime_failure=True)
        self.run_installer(mode='container', runtime_failure=True)
