cmake_minimum_required(VERSION 3.16)
project(dorm_radar_native_tests LANGUAGES CXX)

add_executable(dorm_radar_native_tests
    test_main.cpp
    ../../lib/DormRadarProtocol/src/DormRadarProtocol.cpp
    ../../lib/Ld2450/src/Ld2450.cpp
)

target_include_directories(dorm_radar_native_tests PRIVATE
    ../../lib/DormRadarProtocol/src
    ../../lib/Ld2450/src
)

target_compile_features(dorm_radar_native_tests PRIVATE cxx_std_11)
target_compile_options(dorm_radar_native_tests PRIVATE -Wall -Wextra -Wpedantic)
