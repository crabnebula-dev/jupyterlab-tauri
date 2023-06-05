use std::{path::PathBuf, process::Command};

use crate::python_env::PythonEnvCommand;
use semver::Version;
use serde::Serialize;
use tauri::{api::ipc::CallbackFn, AppHandle, Window};

const REQUIRED_JUPYTERLAB_VERSION: Version = Version::new(3, 4, 5);

#[allow(dead_code)]
#[derive(Serialize)]
#[serde(tag = "event", content = "payload")]
enum InstallEvent {
    Exit(i32),
    Error(String),
    Stdout(String),
    Stderr(String),
}

/// Checks if the JupyterLab is installed in the custom Python env path.
pub fn is_python_env_valid(app: &AppHandle) -> bool {
    let env_path = install_path(app);
    if !env_path.exists() {
        return false;
    }

    match Command::new("python")
        .args(["-m", "jupyterlab", "--version"])
        .add_env_to_path(&env_path)
        .output()
    {
        Ok(output) => {
            let version_str = String::from_utf8_lossy(&output.stdout);
            if let Ok(version) = semver::Version::parse(version_str.trim()) {
                let valid = version > REQUIRED_JUPYTERLAB_VERSION;
                if !valid {
                    eprintln!("jupyterlab version {version_str} does not match required {REQUIRED_JUPYTERLAB_VERSION}");
                }
                valid
            } else {
                eprintln!(
                    "`python -m jupyterlab --version` returned an invalid version: {version_str}"
                );
                false
            }
        }
        Err(e) => {
            eprintln!("Failed to run `python -m jupyterlab --version`: {e}");
            false
        }
    }
}

/// Installer path is `$HOME/Library/org.jupyter.lab/jupyterServer` on macOS.
#[cfg(target_os = "macos")]
pub fn install_path(app: &AppHandle) -> PathBuf {
    tauri::api::path::home_dir()
        .expect("failed to resolve home dir")
        .join("Library")
        .join(&app.config().tauri.bundle.identifier)
        .join("jupyterServer")
}

/// Installer path:
/// - `$XDG_DATA_HOME/org.jupyter.lab/jupyterServer` or `$HOME/.local/share/org.jupyter.lab/jupyterServer` or `$HOME/jupyterServer` on Linux.
/// `{FOLDERID_LocalAppData}/org.jupyter.lab/jupyterServer` or `{FOLDERID_Profile}/jupyterServer` on Windows.
#[cfg(not(target_os = "macos"))]
pub fn install_path(app: &AppHandle) -> PathBuf {
    app.path_resolver()
        .app_local_data_dir()
        .or_else(tauri::api::path::home_dir)
        .expect("failed to resolve install path")
        .join("jupyterServer")
}

/// Executes the installer.
pub fn run_installer(
    _app: &AppHandle,
    window: Window,
    on_event_fn: CallbackFn,
) -> crate::Result<bool> {
    let emit_event = move |event: InstallEvent| {
        let js = tauri::api::ipc::format_callback(on_event_fn, &event)
            .expect("unable to serialize CommandEvent");
        let _ = window.eval(&js);
    };

    std::thread::spawn(move || {
        for i in 1..50 {
            std::thread::sleep(std::time::Duration::from_secs(2));
            emit_event(InstallEvent::Stdout(format!("Running... {i}")));
        }
        emit_event(InstallEvent::Exit(0));
    });

    Ok(true)
}
