import os
import sys
import glob
import argparse
import geopandas as gpd
from shapely import affinity
from shapely import wkt
import json
from tqdm import tqdm
import glob


def parse_args():
    parser = argparse.ArgumentParser("Create JSON PDAL pipelines to create point cloud tiles")
    parser.add_argument("--input_file", "-i",
                        help="input quadtree structure",
                        default="actual_quadtree_structure.gpkg")
    parser.add_argument("--tile_index", "-t",
                        help="tile index gpkg",
                        default="copc_index.gpkg")
    parser.add_argument("--output_pipelines_dir", "-p",
                        help="output pipeline files directory",
                        default="pdal_pipelines")
    parser.add_argument("--output_tiles_dir", "-o",
                        help="output tiles directory",
                        default="pdal_pc_tiles")
    parser.add_argument("--output_log_dir", "-l",
                    help="output logs directory",
                    default="pdal_logs")
    parser.add_argument("--output_cmd_file", "-f",
                        help="output commands file",
                        default="pdal_commands.txt")
    return parser.parse_args()


def create_pipeline(leaf_id, polygon, urls, args):
    content = []
    b = polygon.bounds
    bounds = ([b[0], b[1]], [b[2], b[3]])

    for url in urls:
        tile = {}
        tile["type"] = "readers.copc"
        tile["filename"] = url
        tile["bounds"] = str(bounds)
        content.append(tile)

    filter = {}
    filter["type"] = "filters.assign"
    filter["value"] = "Classification=6 WHERE Classification==67"
    content.append(filter)

    writer = {}
    writer["type"] = "writers.las"
    writer["forward"] = "all"
    writer["extra_dims"] = "all"
    writer["a_srs"] = "EPSG:2154"
    writer["filename"] = os.path.join(args.output_tiles_dir, "tile_"+leaf_id+".laz")
    content.append(writer)

    pipeline = json.dumps(content, indent=2)
    return pipeline


def main():
    args = parse_args()
    # Load quadtree leaves
    quadtree_leaves = gpd.GeoDataFrame.from_file(args.input_file)
    print(args.input_file + " loaded")
    # Scale the leaves so that a buffer is present
    quadtree_leaves['geometry'] = quadtree_leaves.geometry.scale(
        xfact=1.1, yfact=1.1)
    # Load the copc index
    copc_index = gpd.GeoDataFrame.from_file(args.tile_index)
    print(args.tile_index + " loaded")
    # Intersects leaf with copc tiles
    copc_in_leaf = gpd.sjoin(quadtree_leaves, copc_index)
    print("intesection done")
    # Aggregate url per leaf
    intersecting = copc_in_leaf.groupby(
        "leaf_id")["url"].apply(lambda x: ','.join(x))
    intersecting = intersecting.rename("urls")
    # Merge with existing geodataframe
    leaves_with_url = quadtree_leaves.merge(intersecting, on='leaf_id')
    print("merge done")

    for index, leaf in tqdm(leaves_with_url.iterrows(), total=leaves_with_url.shape[0]):
        polygon = leaf["geometry"]
        urls = leaf["urls"]
        urls = urls.split(',')
        leaf_id = leaf["leaf_id"]
        pipeline = create_pipeline(leaf_id, polygon, urls, args)
        output_filename = "tile_"+leaf_id+".json"
        output_filepath = os.path.join(args.output_pipelines_dir, output_filename)
        with open(output_filepath, "w") as outfile:
            outfile.write(pipeline)

    with open(args.output_cmd_file, "w") as dest:
        for filepath in glob.iglob(args.output_pipelines_dir+"/*.json"):
            filename = os.path.basename(filepath).split('.')[0]
            log_filepath = os.path.join(args.output_log_dir, filename+".log")
            row = f"pdal pipeline {filepath} > {log_filepath} 2>&1"
            dest.write(row+"\n")
            
    return 0

if __name__ == '__main__':
    sys.exit(main())
