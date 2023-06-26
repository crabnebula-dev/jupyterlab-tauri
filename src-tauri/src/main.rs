#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::{collections::HashMap, process::Child, sync::Mutex};

use anyhow::Result;
use rand::{distributions::Alphanumeric, Rng};
use tauri::{
    api::http::{ClientBuilder, HttpRequestBuilder},
    AppHandle, Manager, RunEvent, State, Window, WindowBuilder,
};

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
    // we run the installer only on the `init` window for security
    if window.label() == "init" {
        let port = portpicker::pick_unused_port()
            .ok_or_else(|| "failed to pick unused port".to_string())?;
        let token = rand::random::<usize>().to_string();

        let child = std::process::Command::new(
            app.path_resolver()
                .resolve_resource("launch.sh")
                .ok_or_else(|| "failed to find resource".to_string())?,
        )
        .args([&area, &project])
        .args([&token])
        .args([port.to_string()])
        .spawn()
        .map_err(|e| format!("failed to run launcher: {e}"))?;

        std::thread::sleep(std::time::Duration::from_secs(2));
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
        Err("cannot launch on this window".into())
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
