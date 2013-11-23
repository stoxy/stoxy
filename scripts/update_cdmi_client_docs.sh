#!/bin/bash

cd src/libcdmi-python
python ./cdmiclient.py --help | sed "s/^\(.*\)$/    \1/" > ../../docs/source/cli_usage_help.rst
