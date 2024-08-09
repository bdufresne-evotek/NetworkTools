# show_commander_v2.py
# Author - Bryan Dufresne
# Description:
"""Runs show commands from json file against a specified inventory file."""

from datetime import date
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, scrolledtext
from netmiko import ConnectHandler
import logging
import threading

#
# Define global variables
#
today = date.isoformat(date.today())

# Directory where this script is being run from
root_dir = os.path.abspath(os.path.dirname(__file__))

# Define other required directories
resource_dir = os.path.join(root_dir, 'Resources')
inventory_dir = os.path.join(root_dir, 'Inventories')
output_dir = os.path.join(root_dir, 'Output')
log_dir = os.path.join(root_dir, 'Logs')
script_dir = os.path.join(root_dir, 'Scripts')

# Check if the directories exist, and if not, create them
if not os.path.exists(resource_dir):
    os.makedirs(resource_dir)

if not os.path.exists(inventory_dir):
    os.makedirs(inventory_dir)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

if not os.path.exists(script_dir):
    os.makedirs(script_dir)

# Setup logging
#
logfile_name = f"{today}.log"
logfile = os.path.join(log_dir, logfile_name)
logging.basicConfig(filename=logfile, level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Setup threading

# Cheater function to thread another function
def thread_function(function):
    thread = threading.Thread(target=function)
    thread.start()

# Initialize main window
root = tk.Tk()
root.title("Network Device Show Commander")

# Create notebook (tabs)
notebook = ttk.Notebook(root)
notebook.pack(side=tk.BOTTOM, padx=10, pady=10, fill=tk.BOTH, expand=True)

# Terminal frame (tab)
terminal_frame = tk.Frame(notebook)
notebook.add(terminal_frame, text='Terminal')

# Terminal output text widget
terminal = tk.Text(terminal_frame, height=10, width=100, state=tk.DISABLED)
terminal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Terminal output scrollbar
terminal_scrollbar = tk.Scrollbar(terminal_frame)
terminal_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
terminal.config(yscrollcommand=terminal_scrollbar.set)
terminal_scrollbar.config(command=terminal.yview)

# Command List frame (tab)
command_list_frame = tk.Frame(notebook)
notebook.add(command_list_frame, text='Command List')

# Command List text widget
command_list_text = scrolledtext.ScrolledText(command_list_frame, wrap=tk.WORD)
command_list_text.pack(fill=tk.BOTH, expand=True)

# Add Save button to Command List frame
save_command_list_button = tk.Button(command_list_frame, text="Save Commands", command=lambda: save_command_list())
save_command_list_button.pack(pady=5)

# Load command list JSON file into text widget
def load_command_list():
    command_path = os.path.join(resource_dir, 'show_commands.json')
    if not os.path.exists(command_path):
        create_show_commands_json(command_path)
    with open(command_path, 'r') as file:
        commands = json.load(file)
        command_list_text.insert(tk.END, json.dumps(commands, indent=4))

load_command_list()

# Function to save command list JSON file from text widget
def save_command_list():
    command_path = os.path.join(resource_dir, 'show_commands.json')
    try:
        commands = json.loads(command_list_text.get("1.0", tk.END))
        with open(command_path, 'w') as file:
            json.dump(commands, file, indent=4)
        messagebox.showinfo("Success", "Command list saved successfully.")
        terminal_print("Command list saved successfully.\n")
        logging.info("Command list saved successfully.\n")
        terminal_print("Re-loading command list.\n")
        
        # Clear the current content of the text widget before reloading
        command_list_text.delete("1.0", tk.END)
        load_command_list()
    except ValueError as ve:
        messagebox.showerror("Error", "Invalid JSON format.")
        terminal_print(f"Error: Invalid JSON format.\n{ve}\n")
        logging.error(f"Error: Invalid JSON format.\n{ve}\n")

# Create a canvas to add scrollbar support for main_frame
canvas = tk.Canvas(root)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Add scrollbar to the canvas
main_frame_scrollbar = tk.Scrollbar(root, orient=tk.VERTICAL, command=canvas.yview)
main_frame_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
canvas.config(yscrollcommand=main_frame_scrollbar.set)

# Create the main frame within the canvas
main_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=main_frame, anchor='nw')

# Button frame
button_frame = tk.Frame(main_frame)
button_frame.grid(row=1, column=0, padx=5, pady=5, sticky='w')

# Frame for entries
frame = tk.Frame(main_frame)
frame.grid(row=2, column=0, padx=5, pady=5, sticky='nsew')

# Configure row and column weights
main_frame.grid_rowconfigure(2, weight=1)
main_frame.grid_columnconfigure(0, weight=1)

# Column labels
tk.Label(frame, text="Delete").grid(row=0, column=0, padx=5, pady=5)
tk.Label(frame, text="IP Address").grid(row=0, column=1, padx=5, pady=5)
tk.Label(frame, text="Device Type").grid(row=0, column=2, padx=5, pady=5)
tk.Label(frame, text="Username").grid(row=0, column=3, padx=5, pady=5)
tk.Label(frame, text="Password").grid(row=0, column=4, padx=5, pady=5)
tk.Label(frame, text="Show Password").grid(row=0, column=5, padx=5, pady=5)

# Function to print text into the terminal
def terminal_print(text):
    terminal.config(state=tk.NORMAL)
    terminal.insert(tk.END, text)
    terminal.see(tk.END)  # Auto-scroll to the end
    terminal.update_idletasks()  # Force the GUI to update
    terminal.config(state=tk.DISABLED)

# Function to add a new row (adjusted for new layout)
def add_row(data=None):
    row = len(entries) + 1  # Adjust row index for new rows
    delete_button = tk.Button(frame, text="X", command=lambda r=row: delete_row(r))
    ip = tk.Entry(frame)
    device_type = ttk.Combobox(frame, values=device_types)
    username = tk.Entry(frame)
    password = tk.Entry(frame, show='*')

    entries.append({
        'delete': delete_button,
        'ip': ip,
        'type': device_type,
        'username': username,
        'password': password
    })
    
    delete_button.grid(row=row, column=0, padx=5, pady=5)
    ip.grid(row=row, column=1, padx=5, pady=5)
    device_type.grid(row=row, column=2, padx=5, pady=5)
    username.grid(row=row, column=3, padx=5, pady=5)
    password.grid(row=row, column=4, padx=5, pady=5)
    
    # Add show password checkbox
    show_password_var = tk.BooleanVar()
    show_password_check = tk.Checkbutton(
        frame, 
        variable=show_password_var,
        command=lambda entry=password, 
        var=show_password_var: toggle_password(entry, var)
    )
    show_password_check.grid(row=row, column=5, padx=5, pady=5)
    show_password_vars.append(show_password_var)
    
    if data:
        ip.insert(0, data.get('ip', ''))
        device_type.set(data.get('device_type', ''))
        username.insert(0, data.get('username', ''))
        password.insert(0, data.get('password', ''))

# Function to enable/disable username and password fields
def update_entry_states():
    enabled = not use_same_username_password.get()
    for entry in entries[1:]:
        entry['username'].config(state=tk.NORMAL if enabled else tk.DISABLED)
        entry['password'].config(state=tk.NORMAL if enabled else tk.DISABLED)

# Function to run show commands using Netmiko and save output
def run_show_commands():
    try:
        # Load the latest commands from the Command List text widget
        show_commands = json.loads(command_list_text.get("1.0", tk.END))
    except json.JSONDecodeError:
        messagebox.showerror("Error", "Invalid JSON format in command list.")
        terminal_print("Error: Invalid JSON format in command list.\n")
        logging.error("Error: Invalid JSON format in command list.\n")
        return
        
    for entry in entries:
        ip = entry['ip'].get()
        if not validate_ip(ip):
            messagebox.showerror("Invalid IP", f"Invalid IP address: {ip}")
            continue

        device_type = entry['type'].get()
        username = entries[0]['username'].get() if use_same_username_password.get() else entry['username'].get()
        password = entries[0]['password'].get() if use_same_username_password.get() else entry['password'].get()

        device = {
            'device_type': device_type,
            'ip': ip,
            'username': username,
            'password': password
        }
        
        try:
            with ConnectHandler(**device) as net_connect:
                hostname = net_connect.find_prompt().strip('#<>[]')
                outfile = f"{hostname} - {ip}.txt"
                filename = os.path.join(output_dir, outfile)
                
                logging.info(f"Connected to {hostname} ({ip})")
                terminal_print(f"Connected to {hostname} ({ip})\n")

                output = f"=====================\n{hostname} ({ip})\n=====================\n"
                for command in show_commands[device_type]:
                    terminal_print(f"Sending {command}\n")
                    logging.info(f"Sending {command}\n")
                    output += f"\n\n{command}\n{'-' * len(command)}\n"
                    output += net_connect.send_command(command)
                
                with open(filename, 'w') as file:
                    file.write(output)
                
                logging.info(f"Output saved to {filename}\n")
                terminal_print(f"Output saved to {filename}\n")
        
        except Exception as e:
            logging.error(f"Failed to connect to {ip}: {str(e)}")
            terminal_print(f"Failed to connect to {ip}: {str(e)}\n")
            continue
    
    if any([os.path.exists(os.path.join(output_dir, f)) for f in os.listdir(output_dir)]):
        messagebox.showinfo("Success", "Output saved successfully.")
    else:
        logging.warning("No output to save.\n")
        terminal_print("No output to save.\n")
        messagebox.showwarning("No Output", "No output to save.")

# Use same username and password for all devices checkbox
use_same_username_password = tk.BooleanVar()
same_cred_check = tk.Checkbutton(main_frame, text="Use same username/password for all devices", variable=use_same_username_password, command=update_entry_states)
same_cred_check.grid(row=0, column=0, padx=5, pady=5, columnspan=4, sticky='w')

# List to store entry widgets
entries = []
show_password_vars = []

# Function to create the show_commands.json file if it doesn't exist
def create_show_commands_json(file_path):
    commands = {
        "cisco_ios": [
            "show inventory",
            "show ver",
            "show license all",
            "show run",
            "show int status",
            "show ip int brief | exc unas",
            "show etherchannel summary",
            "show mac address-table",
            "show spanning-tree summary",
            "show spanning-tree",
            "show ip route",
            "show cdp neighbor",
            "show lldp neighbor"
        ],
        "arista_eos": [
            "show ver",
            "show module",
            "show switch",
            "show hw-inventory",
            "show vlan",
            "show etherchannel summary",
            "show int trunk",
            "show spanning-tree sum",
            "show lldp neigh",
            "show int statu",
            "show ip int brief | exc unas",
            "show mac add",
            "show ip route",
            "show ip mroute",
            "show ip igmp groups",
            "show run"
        ],
        "aruba_os": [
            "show version",
            "show system",
            "show stacking",
            "show interfaces transceiver detail",
            "show lacp",
            "show int trunk",
            "show trunks",
            "show vlan",
            "show spanning-tree",
            "show arp",
            "show ip route",
            "show ip int brief",
            "show ip",
            "show interfaces",
            "show mac-address",
            "show lldp info remote-device det",
            "show lldp info remote-device",
            "show run"
        ],
        "hp_procurve": [
            "show version",
            "show system",
            "show services",
            "show modules",
            "show lacp",
            "show trunks",
            "show lldp info remote-device",
            "show cdp neigh",
            "show cdp neigh detail",
            "show vlan",
            "show interface brief",
            "show spanning-tree",
            "show arp",
            "show ip route",
            "show ip",
            "show ip igmp",
            "show interfaces brief",
            "show mac-address",
            "show running-config"
        ],
        "hp_comware": [
            "display version",
            "display lldp neighbor-information",
            "display link-aggregation summary",
            "display interface",
            "display interface brief",
            "display vlan all",
            "display mac-address",
            "display stp brief",
            "display stp",
            "display current-configuration"
        ]
    }

    command_path = os.path.join(resource_dir, file_path)

    if not os.path.exists(command_path):
        with open(command_path, 'w') as file:
            json.dump(commands, file, indent=4)
        logging.info(f"{command_path} created successfully.\n")
        terminal_print(f"{command_path} created successfully.\n")
    else:
        logging.info(f"{command_path} already exists.\n")
        terminal_print(f"{command_path} already exists.\n")

# Function to load device types from the JSON file
def load_device_types(file_path):
    # Check if the show_commands.json file exists
    command_path = os.path.join(resource_dir, file_path)
    if not os.path.exists(command_path):
        terminal_print("show_commands.json doesn't exist - creating generic copy\n")
        logging.info("show_commands.json doesn't exist - creating generic copy\n")
        create_show_commands_json(command_path)

    with open(command_path, 'r') as file:
        commands = json.load(file)
    device_types = ', '.join(commands.keys())
    terminal_print(f"Loaded the following device types from {command_path}\nDevice Types: {device_types}\n")
    logging.info(f"Loaded the following device types from {command_path}\nDevice Types: {device_types}\n")
    return list(commands.keys())

# Ensure the show_commands.json file exists and load device types
device_types = load_device_types('show_commands.json')

# Function to validate IPv4 address
def validate_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not 0 <= int(part) <= 255:
            return False
    return True

# Function to toggle password visibility
def toggle_password(entry, show_password_var):
    if show_password_var.get():
        entry.config(show='')
    else:
        entry.config(show='*')


# Function to delete a row
def delete_row(row):
    # Remove the row from the frame
    for widget in frame.grid_slaves(row=row):
        widget.grid_forget()
    
    # Remove the entry from the list
    entries.pop(row - 1)
    
    # Move rows up
    for i in range(row - 1, len(entries)):
        for widget in frame.grid_slaves(row=i + 2):
            widget.grid(row=i + 1)

# Function to save entered data to a user-named .json file - specifically excludes saving passwords
def save_inventory():
    data = []
    common_username = entries[0]['username'].get() if use_same_username_password.get() else None
    #common_password = entries[0]['password'].get() if use_same_username_password.get() else None

    for entry in entries:
        ip = entry['ip'].get()
        if not validate_ip(ip):
            messagebox.showerror("Invalid IP", f"Invalid IP address: {ip}")
            return
        device_type = entry['type'].get()
        username = common_username if use_same_username_password.get() else entry['username'].get()
        #password = common_password if use_same_username_password.get() else entry['password'].get()
        data.append({
            'ip': ip,
            'device_type': device_type,
            'username': username
            # Password is intentionally excluded
        })
    
    # Prompt for filename to save
    outname = simpledialog.askstring("Input", "Enter name for inventory:")
    if outname:
        outfile = f"{outname}.json"
        filename = os.path.join(inventory_dir, outfile)
        with open(f"{filename}", 'w') as file:
            json.dump(data, file, indent=4)
        messagebox.showinfo("Success", "Data saved successfully!")
        terminal_print(f"Data saved successfully to {filename}.\n")
        logging.info(f"Data saved successfully to {filename}.\n")
    else:
        messagebox.showwarning("Cancelled", "Save operation cancelled.")
        terminal_print("Save operation cancelled.\n")
        logging.warning("Save operation cancelled.\n")

# Function to load data from a JSON file
def load_inventory():
    # Open a file dialog to select a JSON file from the "Inventories" folder
    file_path = filedialog.askopenfilename(
        initialdir=inventory_dir,  # Start in the "Inventories" folder
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    
    if not file_path:
        return
    
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    # Clear existing entries
    for widget in frame.winfo_children():
        widget.destroy()
    entries.clear()
    
    # Recreate column labels
    tk.Label(frame, text="Delete").grid(row=0, column=0, padx=5, pady=5)
    tk.Label(frame, text="IP Address").grid(row=0, column=1, padx=5, pady=5)
    tk.Label(frame, text="Device Type").grid(row=0, column=2, padx=5, pady=5)
    tk.Label(frame, text="Username").grid(row=0, column=3, padx=5, pady=5)
    tk.Label(frame, text="Password").grid(row=0, column=4, padx=5, pady=5)
    tk.Label(frame, text="Show Password").grid(row=0, column=5, padx=5, pady=5)
    
    # Add rows with loaded data
    for entry_data in data:
        add_row(entry_data)

# Add, Save, Load buttons
tk.Button(button_frame, text="Add Row", command=add_row).grid(row=0, column=0, padx=5, pady=5)
tk.Button(button_frame, text="Save Inventory", command=save_inventory).grid(row=0, column=1, padx=5, pady=5)
tk.Button(button_frame, text="Load Inventory", command=load_inventory).grid(row=0, column=2, padx=5, pady=5)

# Run button
tk.Button(button_frame, text="Run Show Commands", command=run_show_commands, bg='lightgreen').grid(row=0, column=3, padx=5, pady=5)

# Add initial row
add_row()

# Function to configure the canvas scroll region
def on_frame_configure(canvas):
    canvas.configure(scrollregion=canvas.bbox("all"))

# Bind the frame configuration event to update the scroll region
frame.bind("<Configure>", lambda event, canvas=canvas: on_frame_configure(canvas))

# Display initial welcome message in terminal
terminal_print("Welcome to the Show Commander v2!\nFor questions, issues, and features contact Bryan Dufresne.\n")

# Run the application
root.mainloop()
