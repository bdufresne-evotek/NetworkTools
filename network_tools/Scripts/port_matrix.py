# Author - Bryan Dufresne
# Description:
"""Uses inventory to assemble port-matrix csv file."""

from datetime import date
import getpass
import json
from netmiko import ConnectHandler
import os

def send_show(target_device, command):
    result = ''
    try:
        with ConnectHandler(**target_device) as net_connect:
            result = net_connect.send_command(command, use_textfsm=True, read_timeout=120)
    except Exception as e:
        print(f"Failed to collect results for:\nCommand: {command}\nDevice: {target_device['ip']}\nType: {target_device['device_type']}\nError: {str(e)}")
    return result

def main():

    print("#####\nPort Matrixer\n#####\n")

    today = date.isoformat(date.today())

    # Create the "Output" directory if it doesn't exist
    output_dir = 'Output'
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
    enpass = getpass.getpass(prompt="Enter enable password: ")

    # Connect to devices and execute the show commands
    for device in devices:
        device_type = device['device_type']
        device_ip = device['device_IP']
        device_name = device['name']
        device_location = device['location']
        filename = device_name + " - port-matrix - " + preorpost + "-" + today + ".txt"
    
        device_info = {
            'device_type': device_type,
            'ip': device_ip,
            'username': username,
            'password': password,
            'secret': enpass,
        }

        interfaces = send_show(device_info, 'show interface')
        mac_info = send_show(device_info, 'show mac address-table')
        cdp = send_show(device_info, 'show cdp neighbor detail')
        lldp = send_show(device_info, 'show lldp neighbor')
        lldp_det = send_show(device_info, 'show lldp neighbor detail')

        if isinstance(lldp, list):  # Check if lldp is a list
            for nei in lldp:
                nei['ip'] = ''
                nei['type'] = ''
                if 'Gi' in nei['local_interface']:
                    _, int_num = nei['local_interface'].split('Gi')
                    nei['local_interface'] = 'GigabitEthernet' + int_num
                elif 'Fa' in nei['local_interface']:
                    _, int_num = nei['local_interface'].split('Fa')
                    nei['local_interface'] = 'FastEthernet' + int_num
                for nei_det in lldp_det:
                    if nei['neighbor'] == nei_det['neighbor']:
                        nei['ip'] = nei_det['management_ip']
                        nei['type'] = nei_det['system_description']

        for interface in interfaces:
            int_name = interface['interface']
            interface['intf'] = ''
            if 'TenGig' in int_name:
                _,int_num = int_name.split('TenGigabitEthernet')
                interface['intf'] = 'Te' + int_num
            elif 'Gigabit' in int_name:
                _,int_num = int_name.split('GigabitEthernet')
                interface['intf'] = 'Gi' + int_num
            elif 'FastEth' in int_name:
                _,int_num = int_name.split('FastEthernet')
                interface['intf'] = 'Fa' + int_num
            elif 'Port-c' in int_name:
                _,int_num = int_name.split('Port-channel')
                interface['intf'] = 'Po' + int_num

            interface['status'] = interface['link_status']
            if interface['link_status'] == 'administratively down':
                interface['status'] = 'admin down'
            elif interface['link_status'] == 'up' and 'down' in interface['protocol_status']:
                interface['status'] = 'up/down'

            interface['macs'] = []
            interface['neighbor'] = ''
            interface['nei_ip'] = ''
            interface['nei_type'] = ''
            interface['nei_port'] = ''

            if type(lldp) == 'list':
                for nei in lldp:
                    if nei['local_interface'] == interface['interface']:
                        interface['neighbor'] = nei['neighbor']
                        interface['nei_ip'] = nei['ip']
                        interface['nei_type'] = nei['type']
                        interface['nei_port'] = nei['neighbor_interface']


            for nei in cdp:
                if nei['local_port'] == interface['interface']:
                    interface['neighbor'] = nei['destination_host']
                    interface['nei_ip'] = nei['management_ip']
                    interface['nei_type'] = nei['platform']
                    interface['nei_port'] = nei['remote_port']

        mac_ints = {}

        for mac in mac_info:
            for interface in mac['destination_port']:
                if interface not in mac_ints:
                    mac_ints[interface] = []
                mac_ints[interface].append(mac['destination_address'])

        etherc = send_show(device_info, 'show etherchannel summary')

        for interface in interfaces:
            macs = ''
            int_name = interface['intf']
            if int_name in mac_ints:
                if len(mac_ints[int_name]) > 1:
                    macs = ', '.join(mac_ints[int_name])
                else:
                    macs = mac_ints[int_name][0]
            interface['macs'] = macs

            if 'Po' in int_name:
                for pc in etherc:
                    if pc['po_name'] == int_name:
                        interface['interface'] = interface['interface'] + " (" + ','.join(pc['interfaces']) + ")"


        try:
            # Establish the SSH/Telnet connection and enter enable mode
            connection = ConnectHandler(**device_info)

            outfile = os.path.join(output_dir, filename)
            file = open(outfile, "w")
            print(f"\n########\nCollecting info for: {device_name}")
            file.write(device_name.upper())
            file.write("\n")
            file.write(device_location)
            file.write("\n\n")

            int_count = len(interfaces)
            current_int = 0

            for interface in interfaces:
                current_int += 1
                sho_run = send_show(device_info, 'show run interface ' + interface['intf'])
                mode = ''
                avlan = ''
                tvlan = ''
                vvlan = ''
                lines = sho_run.split('\n')

                # Display results on the same line as they come in
                print(f"\rParsing interface: ({current_int}/{int_count})", end='')
                for line in lines:
                    if 'switchport mode access' in line:
                        mode = 'access'
                    if 'switchport access vlan' in line:
                        _,avlan = line.split('switchport access vlan ')
                    if 'switchport mode trunk' in line:
                        mode = 'trunk'
                    if 'voice vlan' in line:
                        _,vvlan = line.split('voice vlan ')
                    if 'switchport trunk allowed' in line:
                        if 'add' in line:
                            _,vlans = line.split('add ')
                            tvlan = tvlan + ',' + vlans
                        else:
                            _,tvlan = line.split('allowed vlan ')


                file.write(f"{interface['interface']};{interface['media_type']};{interface['description']};{interface['status']};{interface['macs']};{mode};{avlan};{vvlan};{tvlan};{interface['neighbor']};{interface['nei_ip']};{interface['nei_type']};{interface['nei_port']}\n")
            connection.disconnect()
            file.close()

        except Exception as e:
            print(f"Failed to connect to {device_ip} ({device_type}): {str(e)}")