use std::{
    io::BufReader,
    process::{Child, Command, Stdio},
    sync::Mutex,
};

use anyhow::Result;
use tauri::{
    api::http::{ClientBuilder, HttpRequestBuilder},
    AppHandle, Manager, WindowBuilder,
};

use crate::{installer::install_path, python_env::PythonEnvCommand};

pub struct JupyterProcess {
    child: Mutex<Child>,
    port: u16,
    token: String,
}

impl JupyterProcess {
    pub async fn stop(&self) -> Result<()> {
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

pub fn run(app: AppHandle, port: u16, token: String) -> Result<()> {
    let mut cmd = Command::new("python");
    if let Some(home) = tauri::api::path::home_dir() {
        cmd.current_dir(&home);
    }
    let mut child = cmd
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
        .add_env_to_path(&install_path(&app))
        .stderr(Stdio::piped())
        .spawn()?;

    let mut stderr = child.stderr.take().map(BufReader::new).unwrap();
    let mut running = false;
    let app_ = app.clone();
    let token_ = token.clone();
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
                    &app_,
                    "main",
                    tauri::WindowUrl::External(
                        format!("http://localhost:{port}/lab?token={token_}")
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

    app.manage(JupyterProcess {
        child: Mutex::new(child),
        port,
        token,
    });

    Ok(())
}
