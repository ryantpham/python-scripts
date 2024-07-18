# Made by Ryan P from Trace Inc. on 6/20/24 copyright
# Modified by Alex K from Trace Inc. on 04/10/2024 copyright
# This script downloads discharge log files from a remote camera system,
# and analyzes the downloaded discharge log files.

import paramiko
import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
import sys
import datetime
import time

# Function to retrieve the hostname from the remote Linux system
def get_hostname(ssh_client):
    try:
        stdin, stdout, stderr = ssh_client.exec_command('hostname')
        hostname = stdout.read().strip().decode('utf-8')
        return hostname
    except Exception as e:
        print(f"Error retrieving hostname: {e}")
        return None

# Function to download the discharge.log file
def download_discharge_log(ip_address, username, password, remote_file_path, local_base_dir):
    port = 22
    try:
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"IP: {ip_address}")
        print("Connecting to the server...")
        ssh.connect(ip_address, port, username, password)
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

        # Remove Trace from hostname
        if camera_id.startswith("Trace"):
            camera_id = camera_id[len("Trace"):]

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
        return local_file_path, local_dir, camera_id
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None

# Function to analyze the discharge.log file
def analyze_discharge_log(directory_path, camera_id):
    # Pattern to match files like 'dischargeX1234.log'
    pattern = re.compile(r'dischargeX\d+.*\.log|discharge\.log')

    # List to hold matching files
    matching_files = []

    # Loop through files in the provided directory
    for filename in os.listdir(directory_path):
        if pattern.match(filename):
            matching_files.append(filename)

    # Initialize lists to hold the processed data
    msec = []
    milliV = []

    # Process the file
    for filelist in matching_files:
        file_path = os.path.join(directory_path, filelist)
        with open(file_path, 'r') as file:
            # Skip the header if the file is not empty
            try:
                next(file)
            except StopIteration:
                print(f"File {filelist} is empty. Skipping.")
                continue
            msec = []
            milliV = []

            # Extract the HWID (e.g., "X1234") from the filename using regular expression
            hwid_match = re.search(r'X\d+', filelist)
            if hwid_match:
                current_hwid = hwid_match.group(0)
            else:
                current_hwid = "Unknown"  # Use a placeholder if the pattern is not found

            for line in file:
                try:
                    parts = line.strip().split(',')
                    if len(parts) == 2:  # Ensure there are exactly two columns
                        msec.append(int(parts[0]))
                        milliV.append(int(parts[1]))
                    elif len(parts) > 2:
                        print("Skipping Extra Col Lines")
                except ValueError:
                    # Handle lines that cannot be converted to integers
                    continue

        # Convert lists to a DataFrame
        df_clean = pd.DataFrame({
            'msec': msec,
            'milliV': milliV
        })

        # Convert msec to minutes
        df_clean['minutes'] = df_clean['msec'] / 60000.0

        # Perform linear regression on the clean data
        slope, intercept, r_value, p_value, std_err = linregress(df_clean['minutes'], df_clean['milliV'])

        # Calculate the linear fit line
        df_clean['fit'] = intercept + slope * df_clean['minutes']

        # Total runtime in minutes
        total_runtime = df_clean['minutes'].iloc[-1]

        # Calculate the runtime in hours based on the slope
        runtime_hours = 10 / abs(slope)

        # Turn off interactive mode
        plt.ioff()

        # Plotting the cleaned data and the linear fit
        plt.figure(figsize=(10, 6))
        plt.plot(df_clean['minutes'], df_clean['milliV'], label='Discharge Curve')
        plt.plot(df_clean['minutes'], df_clean['fit'], 'r--', label='Linear Fit')
        plt.xlabel(f'Time (minutes) | Total Runtime: {total_runtime:.2f} minutes')
        plt.ylabel(f'Voltage (milliV) | Slope: {slope:.2f} milliV/minute')
        plt.title(f'Battery Discharge Curve with Linear Fit | Camera ID: {camera_id}')
        plt.legend()
        plt.grid(True)
        
        # Get the current date and print it
        current_date = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        # Add legend entries for total runtime, slope, and date on the right side
        plt.text(0.98, 0.83, f'Total Runtime: {runtime_hours:.2f} hours', transform=plt.gca().transAxes, verticalalignment='top', horizontalalignment='right')
        plt.text(0.98, 0.78, f"Slope: {slope:.2f} milliV/minute", transform=plt.gca().transAxes, verticalalignment='top', horizontalalignment='right')
        plt.text(0.98, 0.73, f"Date: {current_date}", transform=plt.gca().transAxes, verticalalignment='top', horizontalalignment='right')
        plt.tight_layout()  # Ensures the legend and text do not overlap

        # Creating the filename
        base_filename = os.path.basename(file_path)  # Extracts the filename from the path
        file_location = os.path.dirname(file_path)
        filename_no_ext = os.path.splitext(base_filename)[0]  # Removes the file extension
        new_filename = f"{filename_no_ext}_{abs(slope):.2f}mv_per_min_{runtime_hours:.2f}hrs.png"
        new_filepath = os.path.join(file_location, new_filename)
        # Save the plot
        plt.savefig(new_filepath)

        plt.show()

        # Print the path to the saved plot for reference
        print(f"Plot saved as: {new_filename}")
        print("--- Discharge Log ---")
        print(f"Camera ID: {camera_id}")
        print(f'Total Runtime (hours): {runtime_hours:.2f} hours')
        print(f"Minutes recorded: {total_runtime:.2f} minutes")
        print(f"Slope: {slope:.2f} milliV/minute")
        # Get the current date and print it
        current_date = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        print(f"Date: {current_date}")
        print("--- END ---")
    
# Main script
if __name__ == "__main__":
    # Input IP address
    ip_address = sys.argv[1] #input("Enter ip Address")

    username = 'trace'
    password = 'trace'
    remote_file_path = '/home/trace/tarfiles/discharge.log'  # Path to the specific file
    local_base_dir = r'C:\Users\Natasha_\Desktop\DischargeCurves'  # Adjust Local Path Here

    # Download the discharge.log file
    local_file_path, local_dir, camera_id = download_discharge_log(ip_address, username, password, remote_file_path, local_base_dir)

    if local_file_path and local_dir and camera_id:
        # Analyze the downloaded discharge.log file
        analyze_discharge_log(local_dir, camera_id)
    else:
        print("Failed to download and analyze the discharge.log file.")

    # Keep the terminal open to view output messages
    input("Press any key to exit...")
