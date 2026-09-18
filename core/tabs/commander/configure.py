#!/usr/bin/env python3
"""Render portable configuration; user-file writes always retain a backup."""
import configparser
import datetime
import io
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import sys
import tempfile


def check_destination(path):
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError(f'{candidate} is symlink-managed; update its owner instead.')


def deploy(source, destination, text=None):
    check_destination(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if destination.exists():
        stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        backup = destination.with_name(destination.name + '.commander-backup-' + stamp)
        destination.rename(backup)
        print(f'Backup: {backup}')
    try:
        if text is not None:
            destination.write_text(text)
        elif source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    except Exception:
        if destination.is_dir():
            shutil.rmtree(destination)
        elif destination.exists():
            destination.unlink()
        if backup:
            backup.rename(destination)
        raise
    print(f'Installed: {destination}')


def render_topgrade(text, distro):
    # Source templates refer to a particular workstation. Let Home Manager use
    # the target's own default configuration and keep pinned sources immutable.
    text = re.sub(r'home_manager_arguments\s*=\s*\[.*?\]', '', text, flags=re.S)
    text = re.sub(r'repos\s*=\s*\[.*?\]', 'repos = []', text, flags=re.S)
    if distro != 'garuda':
        text = text.replace('arch_package_manager = "garuda_update"', 'arch_package_manager = "autodetect"')
    text = text.replace('assume_yes = true', 'assume_yes = false')
    text = text.replace("# Don't ask for confirmation before each update.", '# Ask before updates in the portable toolbox profile.')
    text = text.replace("# Use Garuda's normal system update mechanism.", '# Use Garuda updates on Garuda; autodetect elsewhere.')
    text = text.replace('# Automatically update the dotfiles repository.', '# Add your own editable repositories here; pinned toolbox sources stay unchanged.')
    text = text.replace('# Home Manager flake.', '# Home Manager uses its normal configuration on this machine.')
    if '@HOME_MANAGER_FLAKE@' in text or '@DOTFILES_DIRECTORY@' in text:
        raise ValueError('Unresolved Topgrade template placeholders.')
    return text


def render_grub(text, theme='/usr/share/grub/themes/commander/theme.txt',
                background='/usr/share/grub/themes/commander/background.png'):
    # Change only appearance, never transplant kernel, timeout or disk settings.
    text = re.sub(r'^\s*(?:export\s+)?GRUB_(?:THEME|BACKGROUND|TERMINAL_OUTPUT)=.*\n?', '', text, flags=re.M)
    if theme and re.search(r'^\s*(?:export\s+)?GRUB_TERMINAL=', text, re.M):
        raise ValueError('GRUB_TERMINAL overrides graphics output. Configure this console/serial setting explicitly before applying a graphical theme.')
    output = 'gfxterm' if theme else 'console'
    return (text.rstrip() + '\nGRUB_THEME=' + json.dumps(theme)
            + '\nGRUB_BACKGROUND=' + json.dumps(background)
            + '\nGRUB_TERMINAL_OUTPUT=' + json.dumps(output) + '\n')


CTT_GRUB_THEMES = {'ctt-cyberre': 'CyberRe', 'ctt-cyberpunk': 'Cyberpunk', 'ctt-shodan': 'Shodan', 'ctt-fallout': 'fallout', 'ctt-dedsec': 'dedsec', 'ctt-minegrub': 'minegrub', 'ctt-bsol': 'bsol'}


def prepare_grub_theme(repo, destination, variant, resolution='1080p'):
    if variant == 'commander':
        source = repo / 'system-backup/grub/cachyos'
    elif variant == 'catppuccin':
        source = repo / 'src/catppuccin-mocha-grub-theme'
    elif variant == 'dracula':
        source = repo / 'dracula'
    elif variant in CTT_GRUB_THEMES:
        source = repo / 'themes' / CTT_GRUB_THEMES[variant]
    elif variant in ('tela', 'vimix'):
        if resolution not in ('1080p', '2k', '4k'):
            raise ValueError('Unsupported theme resolution.')
        destination.mkdir(parents=True)
        for font in (repo / 'common').glob('*.pf2'):
            shutil.copy2(font, destination / font.name)
        template = (repo / f'config/theme-{resolution}.txt').read_text()
        # Upstream references terminal_box textures that it does not ship.
        template = re.sub(r'^terminal-box:.*\n?', '', template, flags=re.M)
        (destination / 'theme.txt').write_text(template)
        shutil.copy2(repo / f'backgrounds/{resolution}/background-{variant}.jpg', destination / 'background.jpg')
        shutil.copytree(repo / f'assets/assets-color/icons-{resolution}', destination / 'icons')
        for image in (repo / f'assets/assets-select/select-{resolution}').glob('*.png'):
            shutil.copy2(image, destination / image.name)
        shutil.copy2(repo / f'assets/info-{resolution}.png', destination / 'info.png')
        source = None
    else:
        raise ValueError('Unknown GRUB theme.')
    if source:
        shutil.copytree(source, destination)
    # GRUB generators discover fonts beside theme.txt, not in nested folders.
    if variant == 'ctt-shodan':
        for font in (destination / 'fonts').glob('*.pf2'):
            shutil.copy2(font, destination / font.name)
    if (repo / 'LICENSE').is_file():
        shutil.copy2(repo / 'LICENSE', destination / 'LICENSE')
    if not (destination / 'theme.txt').is_file():
        raise ValueError('Theme is missing theme.txt.')



def render_sddm(text):
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read_string(text)
    for section in ('Theme', 'General'):
        if not parser.has_section(section):
            parser.add_section(section)
    parser['Theme']['Current'] = 'commander-silent'
    parser['General']['InputMethod'] = 'qtvirtualkeyboard'
    # Preserve unrelated greeter variables such as renderer settings.
    env = parser['General'].get('GreeterEnvironment', '').split(',')
    replacements = {
        'QML2_IMPORT_PATH': '/usr/share/sddm/themes/commander-silent/components/',
        'QT_IM_MODULE': 'qtvirtualkeyboard', 'QML_XHR_ALLOW_FILE_READ': '1',
    }
    env = [item for item in env if item and item.split('=', 1)[0] not in replacements]
    env.extend(f'{key}={value}' for key, value in replacements.items())
    parser['General']['GreeterEnvironment'] = ','.join(env)
    output = io.StringIO()
    parser.write(output, space_around_delimiters=False)
    return output.getvalue()


def install_dotfiles(repo, component, config, data):
    source = repo / 'configs' / component
    if component == 'konsole':
        for name in ('Garuda.profile', 'Sweet.colorscheme'):
            check_destination(data / 'konsole' / name)
        for name in ('Garuda.profile', 'Sweet.colorscheme'):
            deploy(source / name, data / 'konsole' / name)
        print('Select the Garuda profile in Konsole. Its font must be installed separately.')
    elif component == 'starship':
        deploy(source / 'starship.toml', config / 'starship.toml')
    elif component == 'ghostty':
        deploy(source / 'spotatui.conf', config / 'ghostty' / 'spotatui.conf')
    elif component == 'nvim':
        deploy(source, config / component)
    elif component == 'fastfetch':
        install_fastfetch(source, config)
    else:
        raise ValueError('Unsupported dotfiles component.')



def fastfetch_shell_config(home, config, shell, launcher):
    target = nala_alias_target(home, config, shell)
    if shell == 'fish':
        target = config / 'fish/conf.d/zz-commander-fastfetch.fish'
    check_destination(target)
    text = target.read_text() if target.exists() else ''
    start = '# BEGIN Commander Linutil Fastfetch PNG'
    end = '# END Commander Linutil Fastfetch PNG'
    if text.count(start) != text.count(end) or text.count(start) > 1:
        raise ValueError('Malformed Commander Fastfetch block.')
    if start in text:
        if text.index(end) < text.index(start):
            raise ValueError('Malformed Commander Fastfetch block.')
        text = text[:text.index(start)] + text[text.index(end) + len(end):].lstrip('\n')
    command = shlex.quote(str(launcher))
    if shell == 'fish':
        block = f'function fastfetch --wraps fastfetch\n    command {command} $argv\nend'
    else:
        block = 'alias fastfetch=' + shlex.quote(command)
    return target, text.rstrip() + '\n\n' + start + '\n' + block + '\n' + end + '\n'


def install_fastfetch(source, config):
    destination = config / 'fastfetch'
    launcher = Path.home() / '.local/bin/fastfetch'
    check_destination(destination)
    check_destination(launcher)
    shell = Path(os.environ.get('SHELL', '/bin/bash')).name
    shell_config, shell_text = fastfetch_shell_config(Path.home(), config, shell, launcher)
    check_destination(shell_config)
    resources = Path(__file__).resolve().parent
    # Prepare the entire config before replacing an existing installation.
    with tempfile.TemporaryDirectory(prefix='commander-fastfetch-') as directory:
        stage = Path(directory) / 'fastfetch'
        shutil.copytree(source, stage)
        logos = stage / 'commander-logos'
        shutil.copytree(resources / 'fastfetch-logos', logos)
        shutil.copy2(source / 'visuals/dr460nized-fastfetch.png', logos / 'garuda.png')
        path = stage / 'config.jsonc'
        settings = json.loads(path.read_text())
        # Keep the layout; the launcher chooses the distro PNG at runtime.
        settings['logo'] = {'type': 'none', 'width': 24}
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=4) + '\n')
        deploy(stage, destination)
    deploy(resources / 'fastfetch-distro.py', launcher)
    launcher.chmod(0o755)
    if not shell_config.exists() or shell_config.read_text() != shell_text:
        deploy(None, shell_config, shell_text)
    print('Installed Fastfetch PNG launcher: ' + str(launcher))
    print('Open a new terminal to activate the fastfetch shell shortcut.')
    print('PNG logos: Kitty/Ghostty, Konsole/WezTerm/iTerm, or Sixel terminals. Other terminals show details without a logo.')


NALA_START = '# BEGIN Commander Linutil Nala alias'
NALA_END = '# END Commander Linutil Nala alias'


def nala_alias_target(home, config, shell):
    if shell == 'bash':
        return home / '.bashrc'
    if shell == 'zsh':
        return Path(os.environ.get('ZDOTDIR', str(home))) / '.zshrc'
    if shell == 'fish':
        return config / 'fish/conf.d/zz-commander-nala.fish'
    raise ValueError('Nala alias setup supports Bash, Zsh and Fish login shells only.')


def render_nala_alias(text, shell):
    if text.count(NALA_START) != text.count(NALA_END) or text.count(NALA_START) > 1:
        raise ValueError('Malformed Commander Nala alias block; check the shell configuration.')
    if NALA_START in text:
        start, end = text.index(NALA_START), text.index(NALA_END)
        if end < start:
            raise ValueError('Malformed Commander Nala alias block.')
        text = text[:start] + text[end + len(NALA_END):].lstrip('\n')
    if shell == 'fish':
        block = "if status is-interactive; and command -q nala\n    alias apt 'nala'\nend"
    else:
        block = "case $- in\n    *i*) if command -v nala >/dev/null 2>&1; then alias apt='nala'; fi ;;\nesac"
    return text.rstrip() + '\n\n' + NALA_START + '\n' + block + '\n' + NALA_END + '\n'


def main():
    mode, path, *args = sys.argv[1:]
    source = Path(path)
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    if mode in ('nala-check', 'nala-alias'):
        shell = args[0]
        target = nala_alias_target(source, config, shell)
        check_destination(target)
        old = target.read_text() if target.exists() else ''
        rendered = render_nala_alias(old, shell)
        if mode == 'nala-alias' and rendered != old:
            deploy(None, target, rendered)
        elif mode == 'nala-check':
            print(f'Alias destination: {target}')
    elif mode == 'dotfiles':
        install_dotfiles(source, args[0], config, data)
    elif mode == 'topgrade':
        template = source / 'configs/topgrade/topgrade.toml'
        deploy(template, config / 'topgrade.toml', render_topgrade(template.read_text(), args[0]))
    elif mode == 'grub':
        print(render_grub(source.read_text(), *args), end='')
    elif mode == 'grub-prepare':
        prepare_grub_theme(source, Path(args[0]), args[1], args[2])
    elif mode == 'sddm':
        print(render_sddm(source.read_text()), end='')
    else:
        raise ValueError('Unknown configuration action.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        sys.exit(str(error))
