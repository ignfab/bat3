import requests
from bs4 import BeautifulSoup
import re
import argparse
import sys
import os
from tqdm import tqdm
import glob


def parse_args():
    parser = argparse.ArgumentParser("Create files and commands in order to build a complete VPC of COPC LIDAR HD files")
    parser.add_argument("--base_url", "-b",
                        help="base S3 url",
                        default="https://storage.sbg.cloud.ovh.net/v1/AUTH_63234f509d6048bca3c9fd7928720ca1/ppk-lidar/")
    parser.add_argument("--output_urls_dir", "-u",
                        help="output index file",
                        default="block_urls_dir")
    parser.add_argument("--output_log_dir", "-l",
                        help="output index file",
                        default="build_vpc_logs")
    parser.add_argument("--output_dir", "-o",
                        help="output vpc directory",
                        default="vpc")
    parser.add_argument("--output_cmd_file", "-f",
                        help="output commands file",
                        default="build_vpc_commands.txt")
    return parser.parse_args()


def main():
    args = parse_args()
    regexp = re.compile("LHD_FXX_(\d*)_(\d*)_.*\.copc\.laz")

    response = requests.get(args.base_url)
    soup = BeautifulSoup(response.text, features="lxml")
    blocks = soup.find_all('a')

    for block in tqdm(blocks):
        response = requests.get(args.base_url+block.get("href"))
        soup = BeautifulSoup(response.text, features="lxml")
        files = soup.find_all('a')
        output_filename = str(block.contents[0]).replace("/", "")+".txt"
        output_filepath = os.path.join(args.output_urls_dir, output_filename)
        with open(output_filepath, "w") as dest:
            for file in files:
                href = file.get("href")
                m = regexp.match(href)
                if m:
                    url = args.base_url + block.get("href") + href
                    dest.write(url+"\n")

    with open(args.output_cmd_file, "w") as dest:
        for urls_filepath in glob.iglob(args.output_urls_dir+"/*.txt"):
            filename = os.path.basename(urls_filepath).split('.')[0]
            output_vpc_filepath = os.path.join(args.output_dir,filename+".vpc")
            output_log_filepath = os.path.join(args.output_log_dir,filename+".log")
            row = f"pdal_wrench build_vpc --output={output_vpc_filepath} --input-file-list={urls_filepath} > {output_log_filepath} 2>&1"
            dest.write(row+"\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
