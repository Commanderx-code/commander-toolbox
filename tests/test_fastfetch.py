import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'core/tabs/commander' / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

runtime = load('runtime', 'fastfetch-distro.py')
configure = load('configure', 'configure.py')


class FastfetchTests(unittest.TestCase):
    def test_distros_select_distinct_real_pngs(self):
        logos = ROOT / 'core/tabs/commander/fastfetch-logos'
        for distro in ('debian', 'fedora', 'arch', 'ubuntu', 'linuxmint', 'gentoo'):
            logo = runtime.distro_logo({'ID': distro}, logos)
            self.assertEqual(logo.name, distro + '.png')
            self.assertEqual(logo.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(runtime.distro_logo({'ID': 'unknown'}, logos).name, 'linux.png')
        self.assertEqual(runtime.distro_logo({'ID': '../escape'}, logos).name, 'linux.png')

    def test_distribution_provided_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pixmaps').mkdir()
            image = root / 'pixmaps/custom-logo.png'
            image.write_bytes(b'fixture')
            self.assertEqual(runtime.distro_logo({'ID': 'custom', 'LOGO': 'custom-logo'}, root, root), image)

    def test_protocols_and_user_overrides(self):
        for env, protocol in [({'KONSOLE_VERSION': '250400'}, 'iterm'), ({'TERM': 'xterm-ghostty'}, 'kitty-direct'), ({'TERM': 'foot'}, 'sixel'), ({'TERM': 'linux'}, 'none'), ({'KITTY_WINDOW_ID': '1', 'SSH_CONNECTION': 'host'}, 'kitty')]:
            self.assertEqual(runtime.image_protocol(env), protocol)
        self.assertEqual(runtime.logo_arguments(['--logo-type=none'], {}, Path('/missing')), [])
        self.assertEqual(runtime.logo_arguments(['--config', 'mine.jsonc'], {}, Path('/missing')), [])
        self.assertEqual(runtime.logo_arguments([], {}, Path('/missing')), ['--logo-type', 'none'])

    def test_wrapper_is_skipped_when_finding_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in ('wrapper', 'real'):
                (root / directory).mkdir()
            wrapper = root / 'wrapper/fastfetch'
            wrapper.write_bytes(b'#!/usr/bin/env python3\n# ' + runtime.MARKER)
            real = root / 'real/fastfetch'
            real.write_text('#!/bin/sh\nexit 0\n')
            wrapper.chmod(0o755)
            real.chmod(0o755)
            self.assertEqual(runtime.real_fastfetch(str(wrapper.parent) + ':' + str(real.parent)), str(real))
            with self.assertRaises(ValueError):
                runtime.real_fastfetch(str(wrapper.parent))

    def test_shell_shortcut_is_repeatable_and_quoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            launcher = home / 'space dir/fastfetch'
            for shell in ('bash', 'fish', 'zsh'):
                with patch.dict(os.environ, {'ZDOTDIR': str(home)}):
                    target, text = configure.fastfetch_shell_config(home, home / '.config', shell, launcher)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(text)
                    self.assertEqual(configure.fastfetch_shell_config(home, home / '.config', shell, launcher)[1], text)

    def test_os_release_is_parsed_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'os-release'
            path.write_text('ID="debian"\nLOGO=debian-logo\nOTHER=$(touch /tmp/not-executed)\n')
            self.assertEqual(runtime.read_os_release(path), {'ID': 'debian', 'LOGO': 'debian-logo'})


if __name__ == '__main__':
    unittest.main()
