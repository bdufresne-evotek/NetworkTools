# Author - Bryan Dufresne
# Description:
"""Runs show commands against a specified inventory file."""

import os
from datetime import date
import json
import getpass
from netmiko import ConnectHandler

# Function to provide different show command libraries for different device types. 
# device_type is defined in the inventory file selected and passed from there.
def vendor_commands(device_type):
    if device_type == "cisco_ios":
        show = [
            'show ver',
            'show module',
            'show switch',
            'show hw-inventory',
            'show vlan',
            'show etherchannel summary',
            'show int trunk',
            'show spanning-tree sum',
            'show cdp neigh',
            'show lldp neigh',
            'show int statu',
            'show ip int brief | exc unas',
            'show mac add',
            'show ip route',
            'show ip mroute',
            'show ip igmp groups',
            'show run'
        ]
        return show
    
    if device_type == "arista_eos":
        show = [
            'show ver',
            'show module',
            'show switch',
            'show hw-inventory',
            'show vlan',
            'show etherchannel summary',
            'show int trunk',
            'show spanning-tree sum',
            'show cdp neigh',
            'show lldp neigh',
            'show int statu',
            'show ip int brief | exc unas',
            'show mac add',
            'show ip route',
            'show ip mroute',
            'show ip igmp groups',
            'show run'
        ]
        return show
    
    if device_type == "aruba_os":
        show = [
            'show version',
            'show system',
            'show stacking',
            'show interfaces transceiver detail',
            'show lacp',
            'show int trunk',
            'show trunks',
            'show vlan',
            'show spanning-tree',
            'show arp',
            'show ip route',
            'show ip int brief',
            'show ip',
            'show interfaces',
            'show mac-address',
            'show lldp info remote-device det',
            'show lldp info remote-device',
            'show run'
        ]
        return show
    
    if device_type == "hp_procurve":
        show = [
            'show version',
            'show system',
            'show services',
            'show modules',
            'show lacp',
            'show trunks',
            'show lldp info remote-device',
            'show cdp neigh',
            'show cdp neigh detail',
            'show vlan',
            'show interface brief',
            'show spanning-tree',
            'show arp',
            'show ip route',
            'show ip',
            'show ip igmp',
            'show interfaces brief',
            'show mac-address',
            'show running-config'
        ]
        return show
        
    if device_type == "hp_comware":
        show = [
            'display version',
            'display lldp neighbor-information',
            'display link-aggregation summary',
            'display interface',
            'display interface brief',
            'display vlan all',
            'display mac-address',
            'display stp brief',
            'display stp',
            'display current-configuration'
        ]
        return show
    
    if device_type == "paloalto_panos":
        show = [
            'set cli config-output-format set',
            'configure',
            'show'
        ]

    else:
        return "No commands available for {device_type}"


def main():

    print("#####\nShow Runner\n#####\n")

    today = date.isoformat(date.today())

    # Prompt for customer/project name for Output folder
    customer = input('Enter name of customer: ')
    project = input('Enter name of project: ')

    # Create the "Output" directory, if it doesn't exist
    output = 'Output'
    if not os.path.exists(output):
        os.makedirs(output)

    # Create the directory with the Customer's name, if it doesn't exist
    customer_dir = os.path.join(output, customer)
    if not os.path.exists(customer_dir):
        os.makedirs(customer_dir)
    
    # Create the directory with the Project name under the Customer's folder, if it doesn't exist
    output_dir = os.path.join(output, customer, project)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # List available JSON inventory files in the 'Inventories' directory
    inventory_files = [f for f in os.listdir('Inventories') if f.endswith('.json')]
    if not inventory_files:
        print("No inventory files found in the 'Inventories' directory.")
        exit()

    print("Available inventory files:")
    for idx, filename in enumerate(inventory_files, start=1):
        print(f"{idx}. {filename}")

    # Prompt for the user's choice of inventory file
    try:
        selection = int(input("Select an inventory file (enter the corresponding number): ")) - 1
        if selection < 0 or selection >= len(inventory_files):
            print("Invalid selection.")
            exit()
    except ValueError:
        print("Invalid input.")
        exit()

    selected_inventory = inventory_files[selection]
    inventory_path = os.path.join('Inventories', selected_inventory)

    # Load device information from the selected inventory JSON file
    with open(inventory_path, 'r') as json_file:
        devices = json.load(json_file)

    # Prompt for the user's username and password
    preorpost = input("Discovery, Pre-change, or post-change? [type disc, pre, or post]: ")
    username = input("Enter your username: ")
    password = getpass.getpass(prompt="Enter your password: ")

    # List of show commands to be sent to devices
    # If statement pivots from the device_type specified in the inventory
    # cisco_ios = []
    # 
    # show_commands = [
    #     'show ver',
    #     'show vlan',
    #     'show etherchannel summary',
    #     'show int trunk',
    #     'show spanning-tree sum',
    #     'show cdp neigh',
    #     'show lldp neigh',
    #     'show int statu',
    #     'show ip int brief | exc unas',
    #     'show mac add',
    #     'show ip route',
    #     'show ip mroute',
    #     'show ip igmp groups',
    #     'show run'
    #     # Add more commands as needed
    # ]

    # Connect to devices and execute the show commands
    for device in devices:
        device_type = device['device_type']
        device_ip = device['device_IP']
        device_name = device['name']
        show_commands = vendor_commands(device_type)
    
        device_info = {
            'device_type': device_type,
            'ip': device_ip,
            'username': username,
            'password': password,
        }
    
        try:
            connection = ConnectHandler(**device_info)
            prompt = connection.find_prompt().strip('#<>[]')
            filename = prompt + " - " + device_ip + " - " + preorpost + " - " + today + ".txt"
            outfile = os.path.join(output_dir, filename)
            file = open(outfile, "w")
            file.write(f"{device_name.upper()} - {device_type} - {device_ip}")
            file.write("\n\n")
            # Add code here to add results to status JSON file that tracks status of each switch and/or errors
            print(f"Device {device_name} ({device_type}) - Command outputs:")
            for show_command in show_commands:
                file.write(show_command)
                file.write("\n")
                output = connection.send_command(show_command)
                #if output has some type of error message:
                    #return some error message about syntax
                file.write(output)
                file.write("\n\n")
                print(f"--- {show_command} ---")
            connection.disconnect()
            file.close()
        except Exception as e:
            print(f"Failed to connect to {device_ip} ({device_type})\nError:\n{str(e)}")
            # Add code here to add results of exceptions to track status.
