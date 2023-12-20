import os
import sys
import glob
import argparse
import geopandas as gpd
from shapely import affinity
from shapely import wkt
from shapely.geometry import shape, mapping, box
import fiona
import json
from tqdm import tqdm
import glob


def parse_args():
    parser = argparse.ArgumentParser("Create PDAL wrench commands in separate files to create point cloud tiles")
    parser.add_argument("--input_file", "-i",
                        help="input quadtree structure",
                        default="actual_quadtree_structure.gpkg")
    parser.add_argument("--input_vpc_file", "-v",
                        help="input vpc file",
                        default="full.vpc")
    parser.add_argument("--fix_pipeline", "-c",
                        help="pdal pipeline for fixing tiles",
                        default="fix_tile.json")
    parser.add_argument("--output_bbox_dir", "-p",
                        help="output pipeline files directory",
                        default="wrench_bbox")
    parser.add_argument("--output_tiles_dir", "-t",
                        help="output tile directory",
                        default="wrench_pc_tiles")
    parser.add_argument("--output_log_dir", "-l",
                        help="output logs directory",
                        default="wrench_logs")
    parser.add_argument("--output_clip_cmd_file", "-f",
                        help="output clip commands file",
                        default="wrench_clip_commands.txt")
    parser.add_argument("--output_merge_cmd_file", "-g",
                        help="output merge commands file",
                        default="wrench_merge_commands.txt")
    parser.add_argument("--output_pipeline_cmd_file", "-n",
                        help="output pipeline commands file",
                        default="wrench_pipeline_commands.txt")
    return parser.parse_args()


def main():
    args = parse_args()
    schema = {'geometry': 'Polygon', 'properties': {'leaf_id': 'str'}}
    with open(args.output_clip_cmd_file, "w") as clip_cmd_dest, open(args.output_merge_cmd_file, "w") as merge_cmd_dest, open(args.output_pipeline_cmd_file, "w") as pipeline_cmd_dest:
        for feat in fiona.open(args.input_file):

            leaf_id = feat["properties"]['leaf_id']
            bbox = shape(feat["geometry"])
            bbox = affinity.scale(bbox, xfact=1.1, yfact=1.1)
            bbox_output_filepath = os.path.join(
                args.output_bbox_dir, "tile_"+leaf_id+".gpkg")

            with fiona.open(bbox_output_filepath, 'w', driver='GPKG', schema=schema, crs="EPSG:2154") as dest:
                dest.write({'geometry': mapping(bbox),
                           'properties': {'leaf_id': leaf_id}})

            clip_output_filepath = os.path.join(
                args.output_tiles_dir, leaf_id+".vpc")
            log_file = os.path.join(args.output_log_dir, leaf_id+".log")
            clip_cmd = f"pdal_wrench clip --input={args.input_vpc_file} --polygon={bbox_output_filepath} --output={clip_output_filepath} > {log_file} 2>&1"
            clip_cmd_dest.write(clip_cmd+"\n")

            las_files = os.path.join(args.output_tiles_dir, leaf_id, "*.las")
            merge_output_filepath = os.path.join(
                args.output_tiles_dir, leaf_id, "merged.las")
            merge_cmd = f"pdal_wrench merge --output={merge_output_filepath} {las_files} >> {log_file} 2>&1"
            merge_cmd_dest.write(merge_cmd+"\n")

            tile_output_filepath = os.path.join(
                args.output_tiles_dir, "tile_"+leaf_id+".laz")
            pipeline_cmd = f"pdal pipeline {args.fix_pipeline} --readers.las.filename={merge_output_filepath} --writers.las.filename={tile_output_filepath} >> {log_file} 2>&1"
            temporary_dir = os.path.join(args.output_tiles_dir, leaf_id)
            pipeline_cmd += f" && rm -rf {temporary_dir}"
            pipeline_cmd_dest.write(pipeline_cmd+"\n")
            
    return 0


if __name__ == '__main__':
    sys.exit(main())
