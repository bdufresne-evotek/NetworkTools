# Author - Bryan Dufresne
# Description:
"""Sweeps IP addresses and/or VLSM networks to discover Cisco hardware inventory & open ports."""

from datetime import datetime
from netmiko import ConnectHandler
import getpass
import ipaddress
import os
import pandas as pd
import ping3
import socket

def cisco_get_info(ip, username, password, method):
    if method == "ssh":
        conn_info = {
            'device_type': 'cisco_ios',
            'ip': ip,
            'username': username,
            'password': password,
        }
    elif method == "telnet":
        conn_info = {
            'device_type': 'cisco_ios_telnet',
            'ip': ip,
            'username': username,
            'password': password,
        }
    else:
        if method is None:
            print("Error: method cannot be blank.")
        else:
            print(f"Error: {method} is not a valid method.")
    
    try:
        connection = ConnectHandler(**conn_info)
        hostname = connection.find_prompt().strip('#<>[]')
        ver_text = connection.send_command('show version', use_textfsm=True)
        connection.disconnect()

    except Exception as e:
        print(f"Unable to connect to {ip}: {e}")
        return []

    if isinstance(ver_text, list):
        device_info_list = []
        for entry in ver_text:
            models = entry.get('hardware', ['Unknown']) # Ensure this is a list
            serial_numbers = entry.get('serial', ['Unknown']) # Ensure this is a list
            sw_image = entry.get('software_image', 'Unknown')  # Ensure this is a string
            os_version = entry.get('version', 'Unknown')  # Ensure this is a string
            
            for serial, model in zip(serial_numbers, models):
                device_info = {
                    "Hostname": hostname,
                    "IP": ip,
                    "Type": "",
                    "Make": "Cisco",
                    "Model": model,
                    "Serial": serial,
                    "SW Image": sw_image,
                    "OS Version": os_version,
                    "Location": "",
                    "Wiped": ""
                }
                device_info_list.append(device_info)

        return device_info_list

    return []

def cisco_get_show_commands(ip, username, password, method, location):
    commands = [
        'show ver',
        'show module',
        'show switch',
        'show switch virtual redundancy',
        'show hw-inventory',
        'show inventory',
        'show env all',
        'show vtp status',
        'show vtp password',
        'show vlan summary',
        'show vlan',
        'show etherchannel summary',
        'show interface trunk',
        'show spanning-tree summary',
        'show cdp neighbor',
        'show cdp neighbor detail',
        'show lldp neighbor',
        'show lldp neighbor detail',
        'show interface status',
        'show interface description',
        'show power inline',
        'show inteface switchport',
        'show ip interface brief | exclude unassigned',
        'show mac address-table',
        'show ip route',
        'show ip mroute',
        'show ip igmp groups',
        'show run'
    ]
    if method == "ssh":
        conn_info = {
            'device_type': 'cisco_ios',
            'ip': ip,
            'username': username,
            'password': password,
        }
    elif method == "telnet":
        conn_info = {
            'device_type': 'cisco_ios_telnet',
            'ip': ip,
            'username': username,
            'password': password,
        }
    else:
        if method is None:
            print("Error: method cannot be blank.")
        else:
            print(f"Error: {method} is not a valid method.")
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        connection = ConnectHandler(**conn_info)
        connection.enable()
        prompt = connection.find_prompt().strip("#<>[]")
        filename = f"{prompt} - {ip} - {today}.txt"
        outdir = os.path.join("Output", location, "Configs")
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        outfile = os.path.join(outdir, filename)
        file = open(outfile, "w")
        file.write(f"{prompt.upper()} ({ip})\n\n")
        print(f"Gathering show commands from {prompt} at {ip}")

        for command in commands:
            file.write(f"{command}\n")
            output = connection.send_command(command, read_timeout=30.0)
            file.write(f"{output}\n\n")

        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False

def generate_inventory(networks, username, password, location):
    usage = """
    generate_inventory(networks, username, password, location)

    Purpose:
    Gather info from single IP or VLSM network. Checks IPs for icmp, telnet, ssh, http, and https and attempts to login (assuming the devices is Cisco) to gather hardware information.

    Parameters:
    networks (str) - IP address or VLSM network or both (e.g., '10.10.0.1' or '10.10.0.0/24' or '10.10.1.1,10.10.0.0/24')
    username (str) - Username to attempt login
    password (str, input hidden) - Password to attempt login
    location (str) - Customer, site, building, room, or other descriptive value - also used in filename

    Example usage: 
    generate_inventory(10.10.0.0/24, myuser, MyS3cr3tP@ss, Corp-Dallas)
    """
    if not networks:
        print(f"Error: networks must be specified.\nUsage: {usage}")
        networks = input("Example: '10.10.0.1' or '10.10.0.0/24' or '10.10.1.1,10.10.0.0/24'\nEnter IP address or VLSM network to generate inventory from: ")

    if not username:
        print(f"Error: username must be specified.\nUsage: {usage}")
        username = input(f"Enter username to try for {networks}: ")

    if not password:
        print(f"Error: password must be specified.\nUsage: {usage}")
        password = getpass.getpass(prompt=f"Enter password to try for {username}: ")

    if not location:
        print(f"Error: location must be specified.\nUsage: {usage}")
        location = input(f"Enter a location name for {networks}\nNote: Location used in filename\nLocation: ")
    
    # Define the hardware & service column headers
    hw_columns = ["Hostname", "IP", "Type", "Make", "Model", "Serial", "SW Image", "OS Version", "Location", "ConfigBackup"]
    service_columns = ["IP", "ICMP", "SSH", "Telnet", "HTTPS", "HTTP"]
    int_columns = ["Hostname", "Group", "Type", "Connected", "Available", "Total"]
    
    # Initialize an empty list to hold the data
    hw_data = []
    service_data = []
    int_data = []

    # Split comma-delimited IPs or handle single subnet
    targets = [t.strip() for t in networks.split(',')]

    # Initialize an empty list to hold all IP addresses
    all_ips = []

    for target in targets:
        try:
            # Handle variable-length subnet mask input
            if '/' in target:
                network = ipaddress.ip_network(target, strict=False)
            else:
                # Single IP address case
                network = ipaddress.ip_network(f"{target}/32", strict=False)
            
            # Append all IP addresses from current network to all_ips list
            all_ips.extend([str(ip) for ip in network.hosts()])

        except ValueError as ve:
            print(f"Error: {ve}")

    total_ips = len(all_ips)
    failures = 0

    for index, ip in enumerate(all_ips, start=1):
        str_ip = str(ip)
        try:
            # Print the progress message
            successes = index - failures
            progress_message = f"Working on {str_ip} - Processed {index} of {total_ips} addresses. - Successes: {successes} - Failures: {failures}"
            print(progress_message)

            icmp_status = try_ping(str_ip)
            telnet_status = try_telnet(str_ip)
            ssh_status = try_ssh(str_ip)
            http_status = try_http(str_ip)
            https_status = try_https(str_ip)
            # snmp_status = try_snmp(str_ip) # Unsure how I want to handle auth at this time

            # Collect service status data
            service_data.append({
                "IP": str_ip,
                "ICMP": icmp_status,
                "SSH": ssh_status,
                "Telnet": telnet_status,
                "HTTPS": https_status,
                "HTTP": http_status
            })

            if ssh_status is True:
                device_info_list = cisco_get_info(str_ip, username, password, "ssh")
                hostname, device_interface_list = cisco_parse_interfaces(str_ip, username, password, "ssh")
                config_downloaded = cisco_get_show_commands(str_ip, username, password, "ssh", location)
            elif telnet_status is True and ssh_status is not None:
                device_info_list = cisco_get_info(str_ip, username, password, "telnet")
                hostname, device_interface_list = cisco_parse_interfaces(str_ip, username, password, "telnet")
                config_downloaded = cisco_get_show_commands(str_ip, username, password, "telnet", location)
            else:
                failures += 1
                continue

            if hostname and device_interface_list:
                int_list = device_interface_list['interface_summary']

            for device_info in device_info_list:
                device_info["Location"] = location  # Set the location if provided
                device_info["ConfigBackup"] = config_downloaded
                hw_data.append(device_info)

            for device_interface in int_list:
                int_data.append({
                    'Hostname': hostname,
                    'Type': device_interface['interface_type'],
                    'Total': device_interface['total'],
                    'Group': device_interface['group'],
                    'Connected': device_interface['connected'],
                    'Available': device_interface['available']
                })

        except Exception as e:
            print(f"\nUnable to get hardware info for {str_ip}\n\n{str(e)}")
            failures += 1
    
    # Create the dataframes with the collected data
    hw_df = pd.DataFrame(hw_data, columns=hw_columns)
    service_df = pd.DataFrame(service_data, columns=service_columns)
    int_df = pd.DataFrame(int_data, columns=int_columns)
    
    # Set output dir to: \Output\{location} and create it, if it doesn't exist
    output_dir = os.path.join("Output", location)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the dataframes to an Excel file on separate sheets
    current_datetime = datetime.now().strftime('%Y-%m-%d')
    filename = f"{location}_inventory - {networks.replace('/', '_')} - {current_datetime}.xlsx"
    outfile = os.path.join(output_dir, filename)
    with pd.ExcelWriter(outfile, engine='xlsxwriter') as writer:
        hw_df.to_excel(writer, sheet_name='Device Inventory', index=False)
        service_df.to_excel(writer, sheet_name='Control Plane Srvcs', index=False)
        int_df.to_excel(writer, sheet_name='Interface Inventory', index=False)

    print(f"{location} inventory generated for {networks} at {current_datetime}.\nOutput saved to: {outfile}")

def cisco_get_interfaces(ip, username, password, method):
    if method == "ssh":
        conn_info = {
            'device_type': 'cisco_ios',
            'ip': ip,
            'username': username,
            'password': password,
        }
    elif method == "telnet":
        conn_info = {
            'device_type': 'cisco_ios_telnet',
            'ip': ip,
            'username': username,
            'password': password,
        }
    else:
        if method is None:
            print("Error: method cannot be blank.")
        else:
            print(f"Error: {method} is not a valid method.")
        return None
    
    try:
        connection = ConnectHandler(**conn_info)
        hostname = connection.find_prompt().strip('#<>[]')
        interfaces = connection.send_command('show interface status', use_textfsm=True)
        connection.disconnect()
        return {'hostname': hostname, 'interfaces': interfaces}
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def cisco_parse_interfaces(ip, username, password, method):
    interface_data = cisco_get_interfaces(ip, username, password, method)
    if not interface_data:
        print("Failed to retrieve interface data. Check your connection details.")
        return None

    hostname = interface_data['hostname']
    interfaces = interface_data['interfaces']

    interface_groups = {
        'FastEthernet': {},
        'GigabitEthernet': {},
        'TenGigabitEthernet': {}
    }

    for interface in interfaces:
        interface_type = interface.get('type', '')
        if not interface_type or interface_type.startswith("Po"):
            continue

        port_name = interface['port']
        if port_name.startswith("Fa"):
            key = 'FastEthernet'
        elif port_name.startswith("Gi"):
            key = 'GigabitEthernet'
        elif port_name.startswith("Te"):
            key = 'TenGigabitEthernet'
        else:
            continue

        if interface_type in interface_groups[key]:
            interface_groups[key][interface_type]['total'] += 1
            if interface['status'].lower() == 'connected':
                interface_groups[key][interface_type]['connected'] += 1
        else:
            interface_groups[key][interface_type] = {
                'total': 1,
                'connected': 1 if interface['status'].lower() == 'connected' else 0
            }

    results = {
        'interface_summary': []
    }
    for group, types in interface_groups.items():
        for interface_type, counts in types.items():
            total_count = counts['total']
            connected_count = counts['connected']
            available_count = total_count - connected_count
            results['interface_summary'].append({
                'group': group,
                'interface_type': interface_type,
                'connected': connected_count,
                'available': available_count,
                'total': total_count
            })

    return hostname, results

def try_ping(ip):
    result = ping3.ping(ip)
    if result is None:
        return False
    else:
        return True

def try_telnet(ip, port=23):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # Adjust timeout as needed
            s.connect((ip, port))
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False

def try_ssh(ip, port=22):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # Adjust timeout as needed
            s.connect((ip, port))
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False

def try_http(ip, port=80):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # Adjust timeout as needed
            s.connect((ip, port))
            s.sendall(b"GET / HTTP/1.1\r\n\r\n")
            data = s.recv(1024)
            if data:
                return True
            else:
                return False
    except (socket.timeout, ConnectionRefusedError):
        return False

def try_https(ip, port=443):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # Adjust timeout as needed
            s.connect((ip, port))
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False

# def try_snmp(ip, port=161):
#     try:
#         with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
#             s.settimeout(1)  # Adjust timeout as needed
#             s.sendto(b'public', (ip, port))
#             data, addr = s.recvfrom(1024)
#             if data:
#                 return True
#             else:
#                 return False
#     except (socket.timeout, ConnectionRefusedError):
#         return False

def main():
    networks = input("Example: '10.10.0.1' or '10.10.0.0/24' or '10.10.1.1,10.10.0.0/24'\nEnter IP address or VSLM network to generate inventory from: ")
    username = input(f"Enter username to try for {networks}: ")
    password = getpass.getpass(prompt=f"Enter password to try for {username}: ")
    location = input(f"Enter a location name for {networks}\nNote: Location used in filename\nLocation: ")

    print("Hang onto your butts....")

    generate_inventory(networks, username, password, location)

if __name__ == "__main__":
    main()
