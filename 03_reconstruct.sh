#!/usr/bin/env bash

rm -rf geoflow_results geoflow_logs
mkdir geoflow_results geoflow_logs
python3 scripts/generate_geoflow_commands.py \
        --output_dir geoflow_results \
        --output_log_dir geoflow_logs
time parallel --joblog parallel_geoflow.log -j $(nproc) < geoflow_commands.txt
