# Author - Bryan Dufresne
# Description:
"""Aggregates modules from Scripts directory and provides selection to execute."""

import cowsay
import importlib
import os

# Function to list Python files in a directory
def list_python_files(directory):
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                python_files.append(file)
    return python_files

# Function to get the module description from its docstring
def get_module_description(module_name):
    try:
        # Dynamically import the module using importlib
        module = importlib.import_module(f'Scripts.{module_name}')
        # Retrieve the module's docstring (__doc__) or provide a default message
        return module.__doc__ or "No description available."
    except ModuleNotFoundError:
        return "No description available."

# Function to execute the selected module's 'main' function
def execute_selected_module(module_name):
    try:
        # Dynamically import the module using importlib
        module = importlib.import_module(f'Scripts.{module_name}')
        # Execute the 'main' function of the module (assuming each module has a 'main' function)
        module.main()
    except ModuleNotFoundError as e:
        print("Module not found.")
        print(e)
    except AttributeError as e:
        print(f"The selected module ({module_name}) does not have a 'main' function.")
        print(e)

# Main function
def main():

    print('#####\t\t\t#####\n\n\tAutomated\n\tNetwork\n\tDiscovery,\n\tReconaissaince, &\n\tEnumeration\n\tWorkbench\n\n#####\t\t\t#####')
    cowsay.cow("Hi, I'm ANDREW!")

    script_directory = 'Scripts'

    while True:
        print("Available modules:")
        python_files = list_python_files(script_directory)

        print("0. Exit")  # Option to exit the script

        for idx, module_file in enumerate(python_files, start=1):
            module_name = module_file[:-3]  # Remove '.py' extension
            description = get_module_description(module_name)
            print(f"{idx}. {module_name}:\t\t{description}")  # Display module and description on the same line with a tab

        try:
            selection = int(input("Select a module (enter its number or 0 to exit): "))
            if selection == 0:
                break  # Exit the script if 0 is selected
            elif 1 <= selection <= len(python_files):
                selected_module = python_files[selection - 1][:-3]  # Remove '.py' extension
                execute_selected_module(selected_module)
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")


if __name__ == "__main__":
    main()
