# Mitigating Latency and Partitioning through Size Regulation in Blockchain-Enabled Robot Swarms

This repository contains the code for the paper "Mitigating Latency and Partitioning through Size Regulation in Blockchain-Enabled Robot Swarms". Submitted to ANTS 2026 -- Fifteenth International Conference on Swarm Intelligence.

# Installations

We assume a previously clean installation of Ubuntu20.04 or Ubuntu22.04.

The ARGoS simulator version 59 can be installed from instructions:  https://github.com/ilpincy/argos3.

Download and compile E-puck plugin (More information at https://github.com/demiurge-project/argos3-epuck). 
The argos-python wrapper was made by Ken Hasslemen: https://github.com/KenN7/argos-python. We have adapted it for our openswarm setup in [argos-python](https://github.com/rainazakir/size_regulation/tree/main/argos-python) folder. 

The toychain implementation of our collective sensing scenario specified in the paper is based on: https://github.com/teksander/toychain-argos.

# Configurations and Running experiments

Edit [```experimentconfig.sh```](https://github.com/rainazakir/size_regulation/blob/main/HelloWorld/experimentconfig.sh) file to match your paths
To run an experiment:
```
cd HelloWorld/
./starter -s
```
