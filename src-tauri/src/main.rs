#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use anyhow::Result;
use tauri::{api::ipc::CallbackFn, AppHandle, Manager, RunEvent, Window, WindowBuilder};

mod installer;
mod jupyterlab;
mod python_env;

#[tauri::command]
async fn run_installer(
    app: AppHandle,
    window: Window,
    on_event_fn: CallbackFn,
) -> Result<(), String> {
    // we run the installer only on the `init` window for securit
    if window.label() == "init" {
        installer::run_installer(&app, window, on_event_fn).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn main() {
    // On macOS and Linux the PATH env variable a packaged app gets does not
    // contain all the information that is usually set in .bashrc, .bash_profile, etc.
    // The `fix-path-env` crate fixes the PATH variable
    let _ = fix_path_env::fix();

    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![run_installer])
        .setup(|app| {
            let handle = app.handle();
            if installer::is_python_env_valid(&handle) {
                // JupyterLab is already installed; let's start it!
                let port = portpicker::pick_unused_port()
                    .ok_or_else(|| anyhow::anyhow!("failed to pick unused port"))?;
                let token = rand::random::<usize>().to_string();

                jupyterlab::run(handle, port, token)?;
            } else {
                // JupyterLab is not installed; let's open the installer window
                WindowBuilder::new(app, "init", Default::default())
                    .title("JupyterLab - Setup Python Env")
                    .initialization_script(&format!(
                        // pass the install path to the UI
                        "window.__PYTHON_ENV_INSTALL_PATH__ = {:?}",
                        installer::install_path(&handle)
                    ))
                    .build()?;
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                // stop the JupyterLab server on app exit
                if let Some(jupyter) = app.try_state::<jupyterlab::JupyterProcess>() {
                    let _ = tauri::async_runtime::block_on(jupyter.stop());
                }
            }
        });
}
