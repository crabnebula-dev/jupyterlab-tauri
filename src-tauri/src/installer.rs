use std::{
    ffi::OsString,
    fs::remove_dir_all,
    path::{Path, PathBuf},
    process::Command,
};

use semver::Version;
use tauri::{AppHandle, Window};

const REQUIRED_JUPYTERLAB_VERSION: Version = Version::new(3, 4, 5);

fn path_with_python_env(env_path: &Path) -> crate::Result<OsString> {
    let mut paths = if let Some(path) = std::env::var_os("PATH") {
        std::env::split_paths(&path).collect::<Vec<_>>()
    } else {
        Vec::new()
    };

    #[cfg(windows)]
    {
        paths.push(env_path.to_path_buf());
        paths.push(env_path.join("Library\\mingw-w64\\bin"));
        paths.push(env_path.join("Library\\usr\\bin"));
        paths.push(env_path.join("Library\\bin"));
        paths.push(env_path.join("Scripts"));
        paths.push(env_path.join("bin"));
    }
    #[cfg(not(windows))]
    {
        paths.push(env_path.to_path_buf());
        paths.push(env_path.join("bin"));
    }

    let new_path = std::env::join_paths(paths)?;
    Ok(new_path)
}

trait PythonEnvCommand {
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

pub fn is_python_env_valid(app: &AppHandle) -> bool {
    let env_path = install_path(app);
    if !env_path.exists() {
        return false;
    }

    if let Ok(output) = Command::new("python")
        .args(["-m", "jupyterlab", "--version"])
        .add_env_to_path(&env_path)
        .output()
    {
        let version_str = String::from_utf8_lossy(&output.stdout);
        if let Ok(version) = semver::Version::parse(&version_str.trim()) {
            version > REQUIRED_JUPYTERLAB_VERSION
        } else {
            false
        }
    } else {
        false
    }
}

pub fn install_path(app: &AppHandle) -> PathBuf {
    app.path_resolver()
        .app_local_data_dir()
        .or_else(tauri::api::path::home_dir)
        .expect("failed to resolve install path")
        .join("jupyterServer")
}

pub fn run_installer(app: &AppHandle, window: &Window) -> crate::Result<bool> {
    let platform = if cfg!(target_os = "linux") {
        "Linux"
    } else if cfg!(target_os = "macos") {
        "MacOSX"
    } else if cfg!(windows) {
        "Windows"
    } else {
        panic!("unsupported platform")
    };

    let arch = "x86_64";

    let ext = if cfg!(windows) { "exe" } else { "sh" };

    let installer_path = app
        .path_resolver()
        .resolve_resource(format!(
            "JupyterLabDesktopAppServer-{}-{}-{}.{}",
            app.package_info().version,
            platform,
            arch,
            ext
        ))
        .expect("failed to resolve installer path");

    let install_path = install_path(app);

    if install_path.exists() {
        let confirmed = tauri::api::dialog::blocking::confirm(
            Some(window),
            "Do you want to overwrite?",
            format!(
                "Install path ({}) is not empty. Would you like to overwrite it?",
                install_path.display()
            ),
        );
        if confirmed {
            remove_dir_all(&install_path)?;
        } else {
            return Ok(false);
        }
    }

    println!("running installer {}", installer_path.display());

    let status = Command::new(&installer_path)
        .args(["-b", "-p"])
        .arg(&install_path)
        .status()?;

    if status.success() {
        app.restart();
    }

    Ok(true)
}
