# Made by Ryan P from Trace Inc. on 6/28/24 copyright
# This script connects to a remote camera system using SSH, navigates to the camcontrol directory,
# runs the ./cleancameras command, and then deletes all files and directories in /home/trace/tarfiles.

import paramiko
import os

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

try:
    # Establish SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to the server...")
    ssh.connect(hostname, port, username, password)
    print("Connected to the server")

    # Get the camera ID (hostname)
    camera_id = get_hostname(ssh)
    if not camera_id:
        print("Could not determine the camera ID.")
        ssh.close()
        exit(1)

    # Navigate to camcontrol directory and run ./cleancameras
    print("Running ./cleancameras...")
    ssh.exec_command('cd /home/trace/camcontrol && ./cleancameras')

    # Remove all files and directories in /home/trace/tarfiles
    print("Deleting files in /home/trace/tarfiles...")
    ssh.exec_command('sudo rm -r /home/trace/tarfiles/*')
    
    ssh.close()
    print("Clean and delete operations completed successfully.")
except Exception as e:
    print(f"An error occurred: {e}")
