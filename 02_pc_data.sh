#!/usr/bin/env bash

# Choose one of the three options
use_pdal=true
use_wrench=false
use_dl_then_wrench=false

# Compile and install PDAL wrench if needed
if $use_wrench || $use_dl_then_wrench; then
    wget https://github.com/PDAL/wrench/archive/refs/tags/v1.1.tar.gz
    tar -zxvf v1.1.tar.gz
    cd wrench-1.1
    mkdir build
    cd build
    cmake -DCMAKE_INSTALL_PREFIX=$CONDA_PREFIX -DCMAKE_PREFIX_PATH=$CONDA_PREFIX ..
    make -j $(nproc)
    make install
    cd ../..
fi

# Option 1 : Using PDAL pipelines in parallel to create tiles
if $use_pdal; then
    # Generate an index of COPC files in S3 as a GPKG file
    rm -rf copc_index.gpkg
    python3 scripts/generate_copc_index.py --output copc_index.gpkg

    # Generate PDAL pipelines files using this index
    rm -rf pdal_pipelines pdal_pc_tiles pdal_logs
    mkdir pdal_pipelines pdal_pc_tiles pdal_logs
    python3 scripts/generate_pdal_pipelines.py \
            --output_pipelines_dir pdal_pipelines \
            --output_tiles_dir pdal_pc_tiles \
            --output_log_dir pdal_logs \
            --tile_index copc_index.gpkg

    # Create pointcloud tiles in parallel using all cores
    time parallel --joblog pdal_logs/parallel.log -j $(nproc) < pdal_commands.txt
fi

# Option 2 : Use PDAL wrench to create tiles 
if $use_wrench; then
    # Create a full VPC of COPC files in S3
    rm -rf block_urls_dir vpc build_vpc_logs
    mkdir block_urls_dir vpc build_vpc_logs
    python3 scripts/generate_build_vpc_commands.py --output_urls_dir block_urls_dir --output_log_dir build_vpc_logs --output_dir vpc

    # creating VPC ... is a lengthy process (~1.5h)
    parallel --joblog build_vpc_logs/parallel.log -j $(($(nproc)*8)) < build_vpc_commands.txt
    python3 scripts/merge_vpc_files.py

    # Try running sequential pdal wrench DOES NOT WORK in terms of performance
    rm -rf wrench_bbox wrench_logs wrench_pc_tiles
    mkdir wrench_bbox wrench_logs wrench_pc_tiles
    python3 scripts/generate_pdal_wrench_commands.py
    parallel --joblog wrench_logs/parallel.log -j 1 < wrench_commands.txt
fi  

# Option 3 : Download directly the needed COPC files and use PDAL wrench commands to create tiles
# TODO: More tests to be done here
if $use_dl_then_wrench; then
    # Generate an index of COPC files in S3 as a GPKG file
    rm -rf copc_index.gpkg
    python3 scripts/generate_copc_index.py --output copc_index.gpkg
    
    # Create wget commands and download
    rm -rf raw_tiles
    mkdir raw_tiles
    python3 scripts/generate_wget_commands.py --output_dir raw_tiles
    parallel --joblog wget_joblog.log -j $(nproc) < wget_commands.txt

    # Create list of downloaded tiles
    ls raw_tiles/*.laz > file_list.txt
    # Create a VPC for the downloaded files
    pdal_wrench build_vpc --output=raw_tiles.vpc --input-file-list=file_list.txt
    
    # Create PDAL wrench commands and use them sequentially
    # TODO: Test with clip commands sequentially, and PDAL wrench merge and PDAL pipeline in parallel.
    rm -rf wrench_bbox wrench_logs wrench_pc_tilest
    mkdir wrench_bbox wrench_logs wrench_pc_tiles
    python3 scripts/generate_pdal_wrench_commands.py --input_vpc_file raw_tiles.vpc
    parallel --joblog wrench_logs/parallel.log -j 1 < wrench_commands.txt
fi

