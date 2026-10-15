import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'core/tabs/commander'
spec = importlib.util.spec_from_file_location('configure', TOOLS / 'configure.py')
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class KernelArgumentTests(unittest.TestCase):
    def test_words_are_added_once_and_other_settings_stay(self):
        original = 'GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3"\nGRUB_CMDLINE_LINUX="root=UUID=x"\n'
        rendered = configure.render_kernel_cmdline(original, 'add', ['splash'])
        self.assertEqual(rendered, 'GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3 splash"\nGRUB_CMDLINE_LINUX="root=UUID=x"\n')
        self.assertEqual(configure.render_kernel_cmdline(rendered, 'add', ['splash']), rendered)

    def test_words_are_removed_and_the_line_is_created_when_missing(self):
        rendered = configure.render_kernel_cmdline('GRUB_CMDLINE_LINUX_DEFAULT="quiet splash rhgb"\n', 'remove', ['splash', 'rhgb'])
        self.assertEqual(rendered, 'GRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
        self.assertEqual(configure.render_kernel_cmdline('GRUB_TIMEOUT=5\n', 'add', ['splash']),
                         'GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX_DEFAULT="splash"\n')
        self.assertEqual(configure.render_kernel_cmdline('', 'remove', ['splash']), 'GRUB_CMDLINE_LINUX_DEFAULT=""\n')

    def test_the_last_assignment_and_its_export_prefix_are_kept(self):
        original = 'GRUB_CMDLINE_LINUX_DEFAULT="old"\nexport GRUB_CMDLINE_LINUX_DEFAULT=\'quiet\'  # trailing\n'
        rendered = configure.render_kernel_cmdline(original, 'add', ['splash'])
        self.assertEqual(rendered, 'GRUB_CMDLINE_LINUX_DEFAULT="old"\nexport GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n')

    def test_unknown_actions_and_broken_quoting_are_refused(self):
        with self.assertRaises(ValueError):
            configure.render_kernel_cmdline('', 'toggle', ['splash'])
        with self.assertRaises(ValueError):
            configure.render_kernel_cmdline('GRUB_CMDLINE_LINUX_DEFAULT="quiet\n', 'add', ['splash'])


class MkinitcpioHookTests(unittest.TestCase):
    def test_plymouth_follows_udev_or_systemd_and_is_added_once(self):
        rendered = configure.render_mkinitcpio_hooks('# hooks\nHOOKS=(base udev autodetect encrypt filesystems)\n', 'add')
        self.assertEqual(rendered, '# hooks\nHOOKS=(base udev plymouth autodetect encrypt filesystems)\n')
        self.assertEqual(configure.render_mkinitcpio_hooks(rendered, 'add'), rendered)
        self.assertEqual(configure.render_mkinitcpio_hooks('HOOKS="base systemd autodetect"\n', 'add'),
                         'HOOKS=(base systemd plymouth autodetect)\n')
        self.assertEqual(configure.render_mkinitcpio_hooks('HOOKS=(keyboard)\n', 'add'), 'HOOKS=(plymouth keyboard)\n')

    def test_removal_and_missing_hooks(self):
        self.assertEqual(configure.render_mkinitcpio_hooks('HOOKS=(base udev plymouth autodetect)\n', 'remove'),
                         'HOOKS=(base udev autodetect)\n')
        with self.assertRaises(ValueError):
            configure.render_mkinitcpio_hooks('#HOOKS=(base udev)\nMODULES=()\n', 'add')


class BootSplashScriptTests(unittest.TestCase):
    """plymouth.sh runs against a fake root with the same transaction safety as the GRUB themes."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.defaults = self.root / 'etc/default/grub'
        self.defaults.parent.mkdir(parents=True)
        self.defaults.write_text('GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
        self.boot = self.root / 'boot/grub'
        self.boot.mkdir(parents=True)
        self.menu = self.boot / 'grub.cfg'
        self.menu.write_text('original boot menu')
        self.hooks = self.root / 'etc/mkinitcpio.conf'
        self.hooks.write_text('HOOKS=(base udev autodetect filesystems)\n')
        self.log = self.root / 'calls.log'
        script = (TOOLS / 'plymouth.sh').read_text()
        for path in ('/etc/default/grub', '/boot/grub', '/etc/mkinitcpio.conf'):
            script = script.replace(path, str(self.root) + path)
        (self.root / 'plymouth.sh').write_text(script)
        shutil.copy2(TOOLS / 'configure.py', self.root / 'configure.py')
        self.write_tool('grub-mkconfig', 'printf "new menu" > "$2"')
        self.write_tool('grub-script-check', 'exit 0')
        for tool in ('mkinitcpio', 'dracut-rebuild'):
            self.write_tool(tool, f'echo "{tool} $*" >> "$CALLS"')
        self.write_tool('plymouth-set-default-theme',
                        'if [ "$1" = --list ]; then printf "bgrt\\nspinner\\n"; elif [ $# -eq 0 ]; then echo bgrt; else echo "theme $1" >> "$CALLS"; fi')

    def write_tool(self, name, body):
        path = self.root / name
        path.write_text(f'#!/bin/sh\n{body}\n')
        path.chmod(0o755)

    def run_script(self, action, tools, stdin=''):
        # The fake helpers answer every confirmation and know only the listed tools.
        known = '|'.join(tools)
        (self.root / 'common.sh').write_text(f'''commander_init() {{ DTYPE=arch; PACKAGER=pacman; ESCALATION_TOOL=env; }}
checkCommandRequirements() {{ :; }}
command_exists() {{ case "$1" in {known}) return 0 ;; *) return 1 ;; esac; }}
confirm() {{ :; }}
install_packages() {{ echo "install $*" >> "$CALLS"; }}
backup_system() {{ backup="$1.backup"; cp -a "$1" "$backup"; }}
''')
        return subprocess.run(['sh', '-e', './plymouth.sh', action], cwd=self.root, input=stdin,
                              env=dict(os.environ, PATH=str(self.root) + ':' + os.environ['PATH'], CALLS=str(self.log)),
                              text=True, capture_output=True)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_enable_adds_the_hook_and_argument_then_rebuilds(self):
        result = self.run_script('on', ['mkinitcpio', 'grub-mkconfig'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.defaults.read_text(), 'GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n')
        self.assertEqual(self.hooks.read_text(), 'HOOKS=(base udev plymouth autodetect filesystems)\n')
        self.assertEqual(self.menu.read_text(), 'new menu')
        self.assertEqual(self.calls(), ['install plymouth', 'mkinitcpio -P'])
        self.assertTrue(self.defaults.with_name('grub.backup').is_file())
        self.assertTrue(self.hooks.with_name('mkinitcpio.conf.backup').is_file())

    def test_disable_removes_the_arguments_and_keeps_the_hook(self):
        self.defaults.write_text('GRUB_CMDLINE_LINUX_DEFAULT="quiet splash rhgb"\n')
        self.hooks.write_text('HOOKS=(base udev plymouth autodetect)\n')
        result = self.run_script('off', ['dracut-rebuild', 'mkinitcpio', 'grub-mkconfig'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.defaults.read_text(), 'GRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
        self.assertEqual(self.hooks.read_text(), 'HOOKS=(base udev plymouth autodetect)\n')
        self.assertEqual(self.menu.read_text(), 'new menu')
        self.assertEqual(self.calls(), [])

    def test_failed_generation_restores_the_defaults_and_menu(self):
        self.write_tool('grub-mkconfig', 'exit 1')
        result = self.run_script('on', ['dracut-rebuild', 'grub-mkconfig'])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.defaults.read_text(), 'GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
        self.assertEqual(self.menu.read_text(), 'original boot menu')
        self.assertEqual(list(self.boot.glob('.commander-grub.*')), [])
        self.assertNotIn('dracut-rebuild', self.calls())

    def test_theme_choice_is_applied_with_the_distro_rebuild_tool(self):
        result = self.run_script('theme', ['dracut-rebuild', 'mkinitcpio'], stdin='2\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ['theme spinner', 'dracut-rebuild '])
        self.assertEqual(self.defaults.read_text(), 'GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
        result = self.run_script('theme', ['dracut-rebuild'], stdin='9\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), ['theme spinner', 'dracut-rebuild '])

    def test_without_an_initramfs_tool_nothing_changes(self):
        result = self.run_script('on', ['grub-mkconfig'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No initramfs tool', result.stderr)
        self.assertEqual(self.defaults.read_text(), 'GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
        self.assertEqual(self.calls(), [])


if __name__ == '__main__':
    unittest.main()
