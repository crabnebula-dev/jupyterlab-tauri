use std::{
    fs::remove_dir_all,
    io::{BufReader, Read},
    path::PathBuf,
    process::{Command, Stdio},
    sync::Arc,
};

use crate::python_env::PythonEnvCommand;
use semver::Version;
use serde::Serialize;
use tauri::{api::ipc::CallbackFn, AppHandle, Window};

const REQUIRED_JUPYTERLAB_VERSION: Version = Version::new(3, 4, 5);

#[derive(Serialize)]
#[serde(tag = "event", content = "payload")]
enum InstallEvent {
    Exit(i32),
    Error(String),
    Stdout(String),
    Stderr(String),
}

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
            if let Ok(version) = semver::Version::parse(&version_str.trim()) {
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

#[cfg(target_os = "macos")]
pub fn install_path(app: &AppHandle) -> PathBuf {
    tauri::api::path::home_dir()
        .expect("failed to resolve home dir")
        .join("Library")
        .join(&app.config().tauri.bundle.identifier)
        .join("jupyterServer")
}

#[cfg(not(target_os = "macos"))]
pub fn install_path(app: &AppHandle) -> PathBuf {
    app.path_resolver()
        .app_local_data_dir()
        .or_else(tauri::api::path::home_dir)
        .expect("failed to resolve install path")
        .join("jupyterServer")
}

pub fn run_installer(
    app: &AppHandle,
    window: Window,
    on_event_fn: CallbackFn,
) -> crate::Result<bool> {
    let platform = if cfg!(target_os = "linux") {
        "Linux"
    } else if cfg!(target_os = "macos") {
        "MacOSX"
    } else if cfg!(windows) {
        "Windows"
    } else {
        panic!("unsupported platform")
    };

    let arch = if cfg!(target_arch = "aarch64") {
        "arm64"
    } else {
        "x86_64"
    };

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
            Some(&window),
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

    println!(
        "running installer {}, target {}",
        installer_path.display(),
        install_path.display()
    );

    let mut child = Command::new(&installer_path)
        .args(["-b", "-p"])
        .arg(&install_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let emit_event = move |event: InstallEvent| {
        let js = tauri::api::ipc::format_callback(on_event_fn, &event)
            .expect("unable to serialize CommandEvent");
        let _ = window.eval(&js);
    };
    let emit_event = Arc::new(emit_event);
    let emit_event_ = emit_event.clone();
    let emit_event__ = emit_event.clone();

    spawn_pipe_reader(child.stdout.take().unwrap(), move |event| {
        emit_event(InstallEvent::Stdout(event))
    });
    spawn_pipe_reader(child.stderr.take().unwrap(), move |event| {
        emit_event_(InstallEvent::Stderr(event))
    });

    std::thread::spawn(move || match child.wait() {
        Ok(status) => {
            emit_event__(InstallEvent::Exit(status.code().unwrap_or_default()));
        }
        Err(err) => {
            emit_event__(InstallEvent::Error(err.to_string()));
        }
    });

    Ok(true)
}

fn spawn_pipe_reader<R, F>(stream: R, f: F)
where
    R: Read + Send + 'static,
    F: Fn(String) + Send + 'static,
{
    let mut reader = BufReader::new(stream);
    std::thread::spawn(move || loop {
        let mut buf = Vec::new();
        match tauri::utils::io::read_line(&mut reader, &mut buf) {
            Err(err) => {
                eprintln!("Error reading from stream: {err}");
                break;
            }
            Ok(size) => {
                if size == 0 {
                    break;
                } else {
                    f(String::from_utf8_lossy(&buf).into_owned());
                }
            }
        }
    });
}
