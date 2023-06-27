#!/bin/bash

cd "${GENNAKER_PATH}/jupyter-libraries" || exit
"${GPYTHON_FRAMEWORK_PATH}/Versions/3.10/bin/python3.10" -m venv  .venv 
source .venv/bin/activate
python3 -m pip install pip -U 
python3 -m pip install -r gennaker-requirements.txt
python3 -m pip uninstall -r gennaker-replacements.txt -y 
python3 -m pip install --no-index --find-links="${PIP_LINKS_PATH}"  -r gennaker-replacements.txt
mv ./signing.py ./.venv/lib/python3.10/site-packages/signing.py
mv ./styles.py ./.venv/lib/python3.10/site-packages/styles.py

declare -a projects=("Setup and Signatures/Shared Libraries" "Authoring/Scratchpad" "Readings/Symbolic Math")
for project in "${projects[@]}"
do
  mkdir -p "${GENNAKER_PATH}/projects/$project"
  cd "${GENNAKER_PATH}/projects/$project"
  mkdir -p .v
  cd .v
  "${GPYTHON_FRAMEWORK_PATH}/Versions/3.10/bin/python3.10" -m venv .venv 
  chown -R "${USER}":staff .venv
  source .venv/bin/activate
  python3 -m pip install pip -U 
done
