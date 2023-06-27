#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::{
    collections::HashMap,
    env::current_exe,
    path::{Path, PathBuf, MAIN_SEPARATOR},
    process::{Child, Command},
    sync::Mutex,
};

use anyhow::Result;
use rand::{distributions::Alphanumeric, Rng};
use tauri::{
    api::http::{ClientBuilder, HttpRequestBuilder},
    AppHandle, Manager, RunEvent, State, Window, WindowBuilder,
};

mod installer;

struct JupyterProcess {
    child: Child,
    port: u16,
    token: String,
}

impl JupyterProcess {
    pub async fn stop(mut self) -> Result<()> {
        #[cfg(not(windows))]
        {
            let client = ClientBuilder::new().build()?;
            let request = HttpRequestBuilder::new(
                "POST",
                format!(
                    "http://localhost:${}/api/shutdown?_xsrf=${}",
                    self.port, self.token
                ),
            )?
            .header("Authorization", format!("token {}", self.token))?;
            client.send(request).await?;
        }

        let _ = self.child.kill();

        Ok(())
    }
}

struct JupyterProcessStore(Mutex<HashMap<u32, JupyterProcess>>);

#[tauri::command]
async fn launch(
    app: AppHandle,
    window: Window,
    store: State<'_, JupyterProcessStore>,
    area: String,
    project: String,
) -> Result<(), String> {
    do_launch(app, window, store, area, project)
        .await
        .map_err(|e| e.to_string())
}

async fn do_launch(
    app: AppHandle,
    window: Window,
    store: State<'_, JupyterProcessStore>,
    area: String,
    project: String,
) -> Result<()> {
    // we run the installer only on the `init` window for security
    if window.label() == "init" {
        let installed = installer::install_if_needed(app.path_resolver())?;

        let port = portpicker::pick_unused_port()
            .ok_or_else(|| anyhow::anyhow!("failed to pick unused port"))?;
        let token = rand::random::<usize>().to_string();

        let child = Command::new(
            app.path_resolver()
                .resolve_resource("launch.sh")
                .ok_or_else(|| anyhow::anyhow!("failed to find resource"))?,
        )
        .args([&area, &project])
        .args([&token])
        .args([port.to_string()])
        .env("GPYTHON_FRAMEWORK_PATH", gpython_framework_path()?)
        .spawn()
        .map_err(|e| anyhow::anyhow!("failed to run launcher: {e}"))?;

        std::thread::sleep(std::time::Duration::from_secs(if installed {
            8
        } else {
            3
        }));
        let _ = WindowBuilder::new(
            &app,
            rand::thread_rng()
                .sample_iter(&Alphanumeric)
                .take(7)
                .map(char::from)
                .collect::<String>(),
            tauri::WindowUrl::External(
                format!("http://localhost:{port}/lab?token={token}")
                    .parse()
                    .unwrap(),
            ),
        )
        .title("JupyterLab")
        .build();

        store
            .0
            .lock()
            .unwrap()
            .insert(child.id(), JupyterProcess { child, port, token });

        Ok(())
    } else {
        Err(anyhow::anyhow!("cannot launch on this window"))
    }
}

fn gpython_framework_path() -> Result<PathBuf> {
    if cfg!(dev) {
        Ok(PathBuf::from(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/gpython.framework"
        )))
    } else {
        let exe = current_exe()?;
        let exe_dir = exe.parent().expect("failed to get exe directory");
        let curr_dir = exe_dir.display().to_string();

        if curr_dir.ends_with(format!("{MAIN_SEPARATOR}target{MAIN_SEPARATOR}debug").as_str())
            || curr_dir.ends_with(format!("{MAIN_SEPARATOR}target{MAIN_SEPARATOR}release").as_str())
        {
            Ok(Path::new(&curr_dir)
                .join("..")
                .join("..")
                .join("gpython.framework")
                .canonicalize()?)
        } else {
            Ok(Path::new(&curr_dir)
                .join("..")
                .join("Frameworks")
                .join("gpython.framework")
                .canonicalize()?)
        }
    }
}

fn main() {
    // On macOS and Linux the PATH env variable a packaged app gets does not
    // contain all the information that is usually set in .bashrc, .bash_profile, etc.
    // The `fix-path-env` crate fixes the PATH variable
    let _ = fix_path_env::fix();

    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![launch])
        .manage(JupyterProcessStore(Default::default()))
        .setup(|app| {
            WindowBuilder::new(app, "init", Default::default())
                .title("JupyterLab")
                .build()?;

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                // stop the JupyterLab server on app exit
                let store = app.state::<JupyterProcessStore>();
                let _ = tauri::async_runtime::block_on(async move {
                    let mut store_ = store.0.lock().unwrap();
                    let keys = store_.keys().cloned().collect::<Vec<u32>>();
                    for k in keys {
                        let _ = store_.remove(&k).unwrap().stop().await;
                    }
                });
            }
        });
}
