# [PATHS]
export HOMEFOLDER="$HOME/"
export MAINFOLDER="$HOMEFOLDER/ants"
export DOCKERFOLDER="$MAINFOLDER/argos-blockchain-sm"
export ARGOSFOLDER="$MAINFOLDER/argos-python"
export EXPERIMENTFOLDER="$MAINFOLDER/HelloWorld"
export BLOCKCHAINPATH="$HOMEFOLDER/eth_data_para/data"
# [[ ":$PATH:" != *":$MAINFOLDER/scripts:"* ]] && export PATH=$PATH:$MAINFOLDER/scripts

# [FILES]
export ARGOSNAME="market-foraging"
export GENESISNAME="genesis_poa"
export CONTRACTNAME="MarketForaging"
export SCNAME="hello_neighbor"

export GENESISFILE="${DOCKERFOLDER}/geth/files/$GENESISNAME.json"
export CONTRACTADDRESS="${EXPERIMENTFOLDER}/scs/contractAddress.txt"
export CONTRACTABI="${EXPERIMENTFOLDER}/scs/build/$CONTRACTNAME.abi"
export CONTRACTBIN="${EXPERIMENTFOLDER}/scs/build/$CONTRACTNAME.bin-runtime"
export SCFILE="${EXPERIMENTFOLDER}/scs/${SCNAME}.sol" 
export SCTEMPLATE="${EXPERIMENTFOLDER}/scs/${SCNAME}.x.sol" 
export ARGOSFILE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argos"
export ARGOSTEMPLATE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.x.argos"

# [DOCKER]
export SWARMNAME=ethereum
export CONTAINERBASE=${SWARMNAME}_eth

# [ARGOS]
export CON1="${EXPERIMENTFOLDER}/controllers/main.py"


export RABRANGE="0.13" #0.26, 0.13
export RABRANGE2="0.65"
export WHEELNOISE="0"
export TPS=1
export DENSITY="1"

#export ARENADIM="4.05"
#export ARENADIMH="2.03"
#export STARTDIM="1.18"

#export REDUCEDL="3.9"
#export MOVEWALL="0.06"
#export MOVESOUTH="-1.88"

#export ARENADIM="2.15"
#export ARENADIMH="1.04"
#export STARTDIM="0.65"

#export REDUCEDL="1.83"
#export MOVEWALL="0.12"
#export MOVESOUTH="-0.767"


export ARENADIM="2.05"
export ARENADIMH="1.001"
export STARTDIM="0.92"

export REDUCEDL="1.92"
export MOVEWALL="0.08"
export MOVESOUTH="-0.89"



export REALTIME=false
export LOGNAME="VID 2S_poa15_10runs_6rob_nohelp_comm0.13_30S_4_1strk__COMMR0.13__list_proposal_checkts250_1R1V_blockwait3_grace_20_28_2_28_run10"
# [GETH

export NUMROBOTS=6
export NUMROBOTS_HELPERS=0

export NUMBYZANTINE=0 #num of byzantines in starting swarm
export BYZANTINESWARMSTYLE=1
#export INTERVALBYZADD=1300000
#export BYZTOADD=22

export REMOVETIMER=70000000 #interval to start checking for robot to remove, to check if you find a byz to remove
export NEWROUNDTIMER=15
export VOTINGTIMER=3
export MEANTYPE="0"   # "0" for normal or "0.09" for smart byzantine
export BLOCKWAIT=5 #block wait for getting votes in Block.py
export ALPHA=1
export whichfuntion="adaptive"   # can be simple as well by stating "threshold" or "adaptive"

export collusiontolerance=0.007 #parameter to tolerate collusion of robots, applicabel for adaptive
export k=2 #std tolerance,applicabel for adaptive
export thresholdcheck=0.07 #only for simple thresholding to remove robots

export GRACEMIN=2
export GRACEMAX=28

# [SC] these are not valid for our experiment- will clean later

export BLOCKPERIOD=3 #irrelevant just keep it dont remove

export MAXWORKERS=15
export LIMITASSIGN=2

export DEMAND_A=0
export DEMAND_B=800
export REGENRATE=20
export FUELCOST=100
export QUOTA_temp=$(echo " scale=4 ; (75/$REGENRATE*$BLOCKPERIOD+0.05)/1" | bc)
export QUOTA=$(echo "$QUOTA_temp*10/1" | bc)
export QUOTA=200
export EPSILON=15
export WINSIZE=5

# [OTHER]		
export SEED=3478

export TIMELIMIT=100
export LENGTH=4000
export SLEEPTIME=5
export REPS=10
export NOTES="Variation of grace period 20 and 28"
