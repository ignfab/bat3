import os,sys
import glob
import argparse
import json
from tqdm import tqdm

def parse_args():
    parser = argparse.ArgumentParser("Merge block VPC files")
    parser.add_argument("--input_dir","-i",
                        help="input",
                        default="vpc")
    parser.add_argument("--output","-o",
                        help="output",
                        default="full.vpc")
    return parser.parse_args()

def main():
    args = parse_args()
    full = []
    for file in tqdm(list(glob.iglob(args.input_dir+"/*.vpc"))):
        f = open(file)
        data = json.load(f)
        full += data["features"]
        f.close()
    print(str(len(full))+" tiles indexed")
    output = {}
    output["type"] = "FeatureCollection"
    output["features"] = full
    json_data = json.dumps(output, indent=4)
    with open(args.output, "w") as outfile:
        outfile.write(json_data)
    print(args.output + " written to disk")

if __name__ == '__main__':
    sys.exit(main())
