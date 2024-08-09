# Author - Bryan Dufresne
# Description:
"""Logs into SilverPeak devices to collect device inventory from 'show arp' & other processing."""
# This script requires nmap (Zenmap in Windows) to be installed and included in the System PATH variable.
# Assembles results and exports to an Excel with pandas package for python.

from netmiko import ConnectHandler
import os
from datetime import date
from socket import gethostbyaddr
from mac_vendor_lookup import MacLookup, BaseMacLookup
from update_oui_vendors import update_oui
import pandas as pd
import nmap
import getpass
import logging

# Function to perform hostname lookup
def lookup_hostname(ip_address):
    try:
        hostname = gethostbyaddr(ip_address)
        if hostname:
            return hostname[0]
        else:
            return ip_address
    except Exception as e:
        logging.error(f"Hostname lookup failed for {ip_address}: {str(e)}")
        return "Unknown"

# Function to gather device type information based on MAC OUI
def lookup_mac_oui(mac_address):
    BaseMacLookup.cache_path = "./mac-vendors.txt"
    update_oui
    try:
        results = MacLookup().lookup(mac_address)
        if results:
            return results  # Return the vendor information as a string
        else:
            return "Unknown"
    except Exception as e:
        return "No Result"


# Function to run nmap discovery to determine device type
def nmap_discovery(target_ip):
    try:
        nm = nmap.PortScanner()
        port_range = "22,135,445,515,1720,5060,5061,9100"
        
        # Perform an Nmap scan for open ports detection
        nm.scan(hosts=target_ip, arguments=f'-p {port_range}')

        if target_ip in nm.all_hosts():
            host = nm[target_ip]

            # Collect the open ports from the scan into the variable open_ports
            open_ports = []

            for port, port_info in host['tcp'].items():
                if port_info['state'] == 'open':
                    open_ports.append(int(port))

            # Check for the presence of specific ports
            is_windows = any(port in open_ports for port in [135, 445])
            is_printer = any(port in open_ports for port in [515, 9100])
            is_vg = all(port in open_ports for port in [1720,5060,5061])
            is_phone = any(port in open_ports for port in [5060, 5061]) and '1720' not in open_ports


            if is_windows:
                return "Windows Machine"
            elif is_printer:
                return "Printer"
            elif is_vg:
                return "Voice Gateway"
            elif is_phone:
                return "Phone/SIP Device"
            else:
                if 22 in open_ports:
                    return "SSH Capable Device"
                else:
                    return "Unknown"
                
        else:
            return "Host unreachable"
    except Exception as e:
        logging.error(f"Nmap discovery failed for {target_ip}: {str(e)}")
        return str(e," 1")


def parse_arp_table(arp_table):
    parsed_entries = []
    arp_lines = arp_table.split('\n')
    total_lines = len(arp_lines)
    processed_lines = 0  # Counter for processed lines
    
    for line in arp_lines:
        if line.strip().endswith("FAILED"):
            processed_lines += 1
            continue  # Ignore lines with "FAILED" at the end

        if line.strip().endswith("INCOMPLETE"):
            processed_lines += 1
            continue  # Ignore lines with "INCOMPLETE" at the end
            
        # Split the line by whitespaces
        parts = line.split()
        if len(parts) < 4:
            print(f"\nSkipping {processed_lines}: {line}\n")
            processed_lines += 1
            continue  # Skip incomplete lines
        
        try:
            # Extract the IP address, MAC address, and interface
            ip_address = parts[0]
            mac_address = parts[4]
            full_interface = parts[2]
            
            # Extract the VLAN number from the interface name
            interface_parts = full_interface.split('.')
            if len(interface_parts) > 1:
                vlan = interface_parts[1]
            else:
                vlan = None
            
            # Perform additional processing
            hostname = lookup_hostname(ip_address)
            mac_oui = lookup_mac_oui(mac_address)
            nmap_result = nmap_discovery(ip_address)
            
            parsed_entry = {
                "hostname": hostname,
                "mac_address": mac_address,
                "vlan": vlan,
                "ip_address": ip_address,
                "new_vlan": "",
                "new_ip": "",
                "nmap_result": nmap_result,
                "mac_oui": mac_oui
            }
            parsed_entries.append(parsed_entry)

        except IndexError as ie:
            print(f"\nError parsing line {processed_lines}: {line}\nError:\n{ie}")
        
        # Increment the counter
        processed_lines += 1

        # Calculate the progress percentage
        progress = (processed_lines / total_lines) * 100

        # Print the progress message
        print(f"\r{progress:.2f}% - Parsed {processed_lines}/{total_lines} ARP entries", end='')
    
    return parsed_entries

def main():
    #site_id = input("(For filename purposes)\nEnter site code: ")
    routers = input("(Example: 172.16.1.1,172.16.1.2,etc)\nEnter SilverPeak IP Address (or type 'exit' to quit): ")
    today = date.isoformat(date.today())
    username = input("Enter your username: ")
    password = getpass.getpass(prompt="Enter your password: ")

    # Initialize a logging object to log input/output
    logging.basicConfig(filename=f'Output\{today}.txt', level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Validate the format of the input
    router_list = routers.split(',')
    router_list = [r.strip() for r in router_list]  # Remove leading/trailing whitespace

    for router in router_list:
        # Define the target device and SSH parameters
        device = {
            'device_type': 'cisco_ios',  # SilverPeak devices often work with Cisco device_type
            'ip': router,
            'username': username,
            'password': password,
        }

        try:
            # Establish an SSH connection to the device
            connection = ConnectHandler(**device)
            logging.info(f'Connected to device IP: {router}')

            # Send the 'enable' command without a password
            connection.enable()
            logging.info('Enabled mode')

            device_name = connection.find_prompt().rstrip('#')

            # Send the 'show arp' command and collect the output
            arp_table = connection.send_command('show arp')
            logging.info('Executed "show arp" command')

            # Close the SSH connection
            connection.disconnect()
            logging.info('Disconnected from device')

            # Process ARP table through parse_arp_table function.
            print("Parsing ARP Table")
            parsed_entries = parse_arp_table(arp_table)

            # Create a DataFrame from the parsed entries
            df = pd.DataFrame(parsed_entries)

            # Rename the columns to match your desired output
            df = df.rename(columns={
                "hostname": "Hostname",
                "ip_address": "Current IP",
                "mac_address": "Current MAC",
                "mac_oui": "MAC Vendor",
                "nmap_result": "NMAP Result",
                "interface": "Interface",
                "new_vlan": "New VLAN",
                "new_ip": "New IP",
                "vlan": "Current VLAN"
            })

            # Export the DataFrame to a CSV file
            output_dir = 'Output'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            filename = f"{device_name} - arp_results - {today}.csv"
            outfile = os.path.join(output_dir, filename)
            df.to_csv(outfile, index=False)
            logging.info(f'ARP results exported to {filename}')

            print("\n### Parsing Completed ###\n")
            print(f"ARP results exported to {filename}")

        except Exception as e:
            print(f"\nAn error occurred:\n{str(e)}")
            logging.error(f'Error: {str(e)}')

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f'Unhandled error: {str(e)}')
    
    # Wait for user input before exiting
    input("Press Enter to exit...")