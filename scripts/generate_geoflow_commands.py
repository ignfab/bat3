import os
import sys
import glob
import argparse
import glob

def parse_args():
    parser = argparse.ArgumentParser("Create geoflow commands")
    parser.add_argument("--input_pc_dir", "-p",
                        help="input point cloud tiles directory",
                        default="pdal_pc_tiles")
    parser.add_argument("--input_vector_dir", "-v",
                        help="input vector tiles directory",
                        default="vector_tiles")
    parser.add_argument("--output_dir", "-o",
                        help="output dir for geoflow results",
                        default="geoflow_results")
    parser.add_argument("--output_log_dir", "-l",
                        help="output logs directory",
                        default="geoflow_logs")
    parser.add_argument("--output_cmd_file", "-c",
                        help="output commands file",
                        default="geoflow_commands.txt")
    return parser.parse_args()

def main():
    args = parse_args()
    cwd = os.getcwd()
    with open(args.output_cmd_file,'w') as dest:
        for filepath in glob.iglob(args.input_pc_dir+"/*"):
            filename = os.path.basename(filepath).split('.')[0]
            log_file_path = os.path.join(args.output_log_dir, filename+".log")
            pc_tiles_dir = os.path.join(cwd, args.input_pc_dir)
            vector_tiles_dir = os.path.join(cwd, args.input_vector_dir)
            results_dir = os.path.join(cwd, args.output_dir)
            cmd = (
            f'docker run --rm'
            f' -v "{pc_tiles_dir}:/lidar_data"'
            f' -v "{vector_tiles_dir}:/bdtopo_data"'
            f' -v "{results_dir}:/results"'
            f' ignfab/lod22-reconstruct-batch:latest'
            f' -V'
            f' --input_footprint=/bdtopo_data/{filename}.gpkg'
            f' --input_pointcloud=/lidar_data/{filename}.laz'
            f' --output_cityjson=/results/{filename}.json'
            f' --output_cj_referenceSystem="https://www.opengis.net/def/crs/EPSG/0/2154"'
            f' --building_identifier=OGRLoader.cleabs > {log_file_path} 2>&1' 
            )
            dest.write(cmd+"\n")
    return 0

if __name__ == '__main__':
    sys.exit(main())
