#Made by Alex K from Trace Inc. on 04/10/2024 copyright
#This script processes TraceCam Battery Discharge curves and stores to an image
# The camera should last at least 5 hours or lose nore more than 2mv/min

#usage "python AnalyzeBatteryDischarge.py directory_path_here"
# example "python AnalyzeBatteryDischarge.py /Users/akrause/Downloads/DischargeCurves/"

# python AnalyzeBatteryDischarge.py "C:\Users\Natasha_\Desktop\DischargeCurves" 

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
import os
import sys
import re
import paramiko

# Check if a directory path is provided through command line arguments
if len(sys.argv) > 1:
    directory_path = sys.argv[1]
else:
    print("Please provide a directory path as an argument.")
    sys.exit(1)

# Pattern to match files like 'dischargeX1234.log'
pattern = re.compile(r'dischargeX\d+.*\.log|discharge\.log')

# List to hold matching files
matching_files = []

# Loop through files in the provided directory
for filename in os.listdir(directory_path):
    if pattern.match(filename):
        matching_files.append(filename)

# Replace 'file_path' with the actual path of your file
# file_path = '/Users/akrause/Downloads/DischargeCurves/dischargeX4985.log'
file_path = "C:\\Users\\Natasha_\\Desktop\\DischargeCurves"


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

        hwid = []

        for line in file:
            try:
                parts = line.strip().split(',')
                if len(parts) == 2:  # Ensure there are exactly two columns
                    msec.append(int(parts[0]))
                    milliV.append(int(parts[1]))
                    # hwid.append(current_hwid)
                elif len(parts)>2:
                    print("Skipping Extra Col Lines")
            except ValueError:
                # Handle lines that cannot be converted to integers
                continue

    # Convert lists to a DataFrame
    df_clean = pd.DataFrame({
        'msec': msec,
        'milliV': milliV
       # 'HWID': hwid
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

    # Plotting the cleaned data and the linear fit
    plt.figure(figsize=(10, 6))
    plt.plot(df_clean['minutes'], df_clean['milliV'], label='Discharge Curve')
    plt.plot(df_clean['minutes'], df_clean['fit'], 'r--', label='Linear Fit')
    plt.xlabel(f'Time (minutes) | Total Runtime: {total_runtime:.2f} minutes')
    plt.ylabel(f'Voltage (milliV) | Slope: {slope:.2f} milliV/minute')
    plt.title(f'Battery Discharge Curve with Linear Fit | Camera ID: {current_hwid}')
    plt.legend()
    plt.grid(True)

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
    print(f'Total Runtime: {runtime_hours}')
    print("Slope: {slope}")
    print("Date")

#Runtime,slope,date