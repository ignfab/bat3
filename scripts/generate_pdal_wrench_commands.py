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
    parser = argparse.ArgumentParser("Create PDAL wrench commands to create point cloud tiles")
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
    parser.add_argument("--output_cmd_file", "-f",
                        help="output commands file",
                        default="wrench_commands.txt")
    return parser.parse_args()


def main():
    args = parse_args()
    schema = {'geometry': 'Polygon', 'properties': {'leaf_id': 'str'}}
    with open(args.output_cmd_file, "w") as cmd_dest:
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
            cmd = f"pdal_wrench clip --input={args.input_vpc_file} --polygon={bbox_output_filepath} --output={clip_output_filepath} > {log_file} 2>&1"

            las_files = os.path.join(args.output_tiles_dir, leaf_id, "*.las")
            merge_output_filepath = os.path.join(
                args.output_tiles_dir, leaf_id, "merged.las")
            cmd += f" && pdal_wrench merge --output={merge_output_filepath} {las_files} >> {log_file} 2>&1"

            tile_output_filepath = os.path.join(
                args.output_tiles_dir, "tile_"+leaf_id+".laz")
            cmd += f" && pdal pipeline {args.fix_pipeline} --readers.las.filename={merge_output_filepath} --writers.las.filename={tile_output_filepath} >> {log_file} 2>&1"

            temporary_dir = os.path.join(args.output_tiles_dir, leaf_id)
            cmd += f" && rm -rf {temporary_dir}"

            cmd_dest.write(cmd+"\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
