project (pythonwrapper CXX)
cmake_minimum_required (VERSION 3.0)

set(BOOST_INCLUDEDIR /usr/include)

find_package(PythonLibs 3.10 REQUIRED)
include_directories (${PYTHON_INCLUDE_DIRS})
link_directories(${PYTHON_LIBRARIES})

find_package(Boost COMPONENTS python310 REQUIRED)
include_directories (${Boost_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIR})

find_package(PkgConfig)
find_package(ARGoS REQUIRED)

set(ARGOS_PREFIX ${ARGOS_PREFIX} CACHE INTERNAL "")
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${ARGOS_PREFIX}/share/argos3/cmake)

link_directories(${ARGOS_LIBRARY_DIR})
link_libraries(${ARGOS_LDFLAGS})

# Set ARGoS include dir
include_directories(${CMAKE_SOURCE_DIR} ${ARGOS_INCLUDE_DIRS} ${GSL_INCLUDE_DIR} ${LUA_INCLUDE_DIR})

# Set ARGoS link dir
link_directories(${ARGOS_LIBRARY_DIRS})

include_directories(${CMAKE_SOURCE_DIR}/controllers)

set(PYCONTROLLER_HEADERS
  py_controller.h
  py_wrapper.h
  py_actusensor_wrapper_generic.h
  py_actusensor_wrapper_footbot.h
  py_actusensor_wrapper_epuck.h
)

set(PYCONTROLLER_SOURCES
  py_controller.cpp
  py_wrapper.cpp
  py_actusensor_wrapper_generic.cpp
  py_actusensor_wrapper_footbot.cpp
  py_actusensor_wrapper_epuck.cpp
)

set(PYLOOPFUNCTION_HEADERS
  py_loop_function.h 
)

set(PYLOOPFUNCTION_SOURCES
  py_loop_function.cpp
)

set(PYQTUSERFUNCTION_HEADERS
  py_qtuser_function.h 
  py_environment_wrapper.h
)

set(PYQTUSERFUNCTION_SOURCES
  py_qtuser_function.cpp
  py_environment_wrapper.cpp
)

# Libraries
add_library(py_controller_interface SHARED ${PYCONTROLLER_HEADERS} ${PYCONTROLLER_SOURCES})
add_library(py_loop_function_interface SHARED ${PYLOOPFUNCTION_HEADERS} ${PYLOOPFUNCTION_SOURCES})
add_library(py_qtuser_function_interface SHARED ${PYQTUSERFUNCTION_HEADERS} ${PYQTUSERFUNCTION_SOURCES})

# Link them to Python and Boost.Python
target_link_libraries(py_qtuser_function_interface
    ${PYTHON_LIBRARIES}
    ${Boost_LIBRARIES}
)

target_link_libraries(py_loop_function_interface
    ${PYTHON_LIBRARIES}
    ${Boost_LIBRARIES}
)

target_link_libraries(py_controller_interface
    py_loop_function_interface
    py_qtuser_function_interface
    argos3core_simulator
    argos3plugin_simulator_footbot
    argos3plugin_simulator_genericrobot
    ${PYTHON_LIBRARIES}
    ${Boost_LIBRARIES}
)

