import requests
from bs4 import BeautifulSoup
import fiona
from shapely import box
from shapely.geometry import mapping
import re
import argparse
import sys
from tqdm import tqdm

def parse_args():
    parser = argparse.ArgumentParser("Create a simple GPKG grid of all COPC files bounding boxes available in S3")
    parser.add_argument("--base_url","-b",
                        help="base S3 url",
                        default="https://storage.sbg.cloud.ovh.net/v1/AUTH_63234f509d6048bca3c9fd7928720ca1/ppk-lidar/")
    parser.add_argument("--output","-o",
                        help="output index file",
                        default="copc_index.gpkg")
    return parser.parse_args()

def main():
    args = parse_args()
    regexp = re.compile("LHD_FXX_(\d*)_(\d*)_.*\.copc\.laz")
    schema = {'geometry': 'Polygon', 'properties': {'url': 'str'}}

    response = requests.get(args.base_url)
    soup = BeautifulSoup(response.text,features="lxml")

    # LIDAR HD block identifiers should be 2 or 3 uppercase letters
    blocks = soup.find_all('a', string=re.compile('[A-Z]{2,3}/'))

    with fiona.open(args.output, 'w', driver='GPKG', schema=schema, crs="EPSG:2154") as dest:
        for block in tqdm(blocks):
            response = requests.get(args.base_url+block.get("href"))
            soup = BeautifulSoup(response.text, features="lxml")
            files = soup.find_all('a')
            for file in files:
                href = file.get("href")
                m = regexp.match(href)
                if m:
                    url = args.base_url + block.get("href") + href
                    groups = m.groups()
                    xmin = float(groups[0])*1000
                    ymax = float(groups[1])*1000
                    xmax = xmin + 1000
                    ymin = ymax - 1000
                    b = box(xmin,ymin,xmax,ymax)
                    dest.write({'geometry': mapping(b), 'properties': {'url':url}})
    return 0

if __name__ == '__main__':
    sys.exit(main())
