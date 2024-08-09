Welcome to ANDREW!

#####           #####

    Automated
    Network
    Discovery,
    Reconaissaince, &
    Enumeration
    Workbench
    
#####           #####

Current modules:
inventory_manager.py
l2dp_crawler.py
port_matrix.py
show_commander.py
subnet_sweeper.py

#####
First time Use
#####

1. Download network_tools package
2. Create venv and import requirements.txt
3. Activate venv and run the main.py through python.


#####
Virtual Envionrment (venv)

On Windows:
Create virtual environment by loading a terminal and running:
python -m venv C:\path\to\venv

#####
Load virtual environment:
Open PowerShell and navigate to venv folder
cd C:\path\to\venv
.\Scripts\Activate.ps1

#####
Install pip requirements
While in virtual environment, upgrade pip by running:
python -m pip install --upgrade pip

Then install the requirements by changing to the network_tools repo and running:
pip install -r requirements.txt

Once venv is active, run pip install requirements.txt


If you're using this file to generate an inventory for netmiko, make sure to reference the netmiko supported platform information: https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md

If your device_type is not cisco_ios, check the link and find the correct type. Name and Location are custom properties and not required fields. If no name is specified the name of the file will be generated from the device hostname or IP address.







#####
Problem:
WARNING: No libpcap provider available ! pcap won't be used

Solution:
Subnet_recon.py requires winpcap (Windows) or libpcap (Linux) to work properly. On Windows, just install WireShark