#!/bin/bash

# Environment vars for paths 
export GPYTHON_SP="/Library/Frameworks/gpython.framework/Versions/3.10/lib/python3.10/site-packages"
export GENNAKER="${HOME}/Library/Gennaker"
export GEN_JP_LIBRARIES="${GENNAKER}/jupyter-libraries"
export GEN_PROJECTS="${GENNAKER}/projects"
export GEN_SH_LIBRARIES="${GENNAKER}/projects/Setup and Signatures/Shared Libraries"

# Look first in current project, then jupyter-libraries, then gpython
PATH="/Library/Frameworks/gpython.framework/Versions/3.10/bin":${PATH}
PATH="${GEN_JP_LIBRARIES}/.venv/bin":${PATH}
PATH="${GEN_PROJECTS}/${1}/${2}/.v/.venv/bin":"${PATH}"
export PATH

# These will only be visible after starting the GUI from the command line
echo PATH 
echo
echo "${PATH}" 
echo 
echo Launch parameters 
echo area: "${1}"
echo project: "${2}"
echo 


if [ "${1}" = "Setup and Signatures" ]
    then 
    if [ "${2}" = "Shared Libraries" ]
        then  
        PYTHONPATH="${GPYTHON_SP}"
        PYTHONPATH="${GEN_JP_LIBRARIES}/.venv/lib/python3.10/site-packages":${PYTHONPATH}
        PYTHONPATH="${GEN_SH_LIBRARIES}/.v/.venv/lib/python3.10/site-packages":${PYTHONPATH}
        export PYTHONPATH
    else
        PYTHONPATH="${GPYTHON_SP}"
        PYTHONPATH="${GEN_JP_LIBRARIES}/.venv/lib/python3.10/site-packages":${PYTHONPATH}
        PYTHONPATH="${GEN_SH_LIBRARIES}/.v/.venv/lib/python3.10/site-packages":${PYTHONPATH}
        PYTHONPATH="${GEN_PROJECTS}/${1}/${2}/.v/.venv/lib/python3.10/site-packages":${PYTHONPATH}
        export PYTHONPATH
    fi 
else
    PYTHONPATH="${GPYTHON_SP}"
    PYTHONPATH="${GEN_JP_LIBRARIES}/.venv/lib/python3.10/site-packages":${PYTHONPATH}
    PYTHONPATH="${GEN_SH_LIBRARIES}/.v/.venv/lib/python3.10/site-packages":${PYTHONPATH}
    PYTHONPATH="${GEN_PROJECTS}/${1}/${2}/.v/.venv/lib/python3.10/site-packages":${PYTHONPATH}
    export PYTHONPATH
fi

source "${GEN_PROJECTS}/${1}/${2}/.v/.venv/bin/activate" 
export VIRTUAL_ENV_PROMPT="(.venv)"

export PYTHONNOUSERSITE=1
export PIP_REQUIRE_VIRTUALENV=1

export JUPYTERLAB_APP="${GEN_JP_LIBRARIES}/.venv/share/jupyter/lab"
export JUPYTERLAB_SETTINGS_DIR="${GENNAKER}/config"
export JUPYTERLAB_WORKSPACES_DIR="${GENNAKER}/config"
export JUPYTER_CONFIG_DIR="${GENNAKER}/config"
export JUPYTER_CONFIG_PATH="${GENNAKER}/config/path"
export JUPYTER_PATH="${GENNAKER}/config"
export JUPYTER_DATA_DIR="${GENNAKER}/config/data"
export JUPYTER_RUNTIME_DIR="${GENNAKER}/config/runtime"

export JUPYTER_TOKEN=${3}
PORT=${4}

START="${GEN_PROJECTS}/${1}/${2}/${2}.ipynb"
ARGS="--no-browser --expose-app-in-browser --JupyterApp.config_file_name='' --ServerApp.port=${PORT} --ServerApp.allow_origin='*'"

cd "${GEN_PROJECTS}/${1}/${2}" || exit

if [ -f "${START}" ]; then 
    "${GEN_JP_LIBRARIES}"/.venv/bin/python3 -m jupyterlab.labapp "$START" $ARGS
else
    "${GEN_JP_LIBRARIES}"/.venv/bin/python3 -m jupyterlab.labapp $ARGS
fi
