#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::{
    io::BufReader,
    process::{Child, Command, Stdio},
    sync::Mutex,
};

use anyhow::Result;
use tauri::{
    api::http::{ClientBuilder, HttpRequestBuilder},
    AppHandle, Manager, RunEvent, Window, WindowBuilder,
};

mod installer;

struct JupyterProcess {
    child: Mutex<Child>,
    port: u16,
    token: String,
}

impl JupyterProcess {
    async fn stop(&self) -> Result<()> {
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

        // on Windows, jupyertlab-desktop actually uses `taskkill /PID $PID /T /F`
        let _ = self.child.lock().unwrap().kill();

        Ok(())
    }
}

#[tauri::command]
async fn install_and_restart(app: AppHandle, window: Window) -> Result<(), String> {
    if window.label() == "init" {
        installer::run_installer(&app, &window).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn main() {
    // On macOS and Linux the PATH env variable a packaged app gets does not
    // contain all the information that is usually set in .bashrc, .bash_profile, etc.
    // The `fix-path-env` crate fixes the PATH variable
    let _ = fix_path_env::fix();

    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![install_and_restart])
        .setup(|app| {
            let handle = app.handle();
            if installer::is_python_env_valid(&handle) {
                bootstrap_jupyterlab(handle)?;
            } else {
                WindowBuilder::new(app, "init", Default::default())
                    .title("JupyterLab - Setup Python Env")
                    .initialization_script(&format!(
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
                let jupyter = app.state::<JupyterProcess>();
                let _ = tauri::async_runtime::block_on(jupyter.stop());
            }
        });
}

fn bootstrap_jupyterlab(app: AppHandle) -> Result<()> {
    let port = portpicker::pick_unused_port()
        .ok_or_else(|| anyhow::anyhow!("failed to pick unused port"))?;
    let token = rand::random::<usize>().to_string();

    let child = run_jupyterlab(app.clone(), port, token.clone())?;
    app.manage(JupyterProcess {
        child: Mutex::new(child),
        port,
        token,
    });

    Ok(())
}

fn run_jupyterlab(app: AppHandle, port: u16, token: String) -> Result<Child> {
    let mut child = Command::new("python")
        .args([
            "-m",
            "jupyterlab",
            "--no-browser",
            "--expose-app-in-browser",
            // do not use any config file
            r#"--JupyterApp.config_file_name="""#,
            &format!("--ServerApp.port={port}"),
            r#"--ServerApp.allow_origin=" * ""#,
            // enable hidden files (let user decide whether to display them)
            "--ContentsManager.allow_hidden=True",
        ])
        .env("JUPYTER_TOKEN", &token)
        .stderr(Stdio::piped())
        .spawn()?;

    let mut stderr = child.stderr.take().map(BufReader::new).unwrap();
    let mut running = false;
    std::thread::spawn(move || {
        let mut buf = Vec::new();
        loop {
            buf.clear();
            match tauri::utils::io::read_line(&mut stderr, &mut buf) {
                Ok(s) if s == 0 => break,
                _ => (),
            }
            let message = String::from_utf8_lossy(&buf);
            println!("{message}");
            if message.contains("is running at") && !running {
                let _ = WindowBuilder::new(
                    &app,
                    "main",
                    tauri::WindowUrl::External(
                        format!("http://localhost:{port}/lab?token={token}")
                            .parse()
                            .unwrap(),
                    ),
                )
                .title("JupyterLab")
                .build();
                running = true;
            }
        }
    });

    Ok(child)
}
