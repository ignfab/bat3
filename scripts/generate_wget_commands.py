import os,sys
import glob
import argparse
import geopandas as gpd

def parse_args():
    parser = argparse.ArgumentParser("Create wget commands to downoad all the necessary COPC files from OVH S3")
    parser.add_argument("--input_quadtree_structure","-i",
                        help="input",
                        default="actual_quadtree_structure.gpkg")
    parser.add_argument("--tile_index", "-t",
                        help="tile index gpkg",
                        default="copc_index.gpkg")
    parser.add_argument("--output_dir", "-r",
                        help="tile index gpkg",
                        default="raw_tiles")
    parser.add_argument("--output_file","-o",
                        help="output",
                        default="wget_commands.txt")
    return parser.parse_args()

def main():
    args = parse_args()
    # Load quadtree leaves
    quadtree_leaves = gpd.GeoDataFrame.from_file(args.input_quadtree_structure)
    # Scale the leaves so that a buffer is present
    quadtree_leaves['geometry'] = quadtree_leaves.geometry.scale(
        xfact=1.1, yfact=1.1)
    # Load the copc index
    copc_index = gpd.GeoDataFrame.from_file(args.tile_index)
    # Intersects leaf with copc tiles
    copc_in_leaf = gpd.sjoin(quadtree_leaves, copc_index)
    urls = copc_in_leaf["url"].unique()
    with open(args.output_file, "w") as dest:
        for url in urls:
            cmd = "wget " + url + " -P " + args.output_dir
            dest.write(cmd+"\n")
    return 0

if __name__ == '__main__':
    sys.exit(main())
