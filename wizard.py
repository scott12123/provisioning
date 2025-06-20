import os
import shutil

def get_user_input(question):
    return input(question + ' ')

# Generate a list of options from the cambium/templates
def get_template_options():
    template_dir = 'cambium/templates/'
    templates = [f.split('.')[0] for f in os.listdir(template_dir) if f.endswith('.py')]
    return templates

# Function to replace spaces with underscore
def replace_spaces(text):
    return text.replace(' ', '_')

# Function to ensure shortname is all uppercase
def format_shortname(shortname):
    return shortname.upper()

# Function to format sitename
def format_sitename(sitename):
    return ' '.join(word.capitalize() for word in sitename.lower().split())

# Function to copy template file and replace placeholders
def generate_custom_file(sitename, shortname, device):
    # Format sitename, shortname, and device
    sitename = format_sitename(sitename)
    shortname = format_shortname(shortname)
    device = device.replace('.py', '')  # Remove file extension

    # Replace spaces with underscore
    shortname = replace_spaces(shortname)
    sitename = replace_spaces(sitename)

    # Check if output file already exists
    output_file = f'cambium/rcp-{shortname}-{device}-remote.py'
    if os.path.exists(output_file):
        overwrite = input("File already exists. Do you want to overwrite it? (Y/N): ")
        if overwrite.upper() != 'Y':
            print("Operation cancelled.")
            return

    template_dir = 'cambium/templates/'
    template_file = os.path.join(template_dir, device + '.py')

    # Copy template file
    shutil.copy(template_file, output_file)

    # Replace placeholders in the new file
    with open(output_file, 'r') as file:
        filedata = file.read()

    filedata = filedata.replace('SITENAME', sitename)
    filedata = filedata.replace('SHORTNAME', shortname)
    filedata = filedata.replace('DEVICE', device)

    with open(output_file, 'w') as file:
        file.write(filedata)

    print("Custom file generated successfully!")

    # Update configure.py file
    with open('configure.py', 'r') as config_file:
        config_data = config_file.readlines()

    new_function = f"def RCP_{sitename}_{device}_Configuration():\n"
    new_function += f"    with open('cambium/rcp-{shortname}-{device}-remote.py') as file:\n"
    new_function += f"         exec(file.read())\n"
    new_function += "\n"

    config_data.insert(20, new_function)

    with open('configure.py', 'w') as config_file:
        config_file.writelines(config_data)

# Main function
def main():
    # Step 1: Get site name
    sitename = get_user_input("What is the full site name?")

    # Step 2: Get shortname
    shortname = get_user_input("What is the shortname for the site? Example: Bidyadanga is BID and Tjuntjuntjara is TJN.")
    shortname = format_shortname(shortname)

    # Step 3: Get device
    print("Select the device:")
    template_options = get_template_options()
    for idx, option in enumerate(template_options):
        print(f"{idx+1}. {option}")
    choice = int(input("Enter the number corresponding to the device: ")) - 1
    device = template_options[choice]

    # Generate custom file
    generate_custom_file(sitename, shortname, device)

if __name__ == "__main__":
    main()
