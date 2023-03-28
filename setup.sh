#!/bin/sh
rm -rf env
python3 -m venv env
brew install python-tk
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt