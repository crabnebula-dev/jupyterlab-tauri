# JupyterLab + Tauri

A desktop application for [JupyterLab](https://github.com/jupyterlab/jupyterlab), based on [Tauri](https://tauri.app/).

The application installs JupyterLab on its own Python environment. The env path is:
- `$HOME/Library/org.jupyter.lab/jupyterServer` on macOS.
- `$XDG_DATA_HOME/org.jupyter.lab/jupyterServer` or `$HOME/.local/share/org.jupyter.lab/jupyterServer` or `$HOME/jupyterServer` on Linux.
- `{FOLDERID_LocalAppData}/org.jupyter.lab/jupyterServer` or `{FOLDERID_Profile}/jupyterServer` on Windows.

## Build dependencies

- [conda](https://docs.conda.io)

  Install version 22.11.1 from the [archive](https://repo.anaconda.com/miniconda/).

- [(conda) Constructor](https://github.com/conda/constructor) to bundle JupyterLab Desktop Server into the stand-alone application. You can install Constructor using:

  ```bash
  conda install -c conda-forge constructor
  ```

  <details>
    <summary>Windows 10 requirement</summary>
    
    For some reason on Windows 10 the pillow package crashes on a missing _imagine_ DLL. So you will have to change the pillow version manually with the following command:
    
    ```bash
    conda install -c conda-forge pillow=9.0.0
    ```
  
  </details>

- NodeJS

  You can install from https://nodejs.org/en/download/ or run:

  ```bash
  conda install -c conda-forge nodejs
  ```

- Yarn

  Install using

  ```bash
  npm install --global yarn
  ```
