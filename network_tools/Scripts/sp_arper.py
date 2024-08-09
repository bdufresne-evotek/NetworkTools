import json
import getpass
from netmiko import ConnectHandler

# Function to get ARP data from SilverPeak appliance
def get_arp_data(device, command):
    try:
        # Establish an SSH connection to the device
        connection = ConnectHandler(**device)

        # Enable mode (no password required)
        connection.enable()

        # Enter shell mode
        connection.send_command("_spsshell")

        # Run the arp command and collect the output
        arp_output = connection.send_command(command)

        # Close the SSH connection
        connection.disconnect()

        return arp_output
    except Exception as e:
        return str(e)

def main(ip):
    # Define the target device and SSH parameters
    device = {
        'device_type': 'cisco_ios',  # SilverPeak devices often work with Cisco device_type
        'ip': ip,
        'username': input("Enter your username: "),
        'password': getpass.getpass(prompt="Enter your password: "),
    }

    # Define the command to run (ARP excluding incomplete entries)
    arp_command = "arp | grep -v incomplete"

    # Get ARP data from the device
    arp_output = get_arp_data(device, arp_command)

    # Process ARP output and extract IP and MAC addresses
    arp_entries = []
    for line in arp_output.splitlines():
        if len(line.strip()) > 0:
            parts = line.split()
            if len(parts) >= 3:
                ip_address, mac_address = parts[1], parts[3]
                arp_entries.append({'ip': ip_address, 'mac': mac_address})

    # Store the ARP data in a JSON file
    with open('arp_data.json', 'w') as json_file:
        json.dump(arp_entries, json_file, indent=4)

    print("ARP data extracted and saved in arp_data.json")

if __name__ == "__main__":
    main(ip)
