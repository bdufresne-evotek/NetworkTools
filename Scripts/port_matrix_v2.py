# Author - Bryan Dufresne
# Description:
"""Uses inventory to assemble formatted port-matrix xlsx file."""

from datetime import date
import getpass
import json
from netmiko import ConnectHandler
import pandas as pd
import os
import re
import xlsxwriter

def main():

    print("#####\nPort Matrixer v2\n#####\n")

    today = date.isoformat(date.today())

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
    inventory_name = selected_inventory.split(".json")[0]
    inventory_path = os.path.join('Inventories', selected_inventory)

    # Load device information from the selected inventory JSON file
    with open(inventory_path, 'r') as json_file:
        devices = json.load(json_file)

    # Prompt for the user's username and password
    preorpost = input("Discovery, Pre-change, or post-change? [type disc, pre, or post]: ")
    username = input("Enter your username: ")
    password = getpass.getpass(prompt="Enter your password: ")

    # Create the "Output" directory if it doesn't exist
    job_folder = preorpost + " - " + today
    output_dir = os.path.join('Output', inventory_name, job_folder)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Sets JSON file to record results of current job
    joblog = f"{inventory_name}_{today}_job-log.json"
    joblog_out = os.path.join(output_dir, joblog)
    joblog_data = {'Success': [], 'Error': []}

    # List to store dataframes for each device
    device_dfs = []

    # Connect to devices and execute the show commands
    for device in devices:
        prompt = 'Undefined'
        device_type = device['device_type']
        device_ip = device['device_IP']

        device_info = {
            'device_type': device_type,
            'ip': device_ip,
            'username': username,
            'password': password,
            #uncomment below for slower old gear like HP Comware
            #'global_delay_factor': 60,
        }

        # Connect to the switch
        try:
            connection = ConnectHandler(**device_info)
            #connection.enable()
            # Execute show commands
            prompt = connection.find_prompt().strip("#<>[]")
            print(f'\nConnected to {prompt} [{device_ip}]\n')
            print('Collecting "show interfaces status"...')
            show_interfaces_status = connection.send_command("show interfaces status")
            print('Collecting "show interfaces description"...')
            show_interfaces_desc = connection.send_command("show interfaces description")
            print('Collecting "show interfaces switchport"...')
            show_interfaces_switchport = connection.send_command("show interfaces switchport")
            print('Collecting "show cdp neighbor detail"...')
            show_cdp_neighbor_detail = connection.send_command("show cdp neighbor detail")
            print('Collecting "show lldp neighbors detail"...')
            show_lldp_neighbors_detail = connection.send_command("show lldp neighbors detail")
            print('Collecting "show mac address-table"...')
            show_mac_address_table = connection.send_command("show mac address-table")

            # Parse show interfaces description output
            interface_desc_lines = show_interfaces_desc.strip().splitlines()
            interface_desc_data = []
            for line in interface_desc_lines[1:]:
                interface = line.split()[0]
                if not interface.startswith("Vl"):
                    desc = line[55:].strip()
                    interface_desc_data.append([interface, desc])

            # Convert the description data into a DataFrame
            interface_desc_df = pd.DataFrame(interface_desc_data, columns=["Interface", "Description"])

            # Parse show interfaces status output
            interface_status_lines = show_interfaces_status.strip().splitlines()
            interface_status_data = []
            for line in interface_status_lines[1:]:
                if len(line.split()[0].strip()) < 6:
                    interface = line[:6].strip()
                    media = line[67:].strip()
                    status = line[29:43].strip()
                elif len(line.split()[0].strip()) < 9:
                    interface = line[:9].strip()
                    media = line[70:].strip()
                    status = line[32:45].strip()
                elif len(line.split()[0].strip()) < 13:
                    interface = line[:12].strip()
                    media = line[72:].strip()
                    status = line[34:47].strip()
                interface_status_data.append([interface, media, status])

            # Convert the status data into a DataFrame
            interface_status_df = pd.DataFrame(interface_status_data, columns=["Interface", "Media", "Status"])

            # Merge the status DataFrame with the description DataFrame
            interface_data_df = pd.merge(interface_desc_df, interface_status_df, on="Interface", how="left")

            # Parse show interfaces switchport output
            switchport_lines = show_interfaces_switchport.strip().split("\n\n")
            switchport_data = []
            for section in switchport_lines:
                lines = section.strip().splitlines()
                interface = None
                admin_status = None
                admin_mode = None
                access_vlan = None
                access_vlan_name = None
                native_vlan = None
                native_vlan_name = None
                voice_vlan = None
                voice_vlan_name = None
                trunk_vlans = None
                trunk_vlans_list = None
                idx = 0

                for idx, line in enumerate(lines):
                    print(f'\rParsing switchport info...', end='', flush=True)
                    if line.startswith("Name:"):
                        interface = line.split()[1]
                    #elif line.startswith("Switchport:"):
                    #    admin_status = line.split()[1:]
                    elif line.startswith("Administrative Mode:"):
                        admin_mode = " ".join(line.split()[2:])
                    elif line.startswith("Access Mode VLAN:"):
                        access_vlan = line.split()[3]
                        #access_vlan_name = line.split()[4].strip("()")
                    elif line.startswith("Trunking Native Mode VLAN:"):
                        native_vlan = line.split()[4]
                        #if len(line.split()) > 5:
                        #    native_vlan_name = line.split()[5].strip("()")
                    elif line.startswith("Voice VLAN:"):
                        voice_vlan = line.split()[2]
                        #if voice_vlan != "none":
                        #    voice_vlan_name = line.split()[3].strip("()")
                        #else:
                        #    voice_vlan_name = "none"
                    elif line.startswith("Trunking VLANs Enabled:"):
                        # Add the VLANs from the current line
                        trunk_vlans_list = line.split()[3]
                        # Check for continuation line
                        if trunk_vlans_list.endswith(",") and idx + 1 < len(lines):
                            next_line = idx + 1
                            trunk_vlans_list += lines[next_line].split()[0]  # Concatenate the VLANs from the next line
                        # Use the concatenated string as the trunk_vlans
                        trunk_vlans = trunk_vlans_list

                switchport_data.append([
                    #interface, admin_status, admin_mode, access_vlan, access_vlan_name, native_vlan, native_vlan_name, voice_vlan, voice_vlan_name, trunk_vlans
                    interface, admin_mode, access_vlan, native_vlan, voice_vlan, trunk_vlans
                ])

            print('\nSwitchport info parsed!')
            switchport_df = pd.DataFrame(switchport_data, columns=[
                "Interface", "Admin Mode", "Access VLAN", "Native VLAN", "Voice VLAN", "Trunked VLANs"
            ])

            # Parse show cdp neighbor detail output
            cdp_neighbor_lines = show_cdp_neighbor_detail.strip().splitlines()
            cdp_neighbor_data = []
            cdp_total_lines = len(cdp_neighbor_lines)
            cdp_current_line = 0
            ip_address = None  # Initialize ip_address outside the loop
            local_interface = None
            remote_interface = None
            device_id = None
            platform = None
            
            for line in cdp_neighbor_lines:
                cdp_current_line += 1
                print(f'\rParsing CDP neighbor details - Line {cdp_current_line} of {cdp_total_lines}', end='', flush=True)
                if line.startswith("Device ID:"):
                    if local_interface is not None:
                        # Append the previous data before resetting
                        cdp_neighbor_data.append([local_interface, device_id, ip_address, platform, remote_interface])
                    device_id = line.split(":")[1].strip()
                    ip_address = None
                    platform = None
                    remote_interface = None
                elif line.startswith("  IP address:"):
                    ip_address = line.split(":")[1].strip()
                elif line.startswith("Interface:"):
                    local_interface_str = line.split()[1]
                    comma_index = local_interface_str.find(",")
                    if local_interface_str.startswith("GigabitEthernet"):
                        if comma_index != -1:
                            local_interface = "Gi" + local_interface_str[15:comma_index]
                        else:
                            local_interface = "Gi" + local_interface_str[15:]
                    elif local_interface_str.startswith("TenGigabitEthernet"):
                        if comma_index != -1:
                            local_interface = "Te" + local_interface_str[18:comma_index]
                        else:
                            local_interface = "Te" + local_interface_str[18:]
                    remote_interface = line.split()[6]
                elif line.startswith("Platform:"):
                    platform_str = line.split()[1:]
                    platform_comma = ' '.join(platform_str).find(",")
                    if platform_comma != -1:
                        platform = ' '.join(platform_str)[0:platform_comma]
                    else:
                        platform = ' '.join(platform_str)[0:]
                    
            # Append the last set of data
            if local_interface is not None:
                cdp_neighbor_data.append([local_interface, device_id, ip_address, platform, remote_interface])

            print('\nCDP Parsed!')
            cdp_neighbor_df = pd.DataFrame(cdp_neighbor_data, columns=["Interface", "CDP Neighbor Name", "CDP Neighbor IP", "CDP Neighbor Platform", "CDP Neighbor Interface"])

            # Parse show lldp neighbors detail output
            lldp_neighbor_lines = show_lldp_neighbors_detail.strip().splitlines()
            lldp_neighbor_data = []
            lldp_total_lines = len(lldp_neighbor_lines)
            lldp_current_line = 0
            local_interface = None
            remote_interface = None
            system_name = None
            ip_address = None
            system_description = None
            processing_description = False

            for line in lldp_neighbor_lines:
                lldp_current_line += 1
                print(f'\rParsing LLDP neighbor details - Line {lldp_current_line} of {lldp_total_lines}', end='', flush=True)
                if line.startswith("Local Intf:"):
                    if local_interface is not None:
                        # Append the previous data before resetting
                        lldp_neighbor_data.append([local_interface, system_name, ip_address, system_description, remote_interface])
                    local_interface = line.split(":")[1].strip()
                    remote_interface = None
                    system_name = None
                    ip_address = None
                    system_description = None
                elif line.startswith("Port id:"):
                    remote_interface = line.split(":")[1].strip()
                elif line.startswith("System Name:"):
                    system_name = line.split(":")[1].strip()
                elif line.startswith("    IP:"):
                    ip_address = line.split(":")[1].strip()
                elif line.startswith("System Description:"):
                    processing_description = True
                elif processing_description:
                    system_description = line.strip()
                    processing_description = False

            # Append the last set of data
            if local_interface is not None:
                lldp_neighbor_data.append([local_interface, system_name, ip_address, system_description, remote_interface])

            print('\nLLDP Parsed!')
            lldp_neighbor_df = pd.DataFrame(lldp_neighbor_data, columns=["Interface", "LLDP Neighbor Name", "LLDP Neighbor IP", "LLDP Neighbor System", "LLDP Neighbor Interface"])

            # Parse show mac address-table output
            mac_address_lines = show_mac_address_table.strip().splitlines()
            print(f'Parsing MAC table')
            mac_address_data = [line.split()[:4] for line in mac_address_lines[1:]]
            print('Adding MAC table to dataframe')
            mac_address_df = pd.DataFrame(mac_address_data, columns=["VLAN", "MAC Address", "Type", "Interface"])

            # Drop the 'Type' column and filter dashes from the 'VLAN' column
            print('Dropping "Type" column from MAC table dataframe')
            mac_address_df = mac_address_df.drop("Type", axis=1)
            mac_address_df = mac_address_df[mac_address_df["VLAN"] != "-------------------------------------------"]

            # Remove duplicate MAC addresses within each VLAN
            print('Removing duplicate MAC addresses within each VLAN')
            mac_address_df = mac_address_df.drop_duplicates(subset=["VLAN", "MAC Address"])

            # Replace None and empty strings with a placeholder value
            mac_address_df["MAC Address"] = mac_address_df["MAC Address"].fillna("None")
            mac_address_df["MAC Address"] = mac_address_df["MAC Address"].replace("", "None")

            # Group MAC addresses by Interface and concatenate them into a comma-delimited string
            print('Grouping MACs by Interface')
            mac_address_grouped = mac_address_df.groupby("Interface")["MAC Address"].apply(lambda x: ",".join(x)).reset_index()

            # Merge the grouped MAC addresses back to the original DataFrame
            print('Merging grouped MACs by Interface back into the dataframe')
            mac_address_df = mac_address_df.merge(mac_address_grouped, on="Interface", how="left")

            # Rename the column to "MAC Addresses"
            print('Renaming column to "MAC Addresses"')
            mac_address_df = mac_address_df.rename(columns={"MAC Address": "MAC Addresses"})

            # Merge dataframes
            print('Merging Dataframe')
            merged_df = interface_data_df.merge(switchport_df, on="Interface", how="left")
            merged_df = merged_df.merge(mac_address_grouped, on="Interface", how="left")
            merged_df = merged_df.merge(cdp_neighbor_df.groupby("Interface").first().reset_index(), on="Interface", how="left")
            merged_df = merged_df.merge(lldp_neighbor_df.groupby("Interface").first().reset_index(), on="Interface", how="left")

            # Append dataframe to list
            print('Appending Dataframe to list')
            device_dfs.append((prompt, merged_df, device_ip))

        except Exception as e:
            print(f'Unknown exception with: {device_ip}\nError: {e}')
            joblog_data['Error'].append({'device_ip': device_ip, 'device_type': device_type, 'error': str(e)})
            
        finally:
            connection.disconnect()
            print(f'\nCompleted processing on: {prompt} [{device_ip}].')

    # Save to Excel with multiple sheets
    excel_file_path = os.path.join(output_dir, f"{inventory_name}_port-matrix_{today}.xlsx")
    print(f'Exporting to {excel_file_path}')
    with pd.ExcelWriter(excel_file_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        index_worksheet = workbook.add_worksheet("Index")  # Create the index worksheet
        index_worksheet.write('A1', 'Devices', workbook.add_format({'bold': True}))

        # Write worksheet names and create clickable links
        for idx, (prompt, df, device_ip) in enumerate(device_dfs, start=2):  # Unpack the tuple
            sheet_name = f"{prompt}_{device_ip}"  # Create the sheet name with prompt and device_ip
            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=2)  # Start writing from row 3
            worksheet = writer.sheets[sheet_name]  # Get the worksheet object
            merge_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
            worksheet.merge_range('B1:D1', f"Device: {prompt} - IP: {device_ip}", merge_format)  # Merge and center heading in first two columns
            worksheet.set_row(2, 15)  # Add a blank row after the heading

            # Automatically adjust column widths based on content
            for i, width in enumerate(get_col_widths(df)):
                worksheet.set_column(i, i, width)

            # Add entry to the index worksheet
            cell_ref = xlsxwriter.utility.xl_rowcol_to_cell(idx, 0)
            link = f'internal:{sheet_name}!A1'  # Internal link to A1 cell of the worksheet
            index_worksheet.write_url(cell_ref, link, string=sheet_name)
            
            # Freeze the top 3 rows
            worksheet.freeze_panes(3, 0)

        # Set up the index worksheet
        index_worksheet.set_column('A:A', 30)  # Set the column width for worksheet names
        index_worksheet.freeze_panes(1, 0)  # Freeze the top row

        # Hide gridlines and headings in the index worksheet
        index_worksheet.hide_gridlines(2)

    # Save job log to JSON
    with open(joblog_out, 'w') as f:
        json.dump(joblog_data, f, indent=4)
        
def get_col_widths(dataframe):
    # Get the maximum width of each column
    return [max([len(str(value)) for value in dataframe[col].values] + [len(col)]) for col in dataframe.columns]


if __name__ == "__main__":
    main()