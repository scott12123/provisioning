import sys

if len(sys.argv) < 2:
    print("Missing parameters")
    sys.exit(1)

# Split the CSV line passed as a single string
fields = sys.argv[1].split(',')

try:
    name, ip = fields
except ValueError:
    print("Expected 4 fields: name, ip")
    sys.exit(1)

# Now use them
print(f"Configuring device:")
print(f"Community: {name}")
print(f"IP: {ip}")
print("end")
# You can now use these variables however you like
