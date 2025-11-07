#include "py_loop_function.h"
#include <random>
#include <iostream>
#include <exception>


using namespace argos;
using namespace boost::python;




#define INIT_MODULE_LOOP_FUNCTION PyInit_libpy_loop_function_interface
extern "C" PyObject* INIT_MODULE_LOOP_FUNCTION();

// TODO: I had to add these lines and the line PyImport_AppendInittab("libpy_controller_interface", INIT_MODULE_CONTROLLER)
// in this file, otherwise I god an error that libpy_controller_interface is not a built-in module
#define INIT_MODULE_CONTROLLER PyInit_libpy_controller_interface
extern "C" PyObject* INIT_MODULE_CONTROLLER();

// TODO: I had to add these lines and the line PyImport_AppendInittab("libpy_qtuser_function_interface", INIT_MODULE_QTUSER_FUNCTION)
// in this file, otherwise I god an error that libpy_qtuser_function_interface is not a built-in module
#define INIT_MODULE_QTUSER_FUNCTION PyInit_libpy_qtuser_function_interface
extern "C" PyObject* INIT_MODULE_QTUSER_FUNCTION();

//boost::python::list allRobots;
int m_nextRobotID = 0;  // Initialize it to 0 or any other suitable value




CPyLoopFunction::CPyLoopFunction() {
  // init python

  // TODO: Remove from loop function and only call in controller
  // PyImport_AppendInittab("libpy_qtuser_function_interface", INIT_MODULE_QTUSER_FUNCTION); 
  PyImport_AppendInittab("libpy_controller_interface", INIT_MODULE_CONTROLLER); 
  // TODO: Remove from loop function and only call in controller

  PyImport_AppendInittab("libpy_loop_function_interface", INIT_MODULE_LOOP_FUNCTION);
  if (!Py_IsInitialized()) {
    Py_Initialize();
  }
  m_loop_interpreter = Py_NewInterpreter();
    // init main module and namespace
  m_loop_main = import("__main__");
  m_loop_namesp = m_loop_main.attr("__dict__");

    // Initialize the allrobots list in the Python namespace
    try {
        m_loop_namesp["allrobots"] = boost::python::list();
        std::cout << "Initialized allrobots in C++" << std::endl;
    } catch (const boost::python::error_already_set&) {
        PyErr_Print();
        std::cerr << "Error: Failed to initialize allrobots in C++" << std::endl;
    }

}

void CPyLoopFunction::Init(TConfigurationNode& t_node) {
   float pos_tick=0.0;
  TConfigurationNode& tParams = GetNode(t_node, "params");
  
  /* Load script */
  std::string strScriptFileName;
  GetNodeAttributeOrDefault(tParams, "script", strScriptFileName, strScriptFileName);
  if (strScriptFileName == "") {
    THROW_ARGOSEXCEPTION("Loop function: Error loading python script \"" << strScriptFileName << "\""
      << std::endl);
  }
  // exec user script
  try {
    m_loop_script = exec_file(strScriptFileName.c_str(), m_loop_namesp, m_loop_namesp);

    std::cout << "Loop function: strScript:" << strScriptFileName << std::endl;
  } catch (error_already_set) {
    PyErr_Print();
  }
  // Initialize the allrobots list in the Python namespace
    try {
        m_loop_namesp["allrobots"] = boost::python::list();
        std::cout << "Initialized allrobots in C++" << std::endl;
    } catch (const boost::python::error_already_set&) {
        PyErr_Print();
        std::cerr << "Error: Failed to initialize allrobots in C++" << std::endl;
    }

  
  // Iterate over all robots and add them to a boost list
  boost::python::list allRobots;    
  CSpace::TMapPerType& m_cEpuck = GetSpace().GetEntitiesByType("epuck");
  for(CSpace::TMapPerType::iterator it = m_cEpuck.begin(); it != m_cEpuck.end(); ++it)
  {
    /* Get handle to e-puck entity and controller */
    CEPuckEntity& cEpuck = *any_cast<CEPuckEntity*>(it->second);

    CPyController& cController =  dynamic_cast<CPyController&>(cEpuck.GetControllableEntity().GetController());

    allRobots.append(cController.getActusensors());
    m_nextRobotID++;
  }
  m_loop_namesp["allrobots"]  = allRobots;
  std::cout << "No of rob: " << m_nextRobotID;
      //CRandom::CRNG* pcRNG = CRandom::CreateRNG("argos");
    
  
  
  try {
    // Import the wrapper's lib
    PyRun_SimpleString("import libpy_loop_function_interface as lib");
    object lib = import("libpy_loop_function_interface");
    

    // Launch Python init function
    object init_f = m_loop_main.attr("init");
    init_f();
  } catch (error_already_set) {
    PyErr_Print();
  }

}




void CPyLoopFunction::AddNewRobot(const boost::python::tuple& position, const boost::python::tuple& orientation) {
    // Extract position and orientation values from the Python tuples
    double posX = boost::python::extract<double>(position[0]);
    double posY = boost::python::extract<double>(position[1]);
    double posZ = boost::python::extract<double>(position[2]);

    double quatX = boost::python::extract<double>(orientation[0]);
    double quatY = boost::python::extract<double>(orientation[1]);
    double quatZ = boost::python::extract<double>(orientation[2]);
    double quatW = boost::python::extract<double>(orientation[3]);

    // Create a CVector3 and CQuaternion objects from the extracted values
    argos::CVector3 pos(posX, posY, posZ);
    argos::CQuaternion quat(quatX, quatY, quatZ, quatW);

    // Call the function to add a new robot entity with the converted values
    AddRobotEntity(pos, quat);
         //std::cout << "Acomes to fix pos with robots: " << m_nextRobotID;
}


void CPyLoopFunction::AddRobotEntity(const CVector3& position, const CQuaternion& orientation) {
    std::cout << "AGAIN: Adding robot, current count: " << m_nextRobotID << std::endl;

    // Create a unique ID for the new robot entity
    std::string controllerID = "greedy";

    // Create a new e-puck entity with consecutive IDs
    CEPuckEntity* pcEPuck = new CEPuckEntity(
        "bc" + std::to_string(m_nextRobotID), // Unique robot ID
        controllerID,                         // Controller ID
        position,
        orientation
    );

    // Add the new robot entity to the simulation
    AddEntity(*pcEPuck);

    // Get the controller of the added robot
    CPyController& cController = dynamic_cast<CPyController&>(pcEPuck->GetControllableEntity().GetController());

    try {
        // Access `allrobots` from the Python namespace
        PyObject* allRobotsObj = PyDict_GetItemString(m_loop_namesp.ptr(), "allrobots");

        if (allRobotsObj) {
            // Extract `allrobots` as a Python list
            boost::python::list allRobots = boost::python::extract<boost::python::list>(allRobotsObj);
            
            // Append the new robot to the list
            allRobots.append(cController.getActusensors());

            // Update the Python namespace
            m_loop_namesp["allrobots"] = allRobots;

   // Debugging
            std::cout << "Robot added to allrobots list. Total robots in C++: " 
                      << boost::python::len(allRobots) << std::endl;

            PyObject* checkAllRobotsObj = PyDict_GetItemString(m_loop_namesp.ptr(), "allrobots");
            if (checkAllRobotsObj == allRobotsObj) {
                std::cout << "C++: allrobots reference remains consistent in Python namespace." << std::endl;
            } else {
                std::cerr << "C++: allrobots reference mismatch detected!" << std::endl;
            }        } else {
            std::cerr << "Error: 'allrobots' not found in Python namespace." << std::endl;
        }
    } catch (const boost::python::error_already_set&) {
        PyErr_Print();
        std::cerr << "Error: Failed to update the allrobots list." << std::endl;
    }

    // Increment the ID counter for the next robot
    m_nextRobotID++;
}


/*
void CPyLoopFunction::RemoveRobotEntity(const std::string& robotID) {
    try {
     

        CEPuckEntity* robotEntity = dynamic_cast<CEPuckEntity*>(&GetSpace().GetEntity(robotID));
        if (!robotEntity) {
            std::cerr << "Error: Could not cast entity to CEPuckEntity for ID " << robotID << std::endl;
            return;
        }

        // Remove the entity from the simulation
        RemoveEntity(*robotEntity);
        std::cout << "Removed robot: " << robotID << std::endl;
PyObject* allRobotsObj = PyDict_GetItemString(m_loop_namesp.ptr(), "allrobots");
if (allRobotsObj) {
    boost::python::list allRobots = boost::python::extract<boost::python::list>(allRobotsObj);
    for (int i = 0; i < boost::python::len(allRobots); ++i) {
        try {
            // Debug: Print the string representation of the robot object
            std::string robotStr = boost::python::extract<std::string>(allRobots[i].attr("__str__")());
            std::cout << "Robot object at index " << i << ": " << robotStr << std::endl;

      

            // Attempt to extract the 'id' attribute if it's available
            try {
                std::string currentID = boost::python::extract<std::string>(allRobots[i].attr("id"));
                std::cout << "Robot ID: " << currentID << std::endl;
            } catch (const boost::python::error_already_set&) {
                std::cerr << "Error: 'id' attribute not found for robot at index " << i << std::endl;
            }

        } catch (const boost::python::error_already_set&) {
            PyErr_Print();
            std::cerr << "Error: Could not inspect robot at index " << i << std::endl;
        }
    }
} else {
    std::cerr << "Error: 'allrobots' not found in Python namespace." << std::endl;
}
    } catch (argos::CARGoSException& ex) {
        std::cerr << "Error: Could not remove robot with ID " << robotID << ". " << ex.what() << std::endl;
    } catch (const boost::python::error_already_set&) {
        PyErr_Print();
        std::cerr << "Error: Failed to update allrobots after removal." << std::endl;
    }
}
*/

/*
void CPyLoopFunction::RemoveRobotEntity(const std::string& robotID) {
    try {
        // Retrieve the robot entity by its ID
        CEPuckEntity& robotEntity = dynamic_cast<CEPuckEntity&>(GetSpace().GetEntity(robotID));
        
        // Remove the entity from the simulation
        RemoveEntity(robotEntity);
        
        // Optional: Remove the robot from the Python 'allrobots' list
        PyObject* allRobotsObj = PyDict_GetItemString(m_loop_namesp.ptr(), "allrobots");
        if (allRobotsObj) {
            boost::python::list allRobots = boost::python::extract<boost::python::list>(allRobotsObj);
            for (int i = 0; i < boost::python::len(allRobots); ++i) {
                // Assuming `getActusensors` provides a unique identifier matching `robotID`
                boost::python::object robot = allRobots[i];
                if (boost::python::extract<std::string>(robot.attr("id")) == robotID) {
                    allRobots.pop(i);
                    break;
                }
            }
            m_loop_namesp["allrobots"] = allRobots;
        }

        std::cout << "Removed robot: " << robotID << std::endl;
    } catch (argos::CARGoSException& ex) {
        std::cerr << "Error: Could not remove robot with ID " << robotID << ". " << ex.what() << std::endl;
    }
}
*/



boost::python::list CPyLoopFunction::GetAllRobots() const {
    boost::python::list allRobots;

    try {
        // Access `allrobots` from the Python namespace
        PyObject* allRobotsObj = PyDict_GetItemString(m_loop_namesp.ptr(), "allrobots");

        if (allRobotsObj) {
            // Extract `allrobots` as a Python list
            allRobots = boost::python::extract<boost::python::list>(allRobotsObj);

            // Debugging: Print the length of the allrobots list
            std::cout << "Retrieved allrobots list from Python namespace. Total robots: "
                      << boost::python::len(allRobots) << std::endl;
        } else {
            std::cerr << "Error: 'allrobots' not found in Python namespace." << std::endl;
        }
    } catch (const boost::python::error_already_set&) {
        PyErr_Print();
        std::cerr << "Error: Failed to retrieve allrobots list from Python namespace." << std::endl;
    }

    return allRobots;
}



void CPyLoopFunction::Reset() {
  // launch python reset function
  try {
    object reset_f = m_loop_main.attr("reset");
    reset_f();
  } catch (error_already_set) {
    PyErr_Print();
  }
}


void CPyLoopFunction::Destroy() {
  
  // Launch Python destroy function
  try {
    object destroy_f = m_loop_main.attr("destroy");
    destroy_f();
  } catch (error_already_set) {
    PyErr_Print();
  }
}

void CPyLoopFunction::PreStep() {
   // std::cout << "comes to presetep in cpp"<< std::endl;

  // Launch Python pre_step function
  try {
    object pre_step_f = m_loop_main.attr("pre_step");
    pre_step_f();
  } catch (error_already_set) {
    PyErr_Print();
  }
}

void CPyLoopFunction::PostStep() {
  // Launch Python post_step function
  
 // if (GetSpace().GetSimulationClock()==99){


        
  //}

  
  
  try {
    object post_step_f = m_loop_main.attr("post_step");
    post_step_f();
  } catch (error_already_set) {
    PyErr_Print();
  }
}


bool CPyLoopFunction::IsExperimentFinished() {

// Launch Python is_experiment_finished function
  try {
    object is_experiment_finished_f = m_loop_main.attr("is_experiment_finished");
    return is_experiment_finished_f();
  } catch (error_already_set) {
    PyErr_Print();
    return true;
  }

}




CColor CPyLoopFunction::GetFloorColor() {

// Launch Python is_experiment_finished function
  try {
    object get_floor_color_f = m_loop_main.attr("get_floor_color");

    std::cout << "Testing GetFloorColor" << std::endl;
    return CColor::WHITE;
  } catch (error_already_set) {
    PyErr_Print();
    return CColor::WHITE;
  }

}

void CPyLoopFunction::AddRobotArena(float x, float y , int num) {
  try{
  // Launch Python post_experiment function
      std::cout << "comes to add robot in cpp"<< std::endl;
     float pos_tick=0.0;
 CEPuckEntity* pcEPuck2 = nullptr;
        
            // Iterate over all e-puck entities
   
 CSpace::TMapPerType& m_cEpuck = GetSpace().GetEntitiesByType("epuck");
       //   CEPuckEntity* pcEPuck2 = nullptr;
//int numRobotsToMove = 6; // Change this value as needed

// Iterate over all e-puck entities
    for(auto& entry : m_cEpuck)
    {
        const std::string& id = entry.first;
        //for (int i = 0; i < numRobotsToMove; ++i) {
            if (id == "bc" + std::to_string(num)) {
                pos_tick += 0.1;
                pcEPuck2 = any_cast<CEPuckEntity*>(entry.second); // Store the entity pointer
                // Define the new position
               // CVector3 newPosition(0.9 - pos_tick, -0.93, 0.0); // Adjust the values as needed
                CVector3 newPosition(x, -y, 0.0); // Adjust the values as needed
                // Move the e-puck entity to the new position
                MoveEntity(pcEPuck2->GetEmbodiedEntity(), newPosition, CQuaternion());
                break; // Exit the loop once a matching robot is found
            }
        //}
    }   
  
} catch (const std::exception& e) {
        std::cerr << "Error in AddRobotArena: " << e.what() << std::endl;
    }
}

void CPyLoopFunction::PostExperiment() {
  // Launch Python post_experiment function
  try {
    object post_experiment_f = m_loop_main.attr("post_experiment");
    post_experiment_f();
  } catch (error_already_set) {
    PyErr_Print();
  }
}

BOOST_PYTHON_MODULE(libpy_loop_function_interface) {
    // Expose the CPyLoopFunction class
    class_<CPyLoopFunction>("CPyLoopFunction")
        // Expose the AddRobotArena function
        .def("AddRobotArena", &CPyLoopFunction::AddRobotArena)
        // Expose other functions as needed
         .def("AddRobotEntity", &CPyLoopFunction::AddRobotEntity)
         .def("AddNewRobot", &CPyLoopFunction::AddNewRobot)
         .def("GetAllRobots", &CPyLoopFunction::GetAllRobots)
         //.def("RemoveRobotEntity", &CPyLoopFunction::RemoveRobotEntity)


    ;

}

REGISTER_LOOP_FUNCTIONS(CPyLoopFunction, "py_loop_function")
