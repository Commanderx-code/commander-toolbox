import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('configure', ROOT / 'core/tabs/commander/configure.py')
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class ConfigurationTests(unittest.TestCase):
    def test_grub_preserves_boot_settings_and_is_repeatable(self):
        original = 'GRUB_CMDLINE_LINUX="root=UUID=target security=selinux"\nGRUB_TIMEOUT=7\nGRUB_THEME="old"\nGRUB_BACKGROUND="old"\n'
        rendered = configure.render_grub(original)
        self.assertIn('root=UUID=target security=selinux', rendered)
        self.assertIn('GRUB_TIMEOUT=7', rendered)
        self.assertEqual(rendered.count('GRUB_THEME='), 1)
        self.assertEqual(configure.render_grub(rendered), rendered)

    def test_topgrade_has_no_machine_paths_and_parses_on_both_distros(self):
        template = '''[misc]
assume_yes = true
[linux]
arch_package_manager = "garuda_update"
home_manager_arguments = ["--flake", @HOME_MANAGER_FLAKE@]
[git]
repos = [@DOTFILES_DIRECTORY@]
'''
        for distro in ('garuda', 'fedora', 'ubuntu'):
            parsed = tomllib.loads(configure.render_topgrade(template, distro))
            self.assertEqual(parsed['linux']['arch_package_manager'], 'garuda_update' if distro == 'garuda' else 'autodetect')
            self.assertFalse(parsed['misc']['assume_yes'])
            self.assertEqual(parsed['git']['repos'], [])
            self.assertNotIn('home_manager_arguments', parsed['linux'])

    def test_sddm_preserves_unrelated_settings_and_environment(self):
        rendered = configure.render_sddm('[Autologin]\nUser=test\n[Theme]\nCurrent=old\n[General]\nGreeterEnvironment=FOO=bar,QT_IM_MODULE=old\n')
        self.assertIn('User=test', rendered)
        self.assertIn('FOO=bar', rendered)
        self.assertIn('Current=commander-silent', rendered)
        self.assertEqual(rendered.count('QT_IM_MODULE='), 1)
        self.assertEqual(configure.render_sddm(rendered), rendered)

    def test_existing_file_is_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'config'
            target.write_text('old')
            configure.deploy(None, target, 'new')
            self.assertEqual(target.read_text(), 'new')
            self.assertEqual(next(Path(tmp).glob('config.commander-backup-*')).read_text(), 'old')

    def test_copy_failure_restores_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'config'
            target.write_text('old')
            with patch.object(configure.shutil, 'copy2', side_effect=OSError('copy failed')):
                with self.assertRaises(OSError):
                    configure.deploy(Path(tmp) / 'missing', target)
            self.assertEqual(target.read_text(), 'old')

    def test_symlink_and_symlink_parent_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real = base / 'managed'
            real.mkdir()
            (real / 'config').write_text('managed')
            link = base / 'link'
            link.symlink_to(real, target_is_directory=True)
            for target in (link, link / 'config'):
                with self.assertRaises(ValueError):
                    configure.deploy(None, target, 'bad')
            self.assertEqual((real / 'config').read_text(), 'managed')

    def test_setup_menus_expose_choices_before_execution(self):
        catalog = tomllib.loads((ROOT / 'core/tabs/applications-setup/tab_data.toml').read_text())
        menus = {entry['name']: entry for entry in catalog['data']}
        self.assertEqual(
            {entry['name'] for entry in menus['Myfish Shell Setup']['entries']},
            {'Myfish Fish (Native)', 'Myfish Bash (Native)', 'Myfish Zsh (Native)', 'Myfish Guided Setup'},
        )
        self.assertEqual(
            {entry['script'] for entry in menus['Dotfiles']['entries']},
            {f'../commander/dotfiles-{component}.sh' for component in ('nvim', 'fastfetch', 'starship', 'konsole', 'ghostty')},
        )
        for name in ('Myfish Shell Setup', 'Dotfiles'):
            self.assertNotIn('script', menus[name])
            self.assertFalse(menus[name]['multi_select'])

    def test_nala_alias_preserves_existing_config_and_is_idempotent(self):
        for shell in ('bash', 'zsh', 'fish'):
            original = '# personal settings\n'
            rendered = configure.render_nala_alias(original, shell)
            self.assertIn(original, rendered)
            self.assertEqual(rendered.count(configure.NALA_START), 1)
            self.assertEqual(configure.render_nala_alias(rendered, shell), rendered)
        with self.assertRaises(ValueError):
            configure.render_nala_alias(configure.NALA_START, 'bash')

    def test_nala_respects_shell_config_locations(self):
        home, config = Path('/example/home'), Path('/example/config')
        self.assertEqual(configure.nala_alias_target(home, config, 'bash'), home / '.bashrc')
        self.assertEqual(configure.nala_alias_target(home, config, 'fish'), config / 'fish/conf.d/zz-commander-nala.fish')
        with patch.dict(configure.os.environ, {'ZDOTDIR': '/example/zsh'}):
            self.assertEqual(configure.nala_alias_target(home, config, 'zsh'), Path('/example/zsh/.zshrc'))
        with self.assertRaises(ValueError):
            configure.nala_alias_target(home, config, 'unsupported')

    def test_nala_menu_is_debian_only_and_follows_arch(self):
        entries = tomllib.loads((ROOT / 'core/tabs/system-setup/tab_data.toml').read_text())['data']
        names = [entry['name'] for entry in entries]
        self.assertEqual(names.index('Debian'), names.index('Arch') + 1)
        debian = entries[names.index('Debian')]
        self.assertIn({'matches': True, 'data': {'containing_file': '/etc/os-release'}, 'values': ['ID=debian']}, debian['preconditions'])
        nala = next(entry for entry in debian['entries'] if entry['name'] == 'Nala Package Manager')
        self.assertFalse(nala['multi_select'])

    def test_entire_catalog_and_custom_script_paths(self):
        found = set()
        def visit(entries, directory):
            for entry in entries:
                forms = set(entry) & {'entries', 'script', 'command'}
                self.assertEqual(len(forms), 1, entry['name'])
                if 'entries' in entry:
                    visit(entry['entries'], directory)
                if 'script' in entry:
                    path = (directory / entry['script']).resolve()
                    self.assertTrue(path.is_file(), str(path))
                    if path.parent.name == 'commander':
                        found.add(entry['name'])
                        self.assertFalse(entry['multi_select'])
        for path in (ROOT / 'core/tabs').glob('*/tab_data.toml'):
            visit(tomllib.loads(path.read_text())['data'], path.parent)
        self.assertEqual(len(found), 34)


if __name__ == '__main__':
    unittest.main()
