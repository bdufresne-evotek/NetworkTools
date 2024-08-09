import os
from netmiko import ConnectHandler
from datetime import date
from update_oui_vendors import update_oui
from mac_vendor_lookup import MacLookup, BaseMacLookup
import pandas as pd
import getpass
import logging


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

def parse_mac_table(mac_table):
    parsed_entries = []
    mac_lines = mac_table.split('\n')
    processed_lines = 0  # Counter for processed lines

    for line in mac_lines:
        if line.strip().endswith("CPU") or line.strip().endswith("--") or not line.strip():
            continue  # Ignore system MACs, separator lines, or empty lines

        # Split the line by whitespace
        parts = line.split()
        if len(parts) < 3:
            print(f"Skipping line: {line}")
            continue  # Skip incomplete lines

        try:
            # Extract the VLAN, MAC address, and interface
            vlan = parts[0]
            mac_address = parts[1]
            interface = parts[3]

            # Perform additional processing
            mac_oui = lookup_mac_oui(mac_address)

            parsed_entry = {
                "vlan": vlan,
                "mac_address": mac_address,
                "mac_oui": mac_oui,
                "interface": interface,
            }
            parsed_entries.append(parsed_entry)

        except Exception as e:
            print(f"Error parsing line: {line}\nError: {e}")

        # Increment the counter
        processed_lines += 1

        # Calculate the progress percentage
        progress = (processed_lines / len(mac_lines)) * 100

        # Print the progress message
        print(f"\r{progress:.2f}% - Parsed {processed_lines}/{len(mac_lines)} MAC entries", end='')

    return parsed_entries

def main():
    while True:
        site_id = input("(For filename purposes)\nEnter site code: ")
        if site_id.lower() == 'exit':
            break
        switches = input("(Example: 10.10.10.2,10.10.10.3,10.10.10.5)\nEnter switch IP address(s): ")
        today = date.isoformat(date.today())
        username = input("Enter your TACACS username: ")
        password = getpass.getpass(prompt="Enter your TACACS password: ")
        enpass = getpass.getpass(prompt="Enter enable password (if any): ")

        # Create a log file for this session
        log_filename = f"session_{site_id}_{today}.log"
        logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(message)s')

        # Validate the format of the input
        switch_list = switches.split(',')
        switch_list = [s.strip() for s in switch_list]  # Remove leading/trailing whitespace

        for switch in switch_list:
            device = {
                'device_type': 'cisco_ios',
                'ip': switch,
                'username': username,
                'password': password,
                'secret': enpass,
            }

            try:
                # Establish an SSH connection to the device
                connection = ConnectHandler(**device)
                logging.info(f'Connected to device IP: {switch}')

                # Send the 'enable' command without a password
                connection.enable()
                logging.info('Enabled mode')

                # Retrieve the hostname from the device
                hostname = connection.find_prompt().strip('#')
                switch_name = device['ip']  # Store the IP as 'switch_name' if 'hostname' is empty

                # Send the 'show mac' command and collect the output
                mac_table = connection.send_command('show mac add')
                logging.info('Executed "show mac" command')

                # Close the SSH connection
                connection.disconnect()
                logging.info('Disconnected from device')

                # Process MAC table through parse_mac_table function.
                logging.info(f"Parsing MAC Table for {hostname or switch_name}")
                parsed_entries = parse_mac_table(mac_table)

                if parsed_entries:
                    # Create a DataFrame from the parsed entries
                    df = pd.DataFrame(parsed_entries)

                    # Rename the columns to match your desired output
                    df = df.rename(columns={
                        "vlan": "VLAN",
                        "mac_address": "MAC Address",
                        "mac_oui": "MAC Vendor",
                        "interface": "Interface",
                    })

                    # Set output dir to Output
                    output_dir = 'Output'
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)

                    # Determine the file name
                    filename = f"{site_id} - {hostname or switch_name} - mac_lookup - {today}.csv"

                    # Save the data to a CSV file
                    outfile = os.path.join(output_dir, filename)
                    df.to_csv(outfile, index=False)

                    logging.info(f"MAC lookup results exported for {hostname or switch_name} to {filename}")
                else:
                    logging.warning(f"No valid data found for {hostname or switch_name}")

            except Exception as e:
                logging.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()