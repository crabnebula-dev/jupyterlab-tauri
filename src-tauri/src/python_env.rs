use std::{ffi::OsString, path::Path, process::Command};

fn path_with_python_env(env_path: &Path) -> crate::Result<OsString> {
    let mut paths = if let Some(path) = std::env::var_os("PATH") {
        std::env::split_paths(&path).collect::<Vec<_>>()
    } else {
        Vec::new()
    };

    #[cfg(windows)]
    {
        paths.insert(0, env_path.join("bin"));
        paths.insert(0, env_path.join("Scripts"));
        paths.insert(0, env_path.join("Library\\bin"));
        paths.insert(0, env_path.join("Library\\usr\\bin"));
        paths.insert(0, env_path.join("Library\\mingw-w64\\bin"));
        paths.insert(0, env_path.to_path_buf());
    }
    #[cfg(not(windows))]
    {
        paths.insert(0, env_path.join("bin"));
        paths.insert(0, env_path.to_path_buf());
    }

    let new_path = std::env::join_paths(paths)?;
    Ok(new_path)
}

pub trait PythonEnvCommand {
    /// Adds the given Python environment path to the `PATH`.
    fn add_env_to_path(&mut self, env_path: &Path) -> &mut Self;
}

impl PythonEnvCommand for Command {
    fn add_env_to_path(&mut self, env_path: &Path) -> &mut Self {
        if let Ok(path) = path_with_python_env(env_path) {
            self.env("PATH", path);
        }
        self
    }
}
