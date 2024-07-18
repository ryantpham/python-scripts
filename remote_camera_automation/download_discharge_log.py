# Made by Ryan P from Trace Inc. on 6/20/24 copyright
# This script downloads discharge log files from a remote camera system.
# It connects to the camera using SSH, identifies the camera ID,
# creates a local directory based on the camera ID, and downloads 
# the discharge.log file to this local directory.

import paramiko
import os
import re

# Function to retrieve the hostname from the remote Linux system
def get_hostname(ssh_client):
    try:
        stdin, stdout, stderr = ssh_client.exec_command('hostname')
        hostname = stdout.read().strip().decode('utf-8')
        return hostname
    except Exception as e:
        print(f"Error retrieving hostname: {e}")
        return None

# Input IP address
hostname = input("Enter the IP address of the camera: ")
port = 22
username = 'trace'
password = 'trace'
remote_file_path = '/home/trace/tarfiles/discharge.log'  # Path to the specific file
local_base_dir = r'C:\Users\Natasha_\Desktop\DischargeCurves' # Local Path

try:
    # Establish SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to the server...")
    ssh.connect(hostname, port, username, password)
    print("Connected to the server")

    # Use SFTP to download the specific file
    sftp = ssh.open_sftp()
    
    # Get the camera ID (hostname)
    camera_id = get_hostname(ssh)
    if not camera_id:
        print("Could not determine the camera ID.")
        sftp.close()
        ssh.close()
        exit(1)
    
    # Create local directory structure
    local_dir = os.path.join(local_base_dir, camera_id)
    os.makedirs(local_dir, exist_ok=True)

    # Path for the downloaded file
    local_file_path = os.path.join(local_dir, 'discharge.log')

    # Download the specific file
    sftp.get(remote_file_path, local_file_path)
    
    sftp.close()
    ssh.close()
    print(f'Discharge log downloaded to {local_file_path}')
except Exception as e:
    print(f"An error occurred: {e}")
