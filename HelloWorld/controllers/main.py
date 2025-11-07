#!/usr/bin/env python3
# This is the main control loop running in each argos robot

# /* Import Packages */
#######################################################################
import random, math
from random import randint
import time, sys, os

import json
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [os.environ['MAINFOLDER'], \
      os.environ['EXPERIMENTFOLDER']+'/controllers', \
      os.environ['EXPERIMENTFOLDER']
      ]
#log_name =' new_log7_24rob_9byz_bp_15_tps1'
from controllers.movement import RandomWalk, Navigate, Odometry, OdoCompass, GPS
from controllers.groundsensor import ResourceVirtualSensor, Resource, GroundSensor
from controllers.erandb import ERANDB
from controllers.rgbleds import RGBLEDs
from controllers.aux import *
from controllers.aux import Timer
from controllers.statemachine import *

from controllers.control_params import params as cp
from loop_functions.loop_params import params as lp

from toychain.src.Node import Node
from toychain.src.Block import Block, State
from toychain.src.utils import gen_enode

from toychain.src.consensus.ProofOfAuth import ProofOfAuthority
from toychain.src.Transaction import Transaction




# /* Global Variables */
#######################################################################
global robot
global toadd
global startFlag
global notdonemod
notdonemod=False
startFlag = False

global txList, tripList, submodules,num_contacts
txList, tripList, submodules = [], [], []

global clocks, counters, logs, txs
global mean_type, function_type,kparam, threshold_check,COMM_WINDOW,last_comm_check,comm_partners
clocks, counters, logs, txs = dict(), dict(), dict(), dict()


COMM_WINDOW = 500   # timesteps
last_comm_check = 0
comm_partners = set()


global estimate, totalWhite, totalBlack, byzantine, byzantine_style, log_folder,number_rob, paused, type_byz, removal_signal,actual,rem_list
TPS = int(lp['environ']['TPS'])
number_rob = int(lp['environ']['NUMROBOTS'])
grace_min = int(lp['environ']['GRACEMIN'])
grace_max = int(lp['environ']['GRACEMAX'])

try:
  log_name=(lp['environ']['LOGNAME'])
except Exception as e:
  print(f"Error: {e}")
estimate =0
totalWhite =0
totalBlack=0

byzantine = 0
# /* Logging Levels for Console and File */
#######################################################################
import logging
loglevel = 10
logtofile = False 
log_records = []
chain_size = []
sync_block = [] 

# /* Experiment Global Variables */
#######################################################################

clocks['peering'] = Timer(0.5)
clocks['sensing'] = Timer(1)
#clocks['ubi'] = Timer(100)
clocks['blocks']  = Timer(26)
clocks['comm'] = Timer(20)
#clocks['voting'] = Timer(3)
#clocks['remove'] = Timer(450)
#clocks['resend'] = Timer(100000)

clocks['newround'] = Timer(int(lp['environ']['NEWROUNDTIMER']))
clocks['voting'] = Timer(int(lp['environ']['VOTINGTIMER']))
clocks['remove'] = Timer(int(lp['environ']['REMOVETIMER']))
mean_type = float(lp['environ']['MEANTYPE'])
function_type = (lp['environ']['whichfuntion'])
collusion_tolerance = float(lp['environ']['collusiontolerance'])
kparam = float(lp['environ']['k'])
threshold_check = float(lp['environ']['thresholdcheck'])

type_byz = 0.125
removal_signal = False

global geth_peer_count

GENESIS = Block(0, 0000, [], [gen_enode(i+1) for i in range(int(lp['environ']['NUMROBOTS']))], 0, 0, 0, nonce = 1, state = State())#
#GENESIS = Block(0, 0000, [], [gen_enode(i+1) for i in range(int(16))], 0, 0, 0, nonce = 1, state = State())


global rwSpeed
rwSpeed = 250
####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################

def init():
  global clocks,counters, logs, submodules, me, rw, nav, odo, gps, rb, w3, fsm, rs, erb, rgb,odo2,gs, byzantine_style, log_folder, toadd
  global paused,robotremove, type_byz, removal_signal,rem_list, mean_type,function_type,k, threshold_check
  global COMM_WINDOW,last_comm_check,comm_partners,num_contacts
  robotID = str(int(robot.variables.get_id()[2:])+1)
  robotIP = '127.0.0.1'
  robot.variables.set_attribute("id", str(robotID))
  robot.variables.set_attribute("byzantine_style", str(0))
  robot.variables.set_attribute("consensus_reached",str("false"))
  robot.variables.set_attribute("scresources", "[]")
  robot.variables.set_attribute("foraging", "")
  robot.variables.set_attribute("state", "")
  robot.variables.set_attribute("quantity", "0")
  robot.variables.set_attribute("block", "")
  robot.variables.set_attribute("block", "0")
  robot.variables.set_attribute("hash", str(hash("genesis")))
  robot.variables.set_attribute("state_hash", str(hash("genesis")))
  #add varible to pause 
  robot.variables.set_attribute("paused", "False")


  # /* Initialize Console Logging*/
  #######################################################################

  log_folder = experimentFolder + '/'+str(log_name)+'/' + robotID + '/'

  # Monitor logs (recorded to file)
  name = 'monitor.log'
  os.makedirs(os.path.dirname(log_folder+name), exist_ok=True)
  os.makedirs(os.path.dirname(log_folder+'sc.csv'), exist_ok=True) 

  logging.basicConfig(filename=log_folder+name, filemode='w+', format='[{} %(levelname)s %(name)s] %(message)s'.format(robotID))
  logging.getLogger('sc').setLevel(10)
  logging.getLogger('w3').setLevel(10)
  logging.getLogger('poa').setLevel(10)
  robot.log = logging.getLogger()
  robot.log.setLevel(0)

  # /* Initialize submodules */
  #######################################################################
  # # /* Init web3.py */
  robot.log.info('Initialising Python Geth Console...')
  w3 = Node(robotID, robotIP, 1233 + int(robotID), ProofOfAuthority(GENESIS))

    # Register as sealer if this robotID is listed in NEW_SIGNERS
  try:
      new_signers = json.loads(os.environ.get('NEW_SIGNERS', '[]'))
  except Exception:
      new_signers = []

  if str(robotID) in new_signers:
      try:
          if w3.enode not in w3.consensus.auth_signers:
              w3.consensus.auth_signers.append(w3.enode)
              w3.consensus.signer_count = len(w3.consensus.auth_signers)
              robot.log.info(f"[INIT] Robot {robotID} added self as PoA signer")
          if hasattr(w3.consensus, 'block_generation'):
            try:
              w3.consensus.block_generation.refresh_index()
            except Exception:
              pass

          # Update block generator index if ProofOfAuth object already created
          #if hasattr(w3.consensus, 'block_generation') and hasattr(w3.consensus.block_generation, 'index'):
          #    w3.consensus.block_generation.index = w3.consensus.auth_signers.index(w3.enode)
          #    robot.log.info(f"[INIT] Updated block_generation.index to {w3.consensus.block_generation.index}")
      except Exception as e:
          robot.log.warning(f"[INIT] Could not add self to PoA auth_signers: {e}")


  # /* Init an instance of peer for this Pi-Puck */
  me = Peer(robotID, robotIP, w3.enode, w3.key)

  # /* Init E-RANDB __listening process and transmit function
  robot.log.info('Initialising RandB board...')
  erb = ERANDB(robot, cp['erbDist'] , cp['erbtFreq'])

  #/* Init Resource-Sensors */
  robot.log.info('Initialising resource sensor...')
  rs = ResourceVirtualSensor(robot)
  
  # /* Init Random-Walk, __walking process */
  robot.log.info('Initialising random-walk...')
  #rw = RandomWalk(robot, cp['scout_speed'])
  rw = RandomWalk(robot, rwSpeed)

  # /* Init Navigation, __navigate process */
  robot.log.info('Initialising navigation...')
  nav = Navigate(robot, cp['recruit_speed'])
  
  # /* Init odometry sensor */
  robot.log.info('Initialising Odo...')
  odo2 = Odometry(robot)
  
  # /* Init odometry sensor */
  robot.log.info('Initialising odometry...')
  odo = OdoCompass(robot)

  # /* Init GPS sensor */
  robot.log.info('Initialising gps...')
  gps = GPS(robot)

  # /* Init LEDs */
  rgb = RGBLEDs(robot)

  # /* Init Finite-State-Machine */
  fsm = FiniteStateMachine(robot, start = States.IDLE)

  # /* Init Ground sensor */
  robot.log.info('Initialising Ground sensor...')
  gs = GroundSensor(robot)
  
  # List of submodules --> iterate .start() to start all
  submodules = [erb,gs]

#########################################################################################################################
#### CONTROL STEP #######################################################################################################
#########################################################################################################################
global pos
pos = [0,0]
global last
last = 0
counter = 0
global checkt
global paused
global add
add =0
global robotremove
robotremove = -1
def controlstep():
  global counter,last, pos, clocks, counters, startFlag, startTime,notdonemod,odo2,checkt, byzantine, byzantine_style, log_folder
  global estimate, totalWhite, totalBlack,add,toadd, paused,robotremove, type_byz, removal_signal,actual,rem_list
  global rw, nav, odo, gps, rb, w3, fsm, rs, erb, mean_type,function_type,function_type,kparam, threshold_check
  global COMM_WINDOW,last_comm_check,comm_partners,num_contacts

      #startFlag=False
      #destroy()
  #startFlag = False 
  for clock in clocks.values():
    clock.time.step()
    checkt = clock.time.time_counter

  paused = str(robot.variables.get_attribute("paused"))

  if not startFlag:

        #if startFlag: 
        #w3.stop_mining()
    ##########################
    #### FIRST STEP ##########
    ##########################
    #SPECIFY THE ROBOTS TO START AT TIME AFTER THEY HAVE MOVED
    if(paused == "True"): # SPECIFY TIME TO START ROBOTS AND THEIR IDS   
      ##print("COMES HERE TO NOT JOIN", checkt)
      startFlag=False
      #print("I AM PAUSED not stop :(" , me.id)

      #if(notdonemod==False):
      #for module in submodules:
          #try:
          #  module.start()
          #except:
          #  robot.log.critical('Error Starting Module: %s', module)
           # sys.exit()
        #notdonemod=True
      #else:
        # Perform submodules step
        #for module in [erb, rs,rw]:
          #module.step()
    else:

        startFlag=True
        startTime = 0
        robot.log.info('--//-- Starting Experiment --//--')
        for module in submodules:
          try:
            module.start()
          except:
            robot.log.critical('Error Starting Module: %s', module)
            sys.exit()
        for log in logs.values():
          log.start()
        #print(odo2.getPosition())
        for clock in clocks.values():
          clock.reset()
        if(paused == "True"):
          print("I am paused and i come here!!!")

        #w3.sc.registerRobot()
        # Startup transactions
        #SPECIFY THE ROBOTS THAT ARE BYZANTINE
        #if int(me.id) ==2 or int(me.id) == 2 or int(me.id) == 2 or int(me.id) == 5 or int(me.id) == 6 or int(me.id) == 3:
        #  byzantine = 1

        byzantine_style = int(robot.variables.get_attribute("byzantine_style"))
        if(int(me.id)>1600):
          if random.random() < 0.5:
            byzantine_style = 1
            robot.variables.set_attribute("isByz", "True")
            print("robot is byzantine: ", me.id)
          else: byzantine_style = 0
        print("--//-- Registering robot --//--")
        txdata = {'function': 'registerRobot', 'inputs': []}
        tx = Transaction(sender = me.id, data = txdata)
        w3.send_transaction(tx)

        w3.start_tcp()
        w3.start_mining()


  else:
    global nav, rw,robotremove, type_byz,function_type
    global COMM_WINDOW,last_comm_check,comm_partners,num_contacts
    ###########################
    ######## ROUTINES #########
    ###########################



    def peering():
      global estimate, totalWhite, totalBlack, checkt, byzantine, byzantine_style, log_folder,number_rob, toadd, paused, robotremove, actual, num_contacts
      # Get the current peers from erb
      erb_enodes = {w3.gen_enode(peer.id) for peer in erb.peers}

      # Add peers on the toychain
      for enode in erb_enodes-set(w3.peers):
        try:
          w3.add_peer(enode)

      
          #Say Hello
          #txdata = {'function': 'sendEstimate','inputs':[str(estimate)]}
          #tx = Transaction(sender=me.id, data=txdata)
          #w3.send_transaction(tx)
        except Exception as e:
          raise e
      if clocks['blocks'].query():  
      # Remove peers from the toychain
        for enode in set(w3.peers)-erb_enodes:
          try:
            w3.remove_peer(enode)
          except Exception as e:
            raise e
        clocks['blocks']  = Timer(randint(grace_min,grace_max))

      # Turn on LEDs according to geth peer count
      if(int(me.id)<7):
        rgb.setLED(rgb.all, rgb.presets1.get(len(w3.peers), 3*['blue']))
      else:
        rgb.setLED(rgb.all, rgb.presets.get(len(w3.peers), 3*['red']))

    # Perform submodules step
    for module in [erb, rs, rw, gs,odo]:
      module.step()
    mean = w3.sc.getMean() 
    #get estimate
    #print(byzantine_style)
    if byzantine_style == 1:
      #print("I AM BYZANTINEEEEE", me.id)
      #estimate = 0
      newValues = gs.getNew()
      for value in newValues:
        if value != 0:
          totalWhite +=1
        else:
          totalBlack+=1
      actual = (0.5+totalWhite)/(totalBlack+totalWhite+1)
      #print("The actual byzantine estimate", actual)
      #estimate = add_noise_to_estimate(actual, mean)
      #print("The changed estimate", estimate)
      estimate=0
    elif byzantine_style == 2:
      estimate = 1    
    elif byzantine_style == 3:
      # 50% chance white, 50% change black
      p = random.uniform(0, 1)
      if p < 0.5:
        estimate = 0
      else:
        estimate = 1
    elif byzantine_style == 4:
      estimate = random.uniform(0, 1)    
    
    else:#Get value from the ground
      newValues = gs.getNew()
      for value in newValues:
        if value != 0:
          totalWhite +=1
        else:
          totalBlack+=1
      estimate = (0.5+totalWhite)/(totalBlack+totalWhite+1)
    myBlocksUBI = [0, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]
    registered = w3.sc.amIregistered(me.id) #does the robot have any payouts
    if(registered == False):
        print("--//-- Registering robot --//--")
        txdata = {'function': 'registerRobot', 'inputs': []}
        tx = Transaction(sender = me.id, data = txdata)
        w3.send_transaction(tx)



    if(paused == "True"):
          print("#######   I AM PAUSED and to be DESTROYEDDDDDDDD    yes start :(" , me.id)
          #self.epuck_wheels.set_speed(0, 0)
          nav.stop()
          nav.stop()

          nav.stop()

          #robot.epuck_wheels.set_speed(0, 0)

          #w3.stop_mining()
          #if startFlag: 
          destroy()
          startFlag = False
    #if 'REM_LIST' in os.environ:
    #    rem_list = json.loads(os.environ['REM_LIST'])


    global toadd,robotremove, removal_signal,function_type,function_type,kparam, threshold_check,num_contacts

    # Step the ERANDB module to update detected peers
    erb.step()

    # Get newly detected robot IDs this timestep
    num_contacts = erb.getNew()

    # Add them to the set for this COMM_WINDOW
    comm_partners.update(num_contacts)

    # Every COMM_WINDOW timesteps, evaluate density
    #if checkt - last_comm_check >= COMM_WINDOW:
    """
    if clocks['comm'].query():
        #print("comes to check")
        num_contacts = len(comm_partners)

        print(f"Robot {me.id} saw {num_contacts} unique robots in last {COMM_WINDOW} steps")
        if num_contacts <0:
            # Trigger SC vote to allow robot addition
            txdata = {'function': 'signal_add_robot', 'inputs': [me.id]}
            tx = Transaction(sender=me.id, data=txdata)
            w3.send_transaction(tx)
            print(f"Robot {me.id} signaled to add a robot due to low density")

        # Reset for next window
        comm_partners.clear()
        last_comm_check = checkt
   

    if clocks['comm'].query():  # every 20 TS
        blockchain = w3.chain
        recent_blocks = list(blockchain)[-5:]  # take last 5 blocks
        block_gap_streak = 0

        # Check gaps between consecutive recent blocks
        for i in range(1, len(recent_blocks)):
            gap = recent_blocks[i].timestamp - recent_blocks[i-1].timestamp
            if gap > 50:
                block_gap_streak += 1
                print(f"[Robot {me.id}] Block gap {gap}s > 15s (streak {block_gap_streak})")
            else:
                block_gap_streak = 0  # reset streak if a block is timely

            if block_gap_streak >= 1:
                txdata = {'function': 'signal_add_robot', 'inputs': [me.id]}
                tx = Transaction(sender=me.id, data=txdata)
                w3.send_transaction(tx)
                print(f"[Robot {me.id}] Signaled SC to add a robot (3 consecutive slow blocks)")
                break  # stop after signaling once

    """

    """
    if clocks['comm'].query():  # every 20 TS
        blockchain = w3.chain
        recent_blocks = list(blockchain)[-5:]  # take last 5 blocks
        if len(recent_blocks) < 5:
            return  # not enough history yet

        # --- Rolling average gap ---
        gaps = [
            recent_blocks[i].timestamp - recent_blocks[i - 1].timestamp
            for i in range(1, len(recent_blocks))
        ]
        avg_gap = sum(gaps) / len(gaps)

        # --- Miner diversity (disabled for now) ---
        unique_ratio = 0
        print(f"[Robot {me.id}] avg_gap={avg_gap:.2f}, miner_div={unique_ratio:.2f}")

        # --- Counter for how many times avg_gap > 60 ---
        if not hasattr(me, "gap_exceed_count"):
            me.gap_exceed_count = 0

        if avg_gap > 90:
            me.gap_exceed_count += 1
        else:
            me.gap_exceed_count = 0  # reset if condition not met

        # --- Decision rule ---
        if me.gap_exceed_count >= 5:
            txdata = {'function': 'signal_add_robot', 'inputs': [me.id]}
            tx = Transaction(sender=me.id, data=txdata)
            w3.send_transaction(tx)
            print(f"[Robot {me.id}] Signaled SC to add a robot "
                  f"(avg_gap={avg_gap:.2f}, miner_div={unique_ratio:.2f})")

            # Reset after signaling
            me.gap_exceed_count = 0
      """
    if clocks['comm'].query():  # every 20 TS
        blockchain = w3.chain
        recent_blocks = list(blockchain)[-5:]  # take last 5 blocks
        if len(recent_blocks) < 5:
            return  # not enough history yet

        # --- Rolling average gap ---
        gaps = [
            recent_blocks[i].timestamp - recent_blocks[i - 1].timestamp
            for i in range(1, len(recent_blocks))
        ]
        avg_gap = sum(gaps) / len(gaps)

        # --- Miner diversity (disabled for now) ---
        unique_ratio = 0
        print(f"[Robot {me.id}] avg_gap={avg_gap:.2f}, miner_div={unique_ratio:.2f}")

        # --- Counter for add condition (avg_gap > 90) ---
        if not hasattr(me, "gap_exceed_count"):
            me.gap_exceed_count = 0

        if avg_gap > 60:
            me.gap_exceed_count += 1
        else:
            me.gap_exceed_count = 0  # reset if condition not met

        # --- Counter for remove condition (avg_gap < 80) ---
        if not hasattr(me, "gap_below_count"):
            me.gap_below_count = 0

        if avg_gap < 50:
            me.gap_below_count += 1
        else:
            me.gap_below_count = 0  # reset if condition not met

        # --- Decision rule for ADD ---
        if me.gap_exceed_count >= 5:
            txdata = {'function': 'signal_add_robot', 'inputs': [me.id]}
            tx = Transaction(sender=me.id, data=txdata)
            w3.send_transaction(tx)
            print(f"[Robot {me.id}] Signaled SC to ADD a robot "
                  f"(avg_gap={avg_gap:.2f})")
            me.gap_exceed_count = 0

        # --- Decision rule for REMOVE ---
        if me.gap_below_count >= 5:
            txdata = {'function': 'signal_remove_robot', 'inputs': [me.id]}
            tx = Transaction(sender=me.id, data=txdata)
            w3.send_transaction(tx)
            print(f"[Robot {me.id}] Signaled SC to REMOVE a to robot "
                  f"(avg_gap={avg_gap:.2f})")
            me.gap_below_count = 0


    #removal_signal = w3.sc.shouldIremove()

    if clocks['newround'].query():#check after every interval timesteps
      sync = "Time: "+str(checkt)+" ID: "+str(me.id)+ " Blocks: "+ str(w3.get_new_blocks())+" \n"
      #sync_block.append(sync)

      if(int(sync.split(' ')[5])>0):
       sync_block.append(sync)
      #print((sync.split(' ')))
      #print(int(sync.split(' ')[5]))



      #balance = w3.sc.getBalance(me.id)
      robbalance = w3.sc.getRobBalance(me.id) #the balance of robots
      block  = w3.get_block('latest') #to get latest block heigh of robots
      #      receivedUBI= w3.sc.getInboundToken(me.id) #the total ubi it has received
      inboundtoken= w3.sc.getInboundToken(me.id) #the total ubi it has received
      robotCount = w3.sc.getRobotCount() #how manybots
      newRound = w3.sc.isNewRound() #new round?
      doIhavePayouts = w3.sc.doIhavePayouts(me.id) #does the robot have any payouts
      getTotPayout = w3.sc.getTotPayout(me.id) #what is total payouts done
      #shouldIaskforUBI = w3.sc.doIhavePayouts(me.id)
      payout = w3.sc.getPayout(me.id)
      #for i in range(len(myBlocksUBI)): #in those specific blocks, ask for ubi
      #  if block.height == myBlocksUBI[i]:
      #toadd = 0 #how manybots
      #print("to add controller: ", toadd)
      #get ubi
      txdata1 = {'function': 'askForUBI', 'inputs': []}
      tx1 = Transaction(sender = me.id, data = txdata1)
      w3.send_transaction(tx1)
      balance = w3.sc.getBalance(me.id)
      print("Robot: ",me.id,"Payout: ", doIhavePayouts)
      

      #shouldweRemove = w3.sc.toRemove() #new round?
      #removalList = w3.sc.getRemovalList()
      #print(removalList)
      #os.environ['ADD'] = json.dumps(removalList) #communicate to loopfunction to move robot aside and add more robots


      """
      if(me.id in removalList):
        #whotoRemove=w3.sc.getRobRemove()
        #if(me.id == whotoRemove):
          toadd = int(me.id)
          os.environ['ADD'] = str(toadd)
          print("/////////In controller robot signalled to be removed: "+ str(me.id)+"by robot: "+str(me.id))
          toadd = whotoRemove
          txdata1 = {'function': 'removed_robot_reset', 'inputs': []}
          tx1 = Transaction(sender = me.id, data = txdata1)
          w3.send_transaction(tx1)
          #w3.stop_mining()
      """
      #if int(me.id)>5:
      #  print("my enode: %s", w3.enode)

      if(doIhavePayouts):# if robot has payouts then get them
        txdata1 = {'function': 'askForPayout', 'inputs': []}
        tx1 = Transaction(sender = me.id, data = txdata1)
        w3.send_transaction(tx1)


      
      if(w3.sc.isNewRound() == True):###### and robbalance > 0): #every new round update mean
        txdata = {'function': 'updateMean', 'inputs': []}
        tx = Transaction(sender = me.id, data = txdata)
        w3.send_transaction(tx) 
      #print("Robot: ",me.id,"Time: " , checkt, "totPayout: ", getTotPayout, "robBalance: ",robbalance,
      #"Tot UBI rec: ", receivedUBI, "Block height: ", block.height, "Robot count: ", robotCount,
      #"New round: ", newRound)

      mean = w3.sc.getMean()
      converged = w3.sc.isConverged()

      logging = "Robot: "+ str(me.id) +" Time: " + str(checkt)+ " totPayout: "+ str(getTotPayout) +" robBalance: "+ str(robbalance) + " Tot UBI rec: "+ str(inboundtoken)+ " Block height: "+ str(block.height)+ " Robot count: "+ str(robotCount)+ " New round: "+ str(newRound)+" myestimate: "+str(estimate)+" mean: "+ str(mean)+ " converged: "+ str(converged)+" comm "+ str(len(comm_partners))+"\n"
      print(logging)
      # List to store log records

      # Parse the log string into a list of values
      #log_values = logging.split()
      size_rec = "Robot: "+ str(me.id) +" Time: " + str(checkt)+ "Size: "+ str(sys.getsizeof(w3.chain))+  " isByz: "+  str(byzantine_style) + "\n"
      # Extract the values by filtering out the labels
      #parsed_values = [log_values[i + 1] for i in range(0, len(log_values), 2)]

      # Add the parsed values to the log_records list
      log_records.append(logging)
      chain_size.append(size_rec)
      #with open(log_folder+str(me.id), 'a') as f:
      #  f.write((str(logging)))


      if converged: #check if converged
        print("converged", mean)
        robot.variables.set_attribute("consensus_reached",str("true"))
      
      #if ubi != 0 and 
    if clocks['voting'].query():#after specific timetspes try to vote
      robbalance = w3.sc.getRobBalance(me.id)
  #    #if(me.id == '4'):
      if robbalance > 39 and checkt>00:
        #print("before: ", balance)
        txdata = {'function': 'send_vote', 'inputs': [estimate]}
        tx = Transaction(sender = me.id, data = txdata)
        w3.send_transaction(tx)
        #print("after: ", balance)
     # balance = w3.sc.getBalance(me.id)
      #if(me.id == '4'):

      
      
      




    # Perform clock steps
    #for clock in clocks.values():
      #print(clock.time.time_counter)
    #  clock.time.step()

    if clocks['peering'].query():
      peering()

    w3.step()

    #print(sys.getsizeof(w3.chain))  
    
    #if (counter % 100) == 0:
      
    #  print("Robot",me.id,"estimate is ", w3.sc.getEstimate())
    #counter +=1

    #print(str(w3.get_block('last')))
    # Update blockchain state on the robot C++ object
    robot.variables.set_attribute("block", str(w3.get_block('last').height))
    robot.variables.set_attribute("block_hash", str(w3.get_block('last').hash))
    robot.variables.set_attribute("state_hash", str(w3.get_block('last').state.state_hash))



def reset():
  pass


def destroy():
    if startFlag:
        w3.stop_mining()
        txs = w3.get_all_transactions()
        if len(txs) != len(set([tx.id for tx in txs])):
            print(f'REPEATED TRANSACTIONS ON CHAIN: #{len(txs)-len(set([tx.id for tx in txs]))}')

        for key, value in w3.sc.state.items():
            print(f"{key}: {value}")

        name   = 'sc.csv'
        header = ['TIMESTAMP', 'BLOCK', 'HASH', 'PHASH', 'BALANCE', 'TX_COUNT','MEAN','VOTECOUNT','VOTEOKCOUNT','INBOUNDTOKEN','CONSENSUS'] 
        #logs['sc'] = Logger(f"{experimentFolder}/logs/{me.id}/{name}", header, ID = me.id)
        #experimentFolder + '/new_log2_24rob_9byz_bp_3_tps1/' + robotID + '/'
        logs['sc'] = Logger(f"{experimentFolder}/{log_name}/{me.id}/{name}", header, ID = me.id)

        
        name   = 'block.csv'
        header = ['TELAPSED','TIMESTAMP','BLOCK', 'HASH', 'PHASH', 'DIFF', 'TDIFF', 'SIZE','TXS', 'UNC', 'PENDING', 'QUEUED']
        logs['block'] = Logger(f"{experimentFolder}/{log_name}/{me.id}/{name}", header, ID = me.id)


        # Log each block over the operation of the swarm
        blockchain = w3.chain
        for block in blockchain:
            block_str = repr(block)  # Convert Block object to string using __repr__
            #f.write(block_str)
            #f.write("\n")
        
            block_size = sys.getsizeof(block_str)  # Get the size of the block string
            #with open(bname, 'w') as f:
            #   f.write(repr(block))
            #    f.write("\n")
            #size=os.path.getsize(bname)

            logs['block'].log(
                [w3.custom_timer.time()-block.timestamp, 
                block.timestamp, 
                block.height, 
                block.hash, 
                block.parent_hash, 
                block.difficulty,
                block.total_difficulty,
                block_size, 
                #sys.getsizeof(block), #/ 1024, 
                len(block.data), 
                0,
                sys.getsizeof(blockchain)
                ])
            totalPaid = 0
            balances = 0
            if me.id in block.state.robot:
                totalPaid = block.state.robot[me.id].get("totalPaid", 0)
                balances = block.state.robot[me.id].get("robBalance", 0)

            logs['sc'].log(
                [block.timestamp, 
                block.height, 
                block.hash, 
                block.parent_hash, 
                balances,
                block.state.n,
                block.state.mean,
                block.state.voteCount,
                block.state.voteOkCount,
                totalPaid,
                block.state.consensusReached
                ])
        filename = f"{experimentFolder}/{log_name}/{me.id}/{me.id}.txt"
        # Function to write log records to file
        with open(filename, 'w') as file:
               file.writelines(log_records)
        bname = f"{experimentFolder}/{log_name}/{me.id}/blocks.txt"
        with open(bname, 'w') as file:
               file.writelines(chain_size)
        sname = f"{experimentFolder}/{log_name}/{me.id}/sync.txt"
        with open(sname, 'w') as file:
               file.writelines(sync_block)


        removalperround = w3.sc.getRemovalCountvote()

        rname = f"{experimentFolder}/{log_name}/{me.id}/removal.txt"
        with open(rname, 'w') as file:
          for entry in removalperround:
            file.write(str(entry) + "\n") 
               #file.writelines(removalperround)
    print('Killed robot '+ me.id)


#########################################################################################################################
#########################################################################################################################
#########################################################################################################################


def getEnodes():
  return [peer['enode'] for peer in w3.geth.admin.peers()]

def getEnodeById(__id, gethEnodes = None):
  if not gethEnodes:
    gethEnodes = getEnodes() 

  for enode in gethEnodes:
    if readEnode(enode, output = 'id') == __id:
      return enode

def getIds(__enodes = None):
  if __enodes:
    return [enode.split('@',2)[1].split(':',2)[0].split('.')[-1] for enode in __enodes]
  else:
    return [enode.split('@',2)[1].split(':',2)[0].split('.')[-1] for enode in getEnodes()]