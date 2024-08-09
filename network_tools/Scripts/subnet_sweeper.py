# Author - Bryan Dufresne
# Description:
"""Performs CIDR-based ping sweeps of multiple subnets"""

import ipaddress
import json
import os
from datetime import datetime
from ping3 import ping

def ping_host(host, active_hosts):
	# Ping the host with a timeout of 1 second (adjust as needed)
    response_time = ping(host, timeout=1)
    if response_time is not None:
        active_hosts.append(host)
        return "alive"
    else:
        return "."

def main():

    print("#####\nSubnet Sweeper\n#####\n")

    # Prompt the user for input: subnet/CIDR (supporting multiple subnets separated by commas)
    subnet_input = input("Enter subnet/CIDR separated by commas for multiples (10.0.0.0/24,10.0.10.0/24)\nSubnets: ")

    # Convert string to dictionary by splitting on the comma
    subnets = subnet_input.split(',')

    # Get the current date and time for the output filename
    current_datetime = datetime.now().strftime("%Y-%m-%d")

    # Create the "Output" directory if it doesn't exist
    output_directory = 'Output'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Initialize variables to count successful pings and total attempts
    total_successful_pings = 0
    total_attempts = 0

    # Initialize a list to store active host IP addresses
    all_active_hosts = []

    for subnet_str in subnets:
        try:
            # Parse the user input as a network
            network = ipaddress.ip_network(subnet_str.strip(), strict=False)
        except ValueError:
            print(f"Invalid subnet/CIDR format: {subnet_str.strip()}. Skipping.")
            continue

        # Define the output filename using subnet/CIDR and current date/time
        output_filename = f"Sweep - {subnet_str.replace('/', '-')} - {current_datetime}.json"

        # Initialize variables to count successful pings and total attempts for this subnet
        successful_pings = 0
        total_attempts_subnet = 0

        # Initialize an empty string to store ping results for this subnet
        ping_results_subnet = ""

        # Initialize a list to store active host IP addresses and MACs for this subnet
        active_hosts = []
        ip_mac = []

        # Perform the ping sweep for each host in the network
        for host in network.hosts():
            total_attempts_subnet += 1
            host = str(host)
            result = ping_host(host, active_hosts)
            ping_results_subnet += result

            if result == "alive":
                # Increment the successful ping counter
                successful_pings += 1

                # Display results on the same line as they come in
                print(f"\rResults: ({successful_pings}/{total_attempts_subnet})", end='')


        # Create a dictionary to store the results and active host IP addresses for this subnet
        results_dict = {
            "total_alive": successful_pings,
            "subnet_size": total_attempts_subnet,
            "active_hosts": active_hosts
        }

        # Write the ping results for this subnet to a JSON file
        output_path_subnet = os.path.join(output_directory, output_filename)
        with open(output_path_subnet, 'w') as json_file:
            json.dump(results_dict, json_file, indent=4)

        # Update the total counts and active host list
        total_successful_pings += successful_pings
        total_attempts += total_attempts_subnet
        all_active_hosts.extend(active_hosts)

        print(f"\nPing sweep for {subnet_str} completed.")
        print(f"Results saved to: {output_path_subnet}")

    # Create a dictionary for the combined results and active host IP addresses
    combined_results = {
        "total_successful": total_successful_pings,
        "total_attempts": total_attempts,
        "all_active_hosts": all_active_hosts
    }

    # Write the combined results to a JSON file
    combined_output_path = os.path.join(output_directory, f"Sweep Summary - {current_datetime}.json")
    with open(combined_output_path, 'w') as json_file:
        json.dump(combined_results, json_file, indent=4)

															
    print("\nPing sweeps completed.")
    print(f"Combined results saved to: {combined_output_path}")

if __name__ == "__main__":
    main()
