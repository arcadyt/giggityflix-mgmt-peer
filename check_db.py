import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'giggityflix_mgmt_peer.v3.settings')
sys.path.insert(0, os.path.abspath('src'))
django.setup()

# Now we can import our models
from giggityflix_mgmt_peer.v3.drive_pool.drive_api.models import PhysicalDrive, Partition

# Query and print all drives
print("===== PHYSICAL DRIVES =====")
drives = PhysicalDrive.objects.all()
for drive in drives:
    print(f"ID: {drive.id}")
    print(f"Manufacturer: {drive.manufacturer}")
    print(f"Model: {drive.model}")
    print(f"Serial: {drive.serial}")
    print(f"Size: {drive.size_bytes} bytes")
    print(f"Filesystem: {drive.filesystem_type}")
    print(f"Detected at: {drive.detected_at}")
    print("-" * 40)

# Query and print all partitions
print("\n===== PARTITIONS =====")
partitions = Partition.objects.all()
for partition in partitions:
    print(f"Mount point: {partition.mount_point}")
    print(f"Physical drive ID: {partition.physical_drive.id}")
    print(f"Physical drive model: {partition.physical_drive.model}")
    print(f"Physical drive manufacturer: {partition.physical_drive.manufacturer}")
    print("-" * 40)

print(f"\nTotal drives: {drives.count()}")
print(f"Total partitions: {partitions.count()}")
