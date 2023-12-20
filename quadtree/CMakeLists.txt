project(quadtree)

cmake_minimum_required(VERSION 3.1)

# GDAL
find_package(GDAL CONFIG REQUIRED)
find_package(CGAL REQUIRED)

add_executable(quadtree quadtree.cpp)

# Link to CGAL and third-party libraries
target_link_libraries(quadtree PRIVATE GDAL::GDAL CGAL::CGAL)