#!/bin/bash

${GPYTHON_FRAMEWORK_PATH}/Versions/3.10/bin/python3.10 -m venv  .venv 
source .venv/bin/activate
python3 -m pip install pip -U 
python3 -m pip install -r gennaker-requirements.txt
python3 -m pip uninstall -r gennaker-replacements.txt -y 
python3 -m pip install --no-index --find-links="${PIP_LINKS_PATH}"  -r gennaker-replacements.txt
mv ./signing.py ./.venv/lib/python3.10/site-packages/signing.py
mv ./styles.py ./.venv/lib/python3.10/site-packages/styles.py
