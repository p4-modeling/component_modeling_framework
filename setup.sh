#! /bin/bash

# setup submodules
git submodule update --init

# create venv
virtualenv --python python3 venv3
source venv3/bin/activate

# install own requirements
pip install -r requirements.txt

# install requirements of deps
pip install -r deps/p4gen16/requirements.txt
