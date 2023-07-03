use anyhow::Result;
use security_framework::authorization::{
    Authorization, AuthorizationItemSetBuilder, Flags as AuthorizationFlags,
};
use std::collections::HashMap;
use std::ffi::OsStr;
use std::fs::create_dir_all;
use std::io::BufRead;
use std::path::{Path, PathBuf};
use tauri::api::path::home_dir;
use tauri::PathResolver;

use crate::gpython_framework_path;

fn exec_admin<E: AsRef<Path>, A: AsRef<OsStr>>(executable: E, args: &[A]) -> Result<()> {
    let rights = AuthorizationItemSetBuilder::new()
        .add_right("system.privilege.admin")?
        .build();
    let auth = Authorization::new(
        Some(rights),
        None,
        AuthorizationFlags::DEFAULTS
            | AuthorizationFlags::INTERACTION_ALLOWED
            | AuthorizationFlags::PREAUTHORIZE
            | AuthorizationFlags::EXTEND_RIGHTS,
    )?;
    let file = auth.execute_with_privileges_piped(
        executable.as_ref(),
        args,
        AuthorizationFlags::DEFAULTS,
    )?;
    for line in std::io::BufReader::new(file).lines().flatten() {
        println!("{}", line);
    }
    auth.destroy_rights();
    Ok(())
}

pub fn install_if_needed(path_resolver: PathResolver) -> Result<()> {
    if let Some(home) = home_dir() {
        let gennaker_path = home.join("Library").join("GennakerTauri");

        let projects_path = gennaker_path.join("projects");
        let libraries_path = gennaker_path.join("jupyter-libraries");
        let projects_exist = projects_path.exists();
        let libraries_exist = libraries_path.exists();

        let mut projects = HashMap::new();
        projects.insert(
            "Setup and Signatures",
            vec!["Quick Start", "Signatures", "Shared Libraries"],
        );
        projects.insert("Authoring", vec!["Scratchpad"]);
        projects.insert("Readings", vec!["Symbolic Math"]);

        let options = fs_extra::dir::CopyOptions::new();
        let venv_exists = if !projects_exist {
            create_dir_all(&projects_path)?;

            for (area, project_list) in &projects {
                for project in project_list {
                    let project_path = projects_path.join(area).join(project);
                    create_dir_all(&project_path)?;
                }
            }

            false
        } else {
            let mut exists = true;
            for (area, project_list) in &projects {
                for project in project_list {
                    let project_path = projects_path.join(area).join(project);
                    if !project_path.join(".v").join(".venv").exists() {
                        exists = false;
                        break;
                    }
                }
            }
            exists
        };

        if !gennaker_path.join("config").exists() {
            fs_extra::copy_items(
                &[path_resolver.resolve_resource("config").unwrap()],
                &gennaker_path,
                &options,
            )?;
        }

        if !libraries_exist {
            fs_extra::copy_items(
                &[path_resolver.resolve_resource("jupyter-libraries").unwrap()],
                &gennaker_path,
                &options,
            )?;
        }

        if !(venv_exists && libraries_exist) {
            std::env::set_var("GPYTHON_FRAMEWORK_PATH", gpython_framework_path()?);
            std::env::set_var(
                "PIP_LINKS_PATH",
                path_resolver
                    .resolve_resource("5_packed")
                    .expect("failed to resolve 5_packed"),
            );
            std::env::set_var("GENNAKER_PATH", &gennaker_path);
            exec_admin::<PathBuf, &str>(
                path_resolver
                    .resolve_resource("setup-venv.sh")
                    .expect("failed to resolve setup-venv.sh"),
                &[],
            )?;

            for (venv_resource_path, venv_target_path) in [
                ("quick_start", "Setup and Signatures/Quick Start"),
                ("signatures", "Setup and Signatures/Signatures"),
            ] {
                let target = projects_path.join(venv_target_path).join(".v");
                create_dir_all(&target)?;
                fs_extra::copy_items(
                    &[path_resolver
                        .resolve_resource(format!("venvs/{venv_resource_path}/.venv"))
                        .unwrap()],
                    target,
                    &options,
                )?;
            }
        }
    }

    Ok(())
}
