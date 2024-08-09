# Author - Bryan Dufresne
# Description:
"""Ping sweeps a subnet and then ARPs each host **Must be run from target network segment."""

import ipaddress
import json
import os
from datetime import datetime
from scapy.all import ARP, Ether, srp

def discover_hosts(subnet):
    active_hosts = []
    local_ip = subnet.network_address.compressed
    ip_addresses = [str(host) for host in subnet.hosts()]
    ans, _ = srp(
        Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_addresses), timeout=2, verbose=False
    )


    for _, rcv in ans:
        active_hosts.append({"ip": rcv.psrc, "mac": rcv.hwsrc})
    
    return active_hosts

def main():
    print("#####\nLocal Subnet Recon\n#####\n")

    subnets_input = input("Enter subnet(s) separated by commas (10.0.0.0/24,10.0.10.0/24)\nSubnets: ")
    subnets = subnets_input.split(',')

    current_datetime = datetime.now().strftime("%Y-%m-%d")
    output_directory = 'Output'

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    total_successful_pings = 0
    total_attempts = 0

    all_results = []

    for subnet_str in subnets:
        try:
            subnet = ipaddress.ip_network(subnet_str.strip(), strict=False)
        except ValueError:
            print(f"Invalid subnet/CIDR format: {subnet_str.strip()}. Skipping.")
            continue

        output_filename = f"Recon - {subnet_str.replace('/', '-')} - {current_datetime}.json"

        successful_pings = 0
        total_attempts_subnet = 0

        active_hosts = discover_hosts(subnet)
        
        results_dict = {
            "total_alive": len(active_hosts),
            "subnet_size": len(list(subnet.hosts())),
            "active_hosts": active_hosts
        }

        output_path_subnet = os.path.join(output_directory, output_filename)
        with open(output_path_subnet, 'w') as json_file:
            json.dump(results_dict, json_file, indent=4)

        total_successful_pings += len(active_hosts)
        total_attempts += len(list(subnet.hosts()))
        all_results.extend(active_hosts)

        print(f"\nSubnet recon for {subnet_str} completed.")
        print(f"Results saved to: {output_path_subnet}")

    combined_results = {
        "total_successful": total_successful_pings,
        "total_attempts": total_attempts,
        "all_active_hosts": all_results
    }

    combined_output_path = os.path.join(output_directory, f"Recon Summary - {current_datetime}.json")
    with open(combined_output_path, 'w') as json_file:
        json.dump(combined_results, json_file, indent=4)

    print("\nSubnet recon completed.")
    print(f"Combined results saved to: {combined_output_path}")

if __name__ == "__main__":
    main()
