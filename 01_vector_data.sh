#!/usr/bin/env bash

# Working area in EPSG:2154
xmin=486000
ymin=6432000
xmax=537000
ymax=6483000

# Options for downloading data
use_wfs=true
use_dl=false

# Option 1 : Use WFS
if $use_wfs; then
    # Download vector data
    rm -rf bati_bdtopo.gml bati_bdtopo.gpkg
    # Limited to 10⁶ results
    wget -O bati_bdtopo.gml "https://data.geopf.fr/wfs?SERVICE=WFS&SRSNAME=EPSG:2154&BBOX=$xmin,$ymin,$xmax,$ymax,EPSG:2154&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=BDTOPO_V3:batiment"
    # Change format from GML to GPKG
    ogr2ogr -lco GEOMETRY_NAME=geom -f "GPKG" -nlt MULTIPOLYGON bati_bdtopo.gpkg bati_bdtopo.gml 
fi

# Option 2 : Use DL
if $use_dl; then
    rm -f bdtopo.7z bdtopo.gpkg bati_bdtopo.gpkg
    BDTOPO_URL="https://data.geopf.fr/telechargement/download/BDTOPO/BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D024_2023-12-15/BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D024_2023-12-15.7z"
    wget -O bdtopo.7z $BDTOPO_URL 
    7z -r e  bdtopo.7z */*/*.gpkg -so > bdtopo.gpkg
    ogr2ogr -spat $xmin $ymin $xmax $ymax -lco GEOMETRY_NAME=geom bati_bdtopo.gpkg bdtopo.gpkg batiment
    rm -f bdtopo.7z bdtopo.gpkg
fi

# Build CGAL quadtree executable
cd quadtree
rm -rf build
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$CONDA_PREFIX ..
make 
cd ../../

# Create vector tiles and quadtree structure files
rm -rf vector_tiles quadtree_structure.gpkg actual_quadtree_structure.gpkg
mkdir vector_tiles
./quadtree/build/quadtree bati_bdtopo.gpkg vector_tiles 10 3500 1.01
