#!/usr/bin/env python3

import os, sys, math
import random
import logging, time, json
import libpy_loop_function_interface
from hexbytes import HexBytes

from controllers.aux import Vector2D, Logger, Timer, Accumulator, mydict, identifiersExtract, Counter
from controllers.groundsensor import Resource
from loop_functions.loop_params import params as lp

from controllers.control_params import params as cp
from loop_functions.loop_helpers import *
from toychain.src.Node import Node
from toychain.src.Block import Block, State
from toychain.src.utils import gen_enode

# Initialize loop function interface
loop_function_interface = libpy_loop_function_interface.CPyLoopFunction()

# shared file for new signers (uses EXPERIMENTFOLDER)
EXPERIMENT_FOLDER = os.environ.get('EXPERIMENTFOLDER', '.')
NEW_SIGNERS_FILE = os.path.join(EXPERIMENT_FOLDER, 'NEW_SIGNERS.json')
REMOVE_FILE = os.path.join(EXPERIMENT_FOLDER, 'remove_list.json')  # shared state file

# always create (overwrite) the file
try:
    with open(NEW_SIGNERS_FILE, 'w') as f:
        json.dump([], f)
except Exception as e:
    print(f"[LoopFunction] Could not create NEW_SIGNERS file: {e}")

try:
    with open(REMOVE_FILE, 'w') as f:
        json.dump([], f)
except Exception as e:
    print(f"[LoopFunction] Could not create remove file: {e}")

experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [os.environ['MAINFOLDER'],
             os.environ['EXPERIMENTFOLDER']+'/controllers',
             os.environ['EXPERIMENTFOLDER']]
log_name = lp['environ']['LOGNAME']

# Global variables
global startFlag, stopFlag, startTime
global toadd
global saved_the_removed
saved_the_removed = 0
startFlag = False
stopFlag = False
startTime = 0

# Initialize RAM and CPU usage
global RAM, CPU
RAM = getRAMPercent()
CPU = getCPUPercent()

TPS = int(lp['environ']['TPS'])

# Initialize timers/accumulators/logs
global clocks, accums, logs, other, addspacebetweenrobots, byzadded, time_rob_added
time_rob_added = 0
byzadded = 0
addspacebetweenrobots = 0
clocks, accums, logs, other = dict(), dict(), dict(), dict()
other['countsim'] = Counter()
clocks['simlog'] = Timer(10*TPS)
clocks['byzlog'] = Timer(50)


def _read_new_signers_file():
    try:
        with open(NEW_SIGNERS_FILE, 'r') as f:
            arr = json.load(f)
            if not isinstance(arr, list):
                return []
            return arr
    except Exception:
        return []


def _append_to_new_signers(ids):
    cur = _read_new_signers_file()
    changed = False
    for rid in ids:
        rs = str(rid)
        if rs not in cur:
            cur.append(rs)
            changed = True
    if changed:
        try:
            with open(NEW_SIGNERS_FILE, 'w') as f:
                json.dump(cur, f)
        except Exception as e:
            print(f"[LoopFunction] Error writing NEW_SIGNERS file: {e}")


def update_allrobots():
    """Refresh Python allrobots list from the C++ wrapper."""
    global allrobots
    try:
        allrobots = loop_function_interface.GetAllRobots()
        print(f"[LoopFunction] Updated allrobots, total: {len(allrobots)}")
    except Exception as e:
        print(f"[LoopFunction] Error updating allrobots: {e}")


def init():
    global robot_ids, addspacebetweenrobots, NEXT_ROBOT_ID
    robot_ids = {}

    try:
        NEXT_ROBOT_ID = int(lp['environ']['NUMROBOTS']) + 1
    except Exception:
        NEXT_ROBOT_ID = len(allrobots) + 1 if 'allrobots' in globals() else 1

    for robot in allrobots:
        try:
            robot_id = int(robot.variables.get_attribute("id"))
            robot_ids[robot] = robot_id
            print(f"Robot initialized: {robot}, ID: {robot_id}")
        except AttributeError as e:
            print(f"Error initializing robot ID: {e}")

    byzantines = random.sample(allrobots, k=int(lp['environ']['NUMBYZANTINE']))
    for robot in byzantines:
        try:
            robot.variables.set_attribute("byzantine_style", lp['environ']['BYZANTINESWARMSTYLE'])
            robot.variables.set_attribute("isByz", "True")
            print(f"Making robot {robot.variables.get_attribute('id')} Byzantine.")
        except Exception as e:
            print(f"Error making robot Byzantine: {e}")

    file = 'simulation.csv'
    header = ['TPS', 'RAM', 'CPU']
    logs['simulation'] = Logger(f"{experimentFolder}/{log_name}/{file}", header, ID='0')

    file1 = 'removal.csv'
    header1 = ['Removal_list', 'TS']
    logs['removal'] = Logger(f"{experimentFolder}/{log_name}/{file1}", header1, ID='0')


def pre_step():
    global allrobots, previous_add_list, previous_remove_list, NEXT_ROBOT_ID, removed_robots, addspacebetweenrobots

    if 'previous_add_list' not in globals():
        previous_add_list = set()
    if 'previous_remove_list' not in globals():
        previous_remove_list = set()
    if 'removed_robots' not in globals():
        removed_robots = set()
    if 'addspacebetweenrobots' not in globals():
        addspacebetweenrobots = 0.0

    # --- Handle ADD ---
    if 'ADD' in os.environ:
        try:
            add_list = json.loads(os.environ['ADD'])
        except Exception:
            add_list = []
        print("[Loop controller] ADD_LIST: ", add_list)

        new_ids = set(add_list) - previous_add_list
        if new_ids:
            assigned_ids = []
            for _ in new_ids:
                robot_id = NEXT_ROBOT_ID
                NEXT_ROBOT_ID += 1
                assigned_ids.append(robot_id)

                try:
                    loop_function_interface.AddNewRobot(
                        (random.uniform(-0.7, 0.7), random.uniform(-0.7, 0.7), 0.0),
                        (0.0, 0.0, 0.0, 1.0)
                    )
                    print(f"[LoopFunction] Spawned new robot {robot_id} for ADD signal")
                except Exception as e:
                    print(f"[LoopFunction] Error spawning robot {robot_id}: {e}")

            update_allrobots()  # Refresh allrobots after additions

            try:
                current_signers = json.loads(os.environ.get("AUTH_SIGNERS", "[]"))
            except Exception:
                current_signers = []

            for rid in assigned_ids:
                enode = gen_enode(rid)
                if enode not in current_signers:
                    current_signers.append(enode)

            print(f"[LoopFunction] Updated AUTH_SIGNERS with {len(current_signers)} signers")
            _append_to_new_signers(assigned_ids)
            previous_add_list.update(new_ids)

    # --- Handle REMOVE ---
    try:
        with open(REMOVE_FILE, "r") as f:
            remove_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        remove_list = []

    print("[LoopFunction] REMOVE_LIST:", remove_list, removed_robots)

    new_removals = set(remove_list) - previous_remove_list
    print("[LoopFunction] new rem:", new_removals)

    for robot_id in new_removals:
        robot_id_str = f"bc{int(robot_id)-1}"
        print("removed robots from system: ", removed_robots)
        if robot_id_str not in removed_robots:
            for robot in allrobots:
                if int(robot.variables.get_attribute("id")) == int(robot_id):
                    robot.variables.set_attribute("paused", "True")
                    print(f"[LoopFunction] Pausing robot {robot_id}")

                    loop_function_interface.AddRobotArena(
                        0.9 - addspacebetweenrobots,
                        0.98,
                        int(robot_id) - 1
                    )
                    addspacebetweenrobots += 0.08
                    print(f"[LoopFunction] Moving robot {robot_id} out of arena")

            removed_robots.add(robot_id_str)

        # update AUTH_SIGNERS
        try:
            current_signers = json.loads(os.environ.get("AUTH_SIGNERS", "[]"))
        except Exception:
            current_signers = []

        enode = gen_enode(int(robot_id))
        if enode in current_signers:
            current_signers.remove(enode)
            os.environ["AUTH_SIGNERS"] = json.dumps(current_signers)
            print(f"[LoopFunction] Updated AUTH_SIGNERS after removal, now {len(current_signers)} signers")

    previous_remove_list.update(new_removals)


def post_step():
    global startFlag, clocks, accums, RAM, CPU
    other['countsim'].step()
    clocks['byzlog'].time.step()

    if clocks['simlog'].query():
        RAM = getRAMPercent()
        CPU = getCPUPercent()
    TPS = round(1/(time.time()-logs['simulation'].latest))
    logs['simulation'].log([TPS, CPU, RAM])

    # --- ADD 20 ROBOTS at timestep 20 ---
    if other['countsim'].count == 10000:
        print("[LoopFunction] Adding 20 robots at timestep 20")

        try:
            existing_robots = int(lp['environ']['NUMROBOTS'])
        except Exception:
            existing_robots = len(allrobots)

        new_robot_ids = [existing_robots + i + 1 for i in range(24)]
        spawned_ids = []

        for robot_id in new_robot_ids:
            try:
                loop_function_interface.AddNewRobot(
                    (random.uniform(-0.7, 0.7), random.uniform(-0.7, 0.7), 0.0),
                    (0.0, 0.0, 0.0, 1.0)
                )
                print(f"[LoopFunction] Spawned robot {robot_id}")
                spawned_ids.append(robot_id)
            except Exception as e:
                print(f"[LoopFunction] Error spawning robot {robot_id}: {e}")

        update_allrobots()  # Refresh allrobots after additions

        if spawned_ids:
            _append_to_new_signers(spawned_ids)
            lp['environ']['NUMROBOTS'] = str(int(lp['environ']['NUMROBOTS']) + len(spawned_ids))
            print(f"[LoopFunction] Updated NUMROBOTS to {lp['environ']['NUMROBOTS']}")


def is_experiment_finished():
    pass


def reset():
    pass


def destroy():
    pass


def post_experiment():
    print("Finished from Python!")
