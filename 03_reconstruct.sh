#!/usr/bin/env bash

rm -rf geoflow_results
mkdir geoflow_results
python3 scripts/generate_geoflow_commands.py
time parallel --joblog parallel_geoflow.log -j $(nproc) < geoflow_commands.txt
