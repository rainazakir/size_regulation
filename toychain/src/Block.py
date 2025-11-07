from random import randint
from json import loads as jsload
import json
from copy import copy
from toychain.src.utils import compute_hash, transaction_to_dict
from os import environ
import os, random
import math
import logging
logger = logging.getLogger('sc')

class Block:
    """
    Class representing a block of a blockchain containing transactions
    """

    def __init__(self, height, parent_hash, data, miner_id, timestamp, difficulty, total_diff, nonce=None,
                 state_var=None, state = None):
        self.height = height
        self.number = height
        self.parent_hash = parent_hash
        self.data = data
        self.miner_id = miner_id
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.total_difficulty = total_diff + difficulty

        if state:
            self.state = state
        else:
            self.state = State(state_var)

        self.nonce = nonce
        if nonce is None:
            self.nonce = randint(0, 1000)

        self.transactions_root = self.transactions_hash()
        self.hash = self.compute_block_hash()

    def compute_block_hash(self):
        """
        computes the hash of the block header
        :return: hash of the block
        """
        _list = [self.height, self.parent_hash, self.transactions_hash(), self.miner_id, self.timestamp,
                 self.difficulty,
                 self.total_difficulty, self.nonce]

        self.hash = compute_hash(_list)

        return self.hash

    def transactions_hash(self):
        """
        computes the hash of the block transactions
        :return: the hash of the transaction list
        """
        transaction_list = [transaction_to_dict(t) for t in self.data]
        self.transactions_root = compute_hash(transaction_list)
        return self.transactions_root

    def get_header_hash(self):
        header = [self.parent_hash, self.transactions_hash(), self.timestamp, self.difficulty, self.nonce]
        return compute_hash(header)

    def increase_nonce(self):  ###### POW
        self.nonce += 1

    def __repr__(self):
        """
        Translate the block object in a string object
        """
        return f"## H: {self.height}, D: {self.difficulty}, TD: {self.total_difficulty}, P: {self.miner_id}, BH: {self.hash[0:5]}, TS:{self.timestamp}, #T:{len(self.data)}, SH:{self.state.state_hash[0:5]}##"


class StateMixin:
    @property
    def getBalances(self):
        return self.balances
    
    @property
    def getN(self):
        return self.n
        
    @property
    def call(self):
        return None
    
    @property
    def state_variables(self):
        return {k: v for k, v in vars(self).items() if not (k.startswith('_') or k == 'msg' or k == 'block' or k == 'private')}
    
    @property
    def state(self):
        return {k: v for k, v in vars(self).items() if not (k.startswith('_') or k == 'msg' or k == 'block' or k == 'private')}

    @property
    def state_hash(self):
        return compute_hash(self.state.values())
    
    def apply_transaction(self, tx, block):

        self.msg = tx
        self.block = block

        self.balances.setdefault(tx.sender, 0)
        self.balances.setdefault(tx.receiver, 0)

        # Check sender funds
        if tx.value and self.balances[tx.sender] < tx.value:
            return
        
        # Apply the transfer of value
        self.balances[tx.sender] -= tx.value
        self.balances[tx.receiver] += tx.value
        
        # Apply the other functions contained in data
        self.n += 1

        if tx.data and 'function' in tx.data and 'inputs' in tx.data:
            function = getattr(self, tx.data.get("function"))
            inputs   = tx.data.get("inputs")
            try:
                function(*inputs) 
            except Exception as e:
                raise e

class State(StateMixin):

    def __init__(self, state_variables = None):

        if state_variables is not None:
            for var, value in state_variables.items(): setattr(self, var, value)     

        else:
            self.private     = {}
            self.n           = 0
            self.balances    = {}
            #self.robots      = {}
            self.mean = 0
            self.threshold = 0
            self.ticketPrice = 40
            self.tau = 0
            self.consensusReached = False
            self.startBlock = 0
            self.valueUBI = 20
            #self.totalUBI = {}
            self.publicPayoutUBI = 0
            self.publicLength = 0
            self.roundCount = 0
            self.voteCount = 0
            self.voteOkCount = 0
            self.robotCount = 0
            self.lastUpdate = 0
            self.newRound = False
            self.blocksUBI = [0, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]
            self.W_n = 0
            self.robotsToPay = []
            self.robot = {}
            self.round = {}
            self.removal_votes = {}
            self.removal_list = []
            self.totalPaid = {}
            self.robot_to_remove =-1
            self.should_we_remove =False
            self.robots_signals = []
            self.initiate_removal = False
            self.robot_vote_count = []
            self.blockwait = int(environ['BLOCKWAIT'])
            self.alpha = int(environ['ALPHA'])
            self.remove_list = []
            self.add_list = []
            self.remove_start_block = None
            self.remove_file = '/root/ants/HelloWorld/remove_list.json'  # shared state file
            

    def abs(self, x):
        if x < 0:
            return -x
        else:
            return x
    def toRemove(self):
        return self.should_we_remove
    def getRobRemove(self):
        return self.robot_to_remove
    def getRemovalList(self):
        return self.removal_list
    #def getBlockHeight(self):
    #    return self.block.height

    def getBalance(self,id): #return the self.balance for a robot
        try:
            return self.balances[id]
        except: 
            return 0
    def getRobBalance(self,id): #return new balance dict for a robot
        try:
            return self.robot[id]["robBalance"]
        except: 
            return 0
            
    def getInboundToken(self, id): #return total UBI received by a robots
        try:
            return self.self.robot[id]["totalPaid"]
        except:
            return 0
    def receivedUBI(self, id): #return total UBI received by a robots
        try:
            return self.self.robot[id]["totalUBI"]
        except:
            return 0
    def isConverged(self): #check convergence
        return self.consensusReached

    def isNewRound(self):
        return self.newRound

    def getMean(self): #retur mean
        return self.mean

    def getRemovalCountvote(self):
        return self.robot_vote_count
        
    def getVoteCount(self):
        return self.voteCount
        
    def getVoteOkCount(self):
        return self.voteOkCount

    def getRobotCount(self):
        return self.robotCount

    def getTicketPrice(self):
        return self.ticketPrice
        
    def getRegisteredRobots(self): #get al robots registered
        return self.robot
        
    def shouldIremove(self): #check if a robot has payouts
        return self.initiate_removal
        
    def doIhavePayouts(self,id): #check if a robot has payouts
        try:
            if (self.robot[id]["payout"])>0:
                return True
            else:
                return False
        except:
            return False
    def getPayout(self, id): #return the payout to do
        try:
            self.robot[id]["payout"]
        except:
            return 0
    def getTotPayout(self, id): #return all payouts done
        try:
            self.robot[id]["totalPayout"]
        except:
            return 0

    def amIregistered(self, id): #check if a robot has payouts
        try:
            if (id not in self.robot or not self.robot[id]["isRegistered"]):
                return False
            else:
                return True
        except:
            return False
    def getVoterCounter(self, id): #return all payouts done
        try:
            self.robot[id]["myVoteCounter"]
        except:
            return 0
    def get_round_data(self):
        return self.round 

    def registerRobot(self): #register a robot and initilaize all the variables that we need in a dict
        os.environ['REMOVE'] = json.dumps(self.remove_list)
        #print("Registered: ",self.msg.sender)
        self.publicLength = len(self.blocksUBI)
        self.ticketPrice = 40
        if self.msg.sender not in self.robot:
            self.robot[self.msg.sender] = {
                "robotAddress": self.msg.sender,
                "isRegistered": True,
                "payout": 0,
                "totalPayout": 0,
                "lastUBI": 0,
                "totalUBI":0,
                "totalPaid":0,
                "myVoteCounter": 0,
                "robBalance": 0,
            }
            self.robotCount += 1
            
    def shouldIaskforUBI(self): #TODO function that robot checks to see if it transact askforUBI func
        pass
        


    def askForUBI(self): #get UBI payments - implemented based on SciRob
        if self.msg.sender not in self.robot or not self.robot[self.msg.sender]["isRegistered"]:
            print("Askig UBI Error: comes to not registered")
        else:
            myBlocksUBI = [0, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]
            payoutUBI = 0
            myValueUBI = 20
            #print(self.robot)
            
            
            for i in range(len(myBlocksUBI)):
                if self.block.height < myBlocksUBI[i]:
                    payoutUBI = (i - self.robot[self.msg.sender]["lastUBI"]) * myValueUBI
                    self.robot[self.msg.sender]["lastUBI"] = i
                    break

            if payoutUBI > 0:
                #print(payoutUBI)
                self.robot[self.msg.sender]["robBalance"] += payoutUBI
                #self.robot[self.msg.sender]["robBalance"] += payoutUBI
                #self.balances[self.msg.sender] += payoutUBI
                self.robot[self.msg.sender]["totalUBI"] += payoutUBI #add payout made to totalpayouts made
                self.robot[self.msg.sender]["totalPaid"] += payoutUBI #add payout made to totalpayouts made

                #self.totalUBI += payoutUBI
                #print(self.balances[self.msg.sender])
            #return payoutUBI
        

    def askForPayout(self): #get payouts
        os.environ['REMOVE'] = json.dumps(self.remove_list)
        if self.msg.sender not in self.robot or not self.robot[self.msg.sender]["isRegistered"]:
            print("Payout error: Robot not registered")
        else:
            payout = self.robot[self.msg.sender]["payout"]
            print("Paying out the robots", self.msg.sender, payout )
            self.robot[self.msg.sender]["robBalance"] += payout #add payout to robots balance
            self.robot[self.msg.sender]["totalPayout"] += payout #add payout made to totalpayouts made
            self.robot[self.msg.sender]["totalPaid"] += payout #add payout made to totalpayouts made
            #self.balances[self.msg.sender] += payout
            #self.totalPaid[self.msg.sender] += payout
            self.robot[self.msg.sender]["payout"] = 0 #reset payout to 0 until next mean
        #return payout

    def send_vote(self, estimate):  # transaction to this function when sending estimate
        os.environ['REMOVE'] = json.dumps(self.remove_list)
        if self.msg.sender not in self.robot or not self.robot[self.msg.sender]["isRegistered"]:
            ##print("update Mean error: not registered")
            return

        if self.robot[self.msg.sender]["robBalance"] <= 39:
            #print(f"Robot {self.msg.sender} has insufficient balance to vote.")
            return

        # Initialize round if not already present
        if self.roundCount not in self.round:
            self.round[self.roundCount] = []

        # Check if robot already voted in this round
        for entry in self.round[self.roundCount]:
            if entry["robot_address"] == self.msg.sender:
                #print(f"Robot {self.msg.sender} already voted in round {self.roundCount}. Vote ignored.")
                return

        # Save the vote
        self.voteCount += 1
        self.round[self.roundCount].append({
            "robot_address": self.msg.sender,
            "vote": round(estimate, 3)
        })
        ##print("Robot:", self.msg.sender, "vote is:", round(estimate, 3))

        self.robot[self.msg.sender]["robBalance"] -= 40  # deduct tokens

        # If all robots have voted, move to new round
        if len(self.round[self.roundCount]) >= self.robotCount/2 and self.robotCount > 4:
            self.roundCount += 1
            self.newRound = True
    
    def _sync_robot_count(self):
        try:
            removed_list = json.loads(os.environ.get("REMOVED_ROBOTS", "[]"))
        except Exception:
            removed_list = []

        registered = [rid for rid, rinfo in self.robot.items() if rinfo["isRegistered"]]
        active = [rid for rid in registered if rid not in removed_list]
        print("removed_list", removed_list)

        self.robotCount = len(active)
        return self.robotCount
    

    def signal_remove_robot(self, voting_robot_id):
        if not hasattr(self, 'remove_list'):
            self.remove_list = []
        if not hasattr(self, "remove_signals"):
            self.remove_signals = set()
        if not hasattr(self, "last_remove_block"):
            self.last_remove_block = None  # track last removal block

        # Load existing list from file
        try:
            with open(self.remove_file, "r") as f:
                self.remove_list = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.remove_list = []

        current_block_height = self.block.height

        if voting_robot_id not in self.robot or not self.robot[voting_robot_id]["isRegistered"]:
            return

        # --- Skip if within 5 blocks of last removal ---
        if self.last_remove_block is not None and current_block_height < self.last_remove_block + 3:
            print(f"[SC] Skipping removal check, waiting {self.last_remove_block + 5 - current_block_height} more blocks")
            return

        self.remove_signals.add(voting_robot_id)
        print("propo signal", (len(self.remove_signals) / self.robotCount), self.remove_signals)
        if (len(self.remove_signals) / self.robotCount) >= 0.33:
            candidates = sorted([
                int(rid) for rid, rinfo in self.robot.items()
                if rinfo["isRegistered"] and str(rid) not in self.remove_list
            ])
            if len(candidates) > 6:
                victim_id = str(max(candidates))
                if victim_id not in self.remove_list:
                    self.remove_list.append(victim_id)
                    with open(self.remove_file, "w") as f:
                        json.dump(self.remove_list, f)
                    self.robotCount -= 1
                    print(f"[SC] Robot {victim_id} added to REMOVE list", len(candidates), self.remove_list)
                    self.robot[victim_id]["isRegistered"] = False

                    # --- mark block when removal happened ---
                    self.last_remove_block = current_block_height
                else:
                    print(f"[SC] Robot {victim_id} already scheduled for removal, skipping", candidates)

            self.remove_signals.clear()
            self.remove_start_block = None

    def signal_add_robot(self, voting_robot_id):
        # Ensure attributes exist
        if not hasattr(self, 'add_start_block'):
            self.add_start_block = None  # Block height when voting started
        if not hasattr(self, "add_signals"):
            self.add_signals = set()

        current_block_height = self.block.height

        # If this is the first vote in the current round, set the start block height
        if self.add_start_block is None:
            self.add_start_block = current_block_height
            print(f"[SC] Adding round started at block {self.add_start_block}.")
            os.environ['ADD'] = json.dumps(self.add_list)
        # Ensure robot is valid and registered
        if voting_robot_id not in self.robot or not self.robot[voting_robot_id]["isRegistered"]:
            return

        # Add vote
        self.add_signals.add(voting_robot_id)
        print("Add signal in SC is ", self.add_signals, len(self.add_signals) / self.robotCount, self.add_list)
        os.environ['ADD'] = json.dumps(self.add_list)
        # Check threshold
        if (len(self.add_signals) / self.robotCount) >= 0.33:
            new_robot_id = f"new_{random.randint(1000,9999)}"
            print("[SC] Signalling loop controller to add a robot", new_robot_id)
            #os.environ['ADD'] = json.dumps([new_robot_id])
            # --- Make ADD persistent ---
            try:
                self.add_list = json.loads(os.environ.get('ADD', '[]'))
            except Exception:
                self.add_list = []
            self.add_list.append(new_robot_id)
            os.environ['ADD'] = json.dumps(self.add_list)
            print("ADD LIST IN SC: ", self.add_list)
            self.add_signals.clear()
            self.add_start_block = None  # Reset voting round

        # Timeout: clear votes if too many blocks passed
        elif current_block_height >= self.add_start_block +5:  # change 4 to desired limit
            print(f"[SC] Clearing add signals after {current_block_height - self.add_start_block} blocks")
            self.add_signals.clear()
            self.add_start_block = None

            

    def can_add_robot(self):
        return getattr(self, "allow_robot_addition", False)

    def updateMean(self): #update the mean of tiles
        os.environ['REMOVE'] = json.dumps(self.remove_list)
        if self.msg.sender not in self.robot or not self.robot[self.msg.sender]["isRegistered"]:
            print("update Mean error: not registered")
        else:
            #print(f"TRYING TO Update mean.......{self.msg.sender}")
            if self.lastUpdate >= self.roundCount:
                self.newRound = False
            else:
                oldMean = self.mean
                r = self.lastUpdate
                myThreshold = 1000 #0.1
                roundVoteOkCount = 0

                for robot in self.removal_list:
                    for past_round in range(len(self.round)):  # check through all past rounds
                        
                        removed_votes = [entry for entry in self.round[past_round] if entry["robot_address"] == robot] # Get all contributions of the robot frm past rounds
                        for entry in removed_votes:
                            delta = float(entry["vote"] - self.mean)  # Recalculate the delta for the chosen robot
                            w_n = 1  # each vote has a weight of 1
                            
                            # Lets remove the contribution of this vote from W_n and mean
                            if self.W_n > w_n:  # To stop division by zero when updating mean
                                self.W_n -= w_n
                                self.mean -= (w_n * delta) / self.W_n
                            else:
                                self.W_n = 0
                                self.mean = 0  # Reset mean if no valid votes remain

                            #print(f"Removing previous impact of robot {robot}'s vote: {delta}, updated mean: {self.mean}, updated W_n: {self.W_n}")

                        # Remove the robot's data from the round
                        self.round[past_round] = [entry for entry in self.round[past_round] if entry["robot_address"] != robot]

                #check if vote within treshold to be counted
                for i in range(len(self.round[r])):
                    entry = self.round[r][i]
                    robot_id = int(entry["robot_address"])

                    # Check participation condition
                    if robot_id > 380:
                        rounds_participated = set()
                        for round_id in self.round:
                            print("rouund id is : ", round_id)
                            for robot_entry in self.round[round_id]:
                                if int(robot_entry["robot_address"]) == robot_id:
                                    rounds_participated.add(round_id)
                        if len(rounds_participated) < self.alpha:
                            ##print(f"Robot {robot_id} not eligible to vote  only participated in {len(rounds_participated)} rounds.")
                            continue  # Skip this robot's vote

                    # Robot is eligible  process the vote
                    ##print("Round data:", entry)
                    delta = float(entry["vote"] - self.mean)
                    self.voteOkCount += 1
                    roundVoteOkCount += 1
                    w_n = 1  # Weight of current vote
                    self.W_n += w_n
                    self.mean += (w_n * delta) / self.W_n
                    self.robotsToPay.append(entry["robot_address"])
                """
                for i in range(len(self.round[r])):
                    delta = float(self.round[r][i]["vote"] - self.mean)
                    #print(self.abs(delta))
                    #if r == 0 or float(self.abs(delta)) < float(myThreshold):
                    self.voteOkCount += 1
                    roundVoteOkCount += 1
                    w_n = 1 #W_n global counter of all votes ever been sent, substract W_n-number of votes sent by removed robot
                    self.W_n += w_n
                    #print(f"Comes to threshhold  for robot and updating mean ....{self.msg.sender} and votes are: {delta} and {self.mean} and self wn {self.W_n}.")
                    self.mean += (w_n * delta) / self.W_n
                    #print(f"Comes to threshhold  for robot and updating mean ....{self.msg.sender} and votes are: {delta} and {self.mean} and self wn  {self.W_n}.")
                    self.robotsToPay.append(self.round[r][i]["robot_address"])
                #if none of the votes were ok, then consider all votes
                """
                """
                if roundVoteOkCount == 0:
                    print(f"No votes were ok....{self.msg.sender}.")
                    for i in range(len(self.round[r])):
                        delta = float(self.round[r][i]["vote"] - self.mean)
                        self.voteOkCount += 1
                        roundVoteOkCount += 1
                        w_n = 1
                        self.W_n += w_n
                        self.mean += (w_n * delta) / self.W_n
                        self.robotsToPay.append(self.round[r][i]["robot_address"])
                """
                # calculate the payouts to be given to robots whose votes were within threshold
                for b in range(len(self.robotsToPay)):
                     self.robot[self.robotsToPay[b]]["payout"] += 1 * self.ticketPrice #* len(self.round[r]) / len(self.robotsToPay)
                    
                #TODO SHOULD WE EXPLICITLY SEND 40 TOKENS TO BE GIVEN BAKC THAT WERE ESCROWED FOR TRANSACTIONS

                #check for convergence
                myTau =10 #is this correct? the paper says 0.2%
                if self.abs(oldMean - self.mean) < myTau and self.voteOkCount > 2 * self.robotCount:
                    self.consensusReached = True

                #reset variables
                self.lastUpdate += 1
                self.newRound = False
                #print(self.robotsToPay)
                self.robotsToPay = []
