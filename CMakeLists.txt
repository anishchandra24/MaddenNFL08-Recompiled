# madden08 - ReXGlue Recompiled Project
#
# SDK boilerplate lives in generated/rexglue.cmake.

cmake_minimum_required(VERSION 3.25)
project(madden08 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(generated/rexglue.cmake)

# Sources
set(Madden08_SOURCES
    src/main.cpp
)

# Optional: embed the game's own icon into the exe. The icon is the game's
# artwork, so it is not part of this project. Run the game once, copy the
# madden08.ico it writes next to the exe into res/, then rebuild.
if(WIN32 AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/res/madden08.ico")
    enable_language(RC)
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/madden08_icon.rc"
         "1 ICON \"${CMAKE_CURRENT_SOURCE_DIR}/res/madden08.ico\"\n")
    list(APPEND Madden08_SOURCES "${CMAKE_CURRENT_BINARY_DIR}/madden08_icon.rc")
endif()

if(WIN32)
    add_executable(madden08 WIN32 ${Madden08_SOURCES})
else()
    add_executable(madden08 ${Madden08_SOURCES})
endif()

rexglue_setup_target(madden08)
