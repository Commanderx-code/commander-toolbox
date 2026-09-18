use std::{
    fs::{self, DirBuilder, OpenOptions},
    io::{self, Write},
    os::unix::fs::{DirBuilderExt, OpenOptionsExt, PermissionsExt},
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

pub fn quote(value: &str) -> String {
    format!("'{}'", value.replace('\'', "'\\''"))
}

pub fn private_directory(path: &Path) -> io::Result<()> {
    for ancestor in path.ancestors() {
        if ancestor.is_symlink() {
            return Err(io::Error::other("history directory is symlink-managed"));
        }
    }
    DirBuilder::new().recursive(true).mode(0o700).create(path)?;
    fs::set_permissions(path, fs::Permissions::from_mode(0o700))
}

pub fn create_at(base: &Path, names: &[&str]) -> io::Result<PathBuf> {
    private_directory(base)?;
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(io::Error::other)?;
    let path = base.join(format!("{}-{}", now.as_nanos(), std::process::id()));
    DirBuilder::new().mode(0o700).create(&path)?;
    for (index, name) in names.iter().enumerate() {
        for (extension, text) in [("name", *name), ("status", "pending")] {
            let mut file = OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(path.join(format!("{index:04}.{extension}")))?;
            writeln!(file, "{text}")?;
        }
    }
    Ok(path)
}

pub fn create(names: &[&str]) -> Option<PathBuf> {
    if std::env::var("COMMANDER_TOOLBOX_HISTORY").as_deref() == Ok("0") {
        return None;
    }
    let state = std::env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .or_else(|| {
            std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".local/state"))
        })?;
    create_at(&state.join("commander-toolbox/history"), names).ok()
}

pub fn wrap(command: &str, status: Option<&Path>) -> String {
    let record = status.map(|path| {
        let path = quote(&path.to_string_lossy());
        let finish = quote(&format!("rc=$?; printf '%s\\n' \"$rc\" > {path}; exit \"$rc\""));
        format!("printf 'running\\n' > {path}\ntrap {finish} 0\ntrap 'exit 130' INT\ntrap 'exit 143' TERM\ntrap 'exit 129' HUP\n")
    }).unwrap_or_default();
    format!("(\n{record}{command}\n)\nrc=$?\n[ \"$rc\" -eq 0 ] || exit \"$rc\"\n")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;

    #[test]
    fn action_failure_is_recorded_and_stops_the_queue() {
        let base =
            std::env::temp_dir().join(format!("toolbox-history-test-{}", std::process::id()));
        let history = create_at(&base, &["first", "second"]).unwrap();
        let first = history.join("0000.status");
        let second = history.join("0001.status");
        let script = wrap("sh -c 'exit 7'", Some(&first)) + &wrap("true", Some(&second));
        assert_eq!(
            Command::new("sh")
                .arg("-c")
                .arg(script)
                .status()
                .unwrap()
                .code(),
            Some(7)
        );
        assert_eq!(fs::read_to_string(&first).unwrap().trim(), "7");
        assert_eq!(fs::read_to_string(&second).unwrap().trim(), "pending");
        assert_eq!(
            fs::metadata(&first).unwrap().permissions().mode() & 0o777,
            0o600
        );
        fs::remove_dir_all(base).unwrap();
    }

    #[test]
    fn quoting_keeps_shell_metacharacters_literal() {
        let value = "spaces ' $(false) ; \" end";
        let result = Command::new("sh")
            .arg("-c")
            .arg(format!("printf %s {}", quote(value)))
            .output()
            .unwrap();
        assert!(result.status.success());
        assert_eq!(String::from_utf8(result.stdout).unwrap(), value);
    }
}
