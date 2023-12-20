#include "ogrsf_frmts.h"
#include <string>
#include <iostream>
#include <stdio.h>
#include <CGAL/Simple_cartesian.h>
#include <CGAL/Quadtree.h>
#include <CGAL/Random.h>
#include <CGAL/Octree.h>

// Raw C++ code for producing quadtree based on building footprints

// Type Declarations
typedef CGAL::Simple_cartesian<double> Kernel;
typedef Kernel::Point_2 Point_2;
typedef std::vector<Point_2> Point_vector;
typedef CGAL::Quadtree<Kernel, Point_vector> Quadtree;

std::string create_leaf_id(Quadtree::Node leaf)
{
    Quadtree::Node::Global_coordinates c = leaf.global_coordinates();
    std::uint8_t d = leaf.depth();
    std::string leaf_id = std::to_string(c[0]) + "_" + std::to_string(c[1]) + "_" + std::to_string(d);
    return leaf_id;
}

int main(int argc, char *argv[])
{

    // input file name
    const std::string input_file = (argc > 1) ? argv[1] : "bati_bdtopo.gpkg";
    // output directory
    const std::string output_dir = (argc > 2) ? argv[2] : "vector_tiles";
    // deepest a tree is allowed to be (nodes at this depth will not be split)
    const int max_depth = (argc > 3) ? std::stoi(argv[3]) : 10;
    // maximum points a node is allowed to contain
    const int bucket_size = (argc > 4) ? std::stoi(argv[4]) : 3500;
    // enlarge ratio for the quadtree global bbox
    const double enlarge_ratio = (argc > 5) ? std::stof(argv[5]) : 1.01;

    const char *outputDriverName = "GPKG";
    GDALDriver *outputDriver;
    GDALAllRegister();

    // Load building footprint file
    GDALDataset *inputDS;
    inputDS = (GDALDataset *)GDALOpenEx(input_file.c_str(), GDAL_OF_VECTOR, NULL, NULL, NULL);
    if (inputDS == NULL)
    {
        printf("Open failed.\n");
        exit(1);
    }
    else
    {
        printf("Open success.\n");
    }

    // Load building footprint layer (the first and only one)
    OGRLayer *inputLayer;
    inputLayer = inputDS->GetLayer(0);

    // Load GPKG driver
    outputDriver = GetGDALDriverManager()->GetDriverByName(outputDriverName);
    if (outputDriver == NULL)
    {
        printf("%s driver not available.\n", outputDriverName);
        exit(1);
    }

    // Create unordered map of [cleabs,  buidling footprint centroid]
    Point_vector points_2d;
    std::unordered_map<std::string, Point_2> mapping;

    // Fill map of centroids
    for (auto &inputFeature : inputLayer)
    {
        std::string unique_id = std::to_string(inputFeature->GetFID());
        OGRGeometry *poGeometry;
        poGeometry = inputFeature->GetGeometryRef();
        OGRPoint *poPoint = new OGRPoint();
        poGeometry->Centroid(poPoint);
        points_2d.emplace_back(poPoint->getX(), poPoint->getY());
        mapping.emplace(std::piecewise_construct, std::forward_as_tuple(unique_id), std::forward_as_tuple(poPoint->getX(), poPoint->getY()));
    }

    // Compute quadtree
    Quadtree quadtree(points_2d, CGAL::Identity_property_map<Point_2>(), enlarge_ratio);
    quadtree.refine(max_depth, bucket_size);

    // keep track of quadtree leaf bbox
    std::unordered_map<std::string, OGRPolygon> leaf_bbox;

    for (Quadtree::Node leaf : quadtree.traverse<CGAL::Orthtrees::Leaves_traversal>())
    {
        OGRPolygon polygon;
        std::ostringstream oss;
        auto bbox = quadtree.bbox(leaf);
        oss << std::fixed << "POLYGON((";
        oss << bbox.xmin() << " " << bbox.ymin() << ",";
        oss << bbox.xmin() << " " << bbox.ymax() << ",";
        oss << bbox.xmax() << " " << bbox.ymax() << ",";
        oss << bbox.xmax() << " " << bbox.ymin() << ",";
        oss << bbox.xmin() << " " << bbox.ymin() << "))";
        const std::string wkt = oss.str();
        const char *c_wkt = wkt.c_str();
        polygon.importFromWkt(&c_wkt);
        std::string leaf_id = create_leaf_id(leaf);
        leaf_bbox[leaf_id] = polygon;
        // std::cout << polygon.exportToWkt() << std::endl;
    }

    // establish [leaf, cleabs] mapping
    std::unordered_map<std::string, std::vector<std::string>> leaf_mapping;

    for (auto i : mapping)
    {
        std::string unique_id = i.first;
        Quadtree::Node leaf = quadtree.locate(i.second);
        std::string leaf_id = create_leaf_id(leaf);
        if (!leaf_mapping.count(leaf_id))
        {
            std::vector<std::string> unique_ids;
            unique_ids.push_back(unique_id);
            leaf_mapping.insert(std::pair<std::string, std::vector<std::string>>(leaf_id, unique_ids));
        }
        else
        {
            leaf_mapping[leaf_id].push_back(unique_id);
        }
    }

    // Keep track of actual leaf bounding boxes
    std::unordered_map<std::string, OGRPolygon> actual_leaf_bbox;


    // create file for each leaf
    for (auto m : leaf_mapping)
    {
        GDALDataset *outputDS;
        OGRLayer *outputLayer;

        std::string leaf_id = m.first;
        std::vector<std::string> unique_ids = m.second;

        std::string outputFileName = leaf_id;
        outputFileName.append(".gpkg");

        outputFileName.insert(0, output_dir+"/tile_");

        std::string outputLayerName = leaf_id;
        outputLayerName.insert(0, "tile_");

        // get SRS definition from original layer
        OGRSpatialReference *spatialReference;
        spatialReference = inputLayer->GetSpatialRef();

        // create file
        outputDS = outputDriver->Create(outputFileName.c_str(), 0, 0, 0, GDT_Unknown, NULL);
        if (outputDS == NULL)
        {
            printf("Creation of output file failed.\n");
            exit(1);
        }

        // create layer
        outputLayer = outputDS->CreateLayer(outputLayerName.c_str(), spatialReference, wkbMultiPolygon, NULL);
        if (outputLayer == NULL)
        {
            printf("Layer creation failed.\n");
            exit(1);
        }

        // create fields the quick and dirty way (is there another way to do so ?)
        OGRFeatureDefn *poFDefn = inputLayer->GetLayerDefn();
        for (int iField = 0; iField < poFDefn->GetFieldCount(); iField++)
        {

            OGRFieldDefn *poFieldDefn = poFDefn->GetFieldDefn(iField);
            outputLayer->CreateField(poFieldDefn);
        }

        // write features to file
        for (auto unique_id : unique_ids)
        {
            OGRFeature *outputFeature;
            GIntBig id = stoll(unique_id, nullptr, 10);
            outputFeature = inputLayer->GetFeature(id);
            outputFeature = outputFeature->Clone();
            if (outputLayer->CreateFeature(outputFeature) != OGRERR_NONE)
            {
                printf("Failed to create building in tile output file.\n");
                exit(1);
            }
        }

        // get actual layer bbox
        OGREnvelope psExtent;
        if (outputLayer->GetExtent(&psExtent, TRUE)!= OGRERR_NONE)
            {
                printf("Failed to get Layer extent.\n");
                exit(1);
            }
        std::ostringstream wkt;
        wkt << std::fixed << "POLYGON((";
        wkt << psExtent.MinX << " " << psExtent.MinY << ",";
        wkt << psExtent.MinX << " " << psExtent.MaxY << ",";
        wkt << psExtent.MaxX << " " << psExtent.MaxY << ",";
        wkt << psExtent.MaxX << " " << psExtent.MinY << ",";
        wkt << psExtent.MinX << " " << psExtent.MinY << "))";
        const std::string wktstr = wkt.str();
        const char *c_wkt = wktstr.c_str();
        OGRPolygon polygon;
        polygon.importFromWkt(&c_wkt);
        actual_leaf_bbox[leaf_id] = polygon;

        std::cout << "tile_" << leaf_id << " done" << std::endl;

        GDALClose(outputDS);
    }


    // Output the computed quadtree structure

    GDALDataset *qtreeDS;
    OGRLayer *qtreeLayer;

    // get SRS definition from original layer
    OGRSpatialReference *spatialReference;
    spatialReference = inputLayer->GetSpatialRef();

    // create file
    qtreeDS = outputDriver->Create("quadtree_structure.gpkg", 0, 0, 0, GDT_Unknown, NULL);
    if (qtreeDS == NULL)
    {
        printf("Creation of output file failed.\n");
        exit(1);
    }

    // create layer
    qtreeLayer = qtreeDS->CreateLayer("quadtree", spatialReference, wkbPolygon, NULL);
    if (qtreeLayer == NULL)
    {
        printf("Layer creation failed.\n");
        exit(1);
    }

    // create field
    OGRFieldDefn oField("leaf_id", OFTString);
    oField.SetWidth(32);
    if (qtreeLayer->CreateField(&oField) != OGRERR_NONE)
    {
        printf("Creating leaf_id field failed.\n");
        exit(1);
    }

    for (auto l : leaf_bbox)
    {
        std::string leaf_id = l.first;
        OGRPolygon polygon = l.second;

        // create feature with id
        OGRFeature *poFeature;
        poFeature = OGRFeature::CreateFeature(qtreeLayer->GetLayerDefn());
        poFeature->SetField("leaf_id", leaf_id.c_str());
        poFeature->SetGeometry(&polygon);
        if (qtreeLayer->CreateFeature(poFeature) != OGRERR_NONE)
        {
            printf("Failed to create bbox polygon.\n");
            exit(1);
        }

    }

    GDALClose(qtreeDS);

   // Output the computed actual quadtree structure

    GDALDataset *aqtreeDS;
    OGRLayer *aqtreeLayer;

    // create file
    aqtreeDS = outputDriver->Create("actual_quadtree_structure.gpkg", 0, 0, 0, GDT_Unknown, NULL);
    if (aqtreeDS == NULL)
    {
        printf("Creation of output file failed.\n");
        exit(1);
    }

    // create layer
    aqtreeLayer = aqtreeDS->CreateLayer("actual_quadtree", spatialReference, wkbPolygon, NULL);
    if (aqtreeLayer == NULL)
    {
        printf("Layer creation failed.\n");
        exit(1);
    }

    // create field
    if (aqtreeLayer->CreateField(&oField) != OGRERR_NONE)
    {
        printf("Creating leaf_id field failed.\n");
        exit(1);
    }

    for (auto l : actual_leaf_bbox)
    {
        std::string leaf_id = l.first;
        OGRPolygon polygon = l.second;

        // create feature with id
        OGRFeature *poFeature;
        poFeature = OGRFeature::CreateFeature(aqtreeLayer->GetLayerDefn());
        poFeature->SetField("leaf_id", leaf_id.c_str());
        poFeature->SetGeometry(&polygon);
        if (aqtreeLayer->CreateFeature(poFeature) != OGRERR_NONE)
        {
            printf("Failed to create bbox polygon.\n");
            exit(1);
        }

    }

    GDALClose(aqtreeDS);

    // Close inputDS
    GDALClose(inputDS);

    return EXIT_SUCCESS;
}