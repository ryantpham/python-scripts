# Made by Wilson N from Trace Inc. on 7/1/24 copyright
# This script connects to a remote camera system using SSH, navigates to the /home/trace/box.id directory,
# and then updates the box.id content to a desired input.

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

# Input IP address and new content for box.id
hostname = input("Enter the IP address of the camera: ")
port = 22
username = 'trace'
password = 'trace'
new_box_id_content = input("Enter the new content for box.id: ")

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

    # Navigate to the directory and update box.id content
    box_id_path = '/home/trace/box.id'
    print(f"Updating the content of {box_id_path}...")
    command = f'echo "{new_box_id_content}" | sudo tee {box_id_path} > /dev/null'
    ssh.exec_command(command)
    
    ssh.close()
    print("Content of box.id updated successfully.")
except Exception as e:
    print(f"An error occurred: {e}")
