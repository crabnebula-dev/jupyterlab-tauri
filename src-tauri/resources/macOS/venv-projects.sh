#!/bin/bash

mkdir -p .v
cd .v
${GPYTHON_FRAMEWORK_PATH}/Versions/3.10/bin/python3.10 -m venv .venv 
sudo chown -R "${USER}":staff .venv
source .venv/bin/activate
python3 -m pip install pip -U 
