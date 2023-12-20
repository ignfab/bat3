# ![Graphicloads-Battery-Battery-bar-5-full 32](https://github.com/ignfab/bat3/assets/5435148/e52b75a7-9f7d-4628-8ca4-e2f237c36910) BAT3

This project is a first try at generating 3D semantized building with [geoflow-bundle](https://github.com/geoflow3d/geoflow-bundle) at scale using [IGNF](https://www.ign.fr/) datasets and services.  
The working area is an [IGNF LIDAR HD](https://geoservices.ign.fr/lidarhd) block (50kmx50km).

## Workflow

The workflow is inspired by [geoflow-bundle](https://github.com/geoflow3d/geoflow-bundle) approach for generating at scale, also implemented in [Optim3D](https://github.com/Yarroudh/Optim3D).  
The main idea is to build a quadtree based on building footprints, tile the point cloud data accordingly and generate 3D buildings using the generated vector and point cloud tiles.  
To speedup the quadtree calculation, the process was implemented here in C++ using GDAL and CGAL.

## Datasets

### Building footprints

The building footprints used are those from [IGNF BDTOPO](https://geoservices.ign.fr/bdtopo) reference vector database.  
A pre-processing task will be added at some point to make sure the footprints perfectly overlay the point cloud data.

### Point cloud

The point cloud date are the newly acquired [IGNF LIDAR HD](https://geoservices.ign.fr/lidarhd) datasets.  
The data are tiled and preprocessed to merge the two building classes (class 6 and class 67).

## Downloading datasets

### BDTOPO building footprints

Two options are possible:
* Using IGNF [Geoplateforme WFS 2.0.0](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities) limited to 10⁶ features per query (but offering paging)
* Downloading dataset archives per [french department](https://geoservices.ign.fr/bdtopo#telechargementgpkgdep) or [french region](https://geoservices.ign.fr/bdtopo#telechargementshpreg) as GPKG files compressed with 7z

In `01_vector_data.sh` the two options are available. WFS is used by default for this example.

### LIDAR HD point cloud

Classified LIDAR HD datasets are available in COPC format in an [OVH S3 bucket](https://storage.sbg.cloud.ovh.net/v1/AUTH_63234f509d6048bca3c9fd7928720ca1/ppk-lidar/).

Two command line tools can be used to query these COPC files and extract the tiles :
* [PDAL](https://github.com/PDAL/PDAL) by defining a pipeline for each tile
* [PDAL wrench](https://github.com/PDAL/wrench) an upgraded version of PDAL supporting multi-threading and the use of VPC files.

The two approaches are available in `02_pc_data.sh`. `PDAL` is used by default in this example as it seems to be the fastest solution in the first tests.

#### Extracting tiles with PDAL

* As explained [here](https://gist.github.com/esgn/4bbf298ad76f4d72e9f3c133cbc96cf1) knowing the COPC files to extract from, it is possible to write a pipeline for each tile
* This solution offers the possibility to define all pre-processing tasks in a single pipeline JSON file
* These pipelines can be launched in parallel using `GNU parallel`

#### Extracting tiles with PDAL wrench

* PDAL wrench uses a VPC file that indexes all COPC files. This global COPC is not provided by IGNF as of now. A script is provided in this example to create this full VPC
* PDAL wrench `clip` operation is multi-threaded but not the `merge` operation. As a result, the optimal way to use this tool would be to launch some operations sequentially and others in parallel. 

## 3D building reconstruction

3D building reconstruction is done with [geoflow-bundle](https://github.com/geoflow3d/geoflow-bundle).  
IGNfab provides additional [images Docker](https://hub.docker.com/u/ignfab) to test the different workflows available in geoflow (single, batch, stream). These are the images used in this example.  
Building reconstruction tasks are launched in parallel using `GNU parallel` 

## How to use this project

This project has been tested with Ubuntu 22.04 running on a CCX53 Hetzner instance with 32 cores.  
It requires [Docker](https://docs.docker.com/engine/install/ubuntu/) to run geoflow and [Anaconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) to get the most out of PDAL.  
It requires 700GB of free space to create the necessary point cloud tiles.

First create the conda environment `bat3` using `conda env create -f environment.yml` then activate it with `conda activate bat3`

Then three main steps of the workflow can be launched using bash script

* `01_vector_data.sh` to download vector data, create quadtree and vector tiles (1 to 2 minutes)
* `02_pc_data.sh` to create point cloud tiles based on COPC files in OVH S3 (~2.5 hours)
* `03_reconstruct.sh` to reconstruct 3D buildings with geoflow (~1.5 hours)

The CityJSON results from geoflow can be merged and filtered using [cjio](https://github.com/cityjson/cjio) if necessary.
