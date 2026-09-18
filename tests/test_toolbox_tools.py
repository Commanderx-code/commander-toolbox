import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'core/tabs/commander'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('toolbox_tools', TOOLS / 'toolbox-tools.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class MaintenanceTests(unittest.TestCase):
    def test_restore_keeps_current_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / '.config/example'
            config.parent.mkdir()
            config.write_text('current')
            source = config.with_name(config.name + '.commander-backup-20260918000000')
            source.write_text('old')
            with patch.dict(os.environ, XDG_CONFIG_HOME=str(config.parent), XDG_DATA_HOME=str(home / '.local/share')):
                self.assertEqual(tools.discover_backups(home), [source])
            tools.restore_backup(source)
            self.assertEqual(config.read_text(), 'old')
            self.assertEqual(source.read_text(), 'old')
            self.assertIn('current', [p.read_text() for p in config.parent.glob('*.commander-backup-*')])

    def test_restore_refuses_links_inside_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'config.commander-backup-20260918'
            source.mkdir()
            (source / 'managed').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                tools.restore_backup(source)
            self.assertFalse((Path(tmp) / 'config').exists())

    def test_terminal_controls_are_not_replayed(self):
        self.assertEqual(tools.safe_text('\x1b[31mHello\x1b[0m\x1b]52;c;secret\x07\r\x00'), 'Hello')

    def test_diagnostics_do_not_install_missing_tools(self):
        with patch.object(tools.shutil, 'which', return_value=None), patch.object(tools, 'run') as run, \
             patch('builtins.input', return_value=''), patch('builtins.print'):
            tools.diagnostics()
            run.assert_not_called()

    def test_container_launcher_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, HOME=tmp, XDG_DATA_HOME=tmp + '/data'), \
                 patch.object(tools, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                 patch('builtins.input', side_effect=['4', 'APPLY']):
                tools.resolve_maintenance()
            self.assertIn('commander-resolve', (Path(tmp) / '.local/bin/commander-resolve').read_text())
            self.assertTrue((Path(tmp) / 'data/applications/commander-resolve.desktop').is_file())

    def test_container_removal_requires_exact_confirmation(self):
        with patch.object(tools, 'run') as run, patch('builtins.input', side_effect=['5', 'NO']):
            with self.assertRaises(ValueError):
                tools.resolve_maintenance()
            self.assertFalse(any('rm' in call.args[0] for call in run.call_args_list))

    def setup_repo(self, root):
        seed, repo, remote = root / 'seed', root / 'repo', root / 'remote'
        def git(*args, cwd=None):
            subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)
        git('init', '--bare', str(remote))
        git('init', '-b', 'main', str(seed))
        git('config', 'user.email', 'test@example.invalid', cwd=seed)
        git('config', 'user.name', 'Test', cwd=seed)
        (seed / 'README').write_text('one')
        git('add', '.', cwd=seed)
        git('commit', '-m', 'initial', cwd=seed)
        git('remote', 'add', 'origin', str(remote), cwd=seed)
        git('push', 'origin', 'main', cwd=seed)
        git('clone', '-b', 'main', str(remote), str(repo))
        (seed / 'README').write_text('two')
        git('commit', '-am', 'update', cwd=seed)
        git('push', 'origin', 'main', cwd=seed)
        return repo

    def test_updater_fast_forwards_and_build_failure_preserves_installed_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.setup_repo(root)
            installed = root / 'installed'
            installed.write_text('previous executable')
            original_git, original_run = tools.git, tools.run
            def git(path, *args):
                if args == ('remote', 'get-url', 'origin'):
                    return 'https://github.com/Commanderx-code/commander-toolbox.git'
                return original_git(path, *args)
            def run(args, **kwargs):
                if args[0] == 'cargo':
                    raise subprocess.CalledProcessError(1, args)
                return original_run(args, **kwargs)
            with patch.object(tools, 'git', side_effect=git), patch.object(tools, 'run', side_effect=run), \
                 patch.object(tools, 'confirm'):
                with self.assertRaisesRegex(ValueError, 'build failed'):
                    tools.update_checkout(repo)
            self.assertEqual((repo / 'README').read_text(), 'two')
            self.assertEqual(installed.read_text(), 'previous executable')

    def test_updater_refuses_local_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.setup_repo(Path(tmp))
            (repo / 'README').write_text('my changes')
            with patch.object(tools, 'confirm') as confirm:
                with self.assertRaisesRegex(ValueError, 'Local changes'):
                    tools.update_checkout(repo)
                confirm.assert_not_called()
            self.assertEqual((repo / 'README').read_text(), 'my changes')


class PrinterTests(unittest.TestCase):
    def run_setup(self, queue='office', exists=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = (TOOLS / 'printer-driverless.sh').read_text()
            script = script.replace('. ../common-service-script.sh', '. ./service.sh')
            script = script.replace('/run/systemd/system', tmp)
            (root / 'printer.sh').write_text(script)
            (root / 'common.sh').write_text('''commander_init() { PACKAGER=dnf; ESCALATION_TOOL=env; }
confirm() { read -r answer; [ "$answer" = APPLY ] || exit 1; }
install_packages() { :; }
command_exists() { command -v "$1" >/dev/null; }
''')
            (root / 'service.sh').write_text('checkInitManager() { :; }\nstartAndEnableService() { :; }\n')
            (root / 'ippfind').write_text('#!/bin/sh\necho ipp://printer.local/ipp/print\n')
            (root / 'lpstat').write_text('#!/bin/sh\n[ "$EXISTS" = yes ] || [ -f "$HOME/queue" ]\n')
            (root / 'lpadmin').write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$HOME/queue"\n')
            for name in ('ippfind', 'lpstat', 'lpadmin'):
                (root / name).chmod(0o755)
            result = subprocess.run(['sh', '-e', './printer.sh'], cwd=root, text=True, capture_output=True,
                input=f'APPLY\nipp://printer.local/ipp/print\n{queue}\nAPPLY\n',
                env=dict(os.environ, HOME=tmp, EXISTS='yes' if exists else 'no', PATH=tmp + ':' + os.environ['PATH']))
            return result, (root / 'queue').read_text() if (root / 'queue').exists() else ''

    def test_driverless_queue(self):
        result, command = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('everywhere', command)
        self.assertIn('printer-is-shared=false', command)

    def test_existing_and_invalid_queues_preserved(self):
        for queue, exists in [('office', True), ('bad;command', False), ('-flag', False)]:
            result, command = self.run_setup(queue, exists)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(command, '')
