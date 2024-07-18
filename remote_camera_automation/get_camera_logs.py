#*******************************************************************************#
#       Copyright (c) 2024 TraceUp All Rights Reserved.                         #
#*******************************************************************************#

# tars and retrieves log files from a camera to the current working directory

import paramiko
from pathlib import Path
import time
from datetime import datetime
import os


# set constants
username = "trace"
password = "trace"
hostname_prefix = '192.168.'
cameraID = 'traceX0168'
port = 22

def byte_count( xfer, to_be_xfer):
    print('\rtransferred: {0:.0f} %'.format((xfer / to_be_xfer) * 100),end='')

def SendCommand(cmd):
    stdin, stdout, stderr = client.exec_command(cmd,get_pty=True)
    out,err = stdout.read(),stderr.read()
    print(out.decode("utf-8"))
    print(err.decode("utf-8"))

# read qrcode and hostname (Qrcode : traceX0108)
try:
    #input cam ID and IP
    cameraID = "trace"
    cameraName = 'X' + str(input('CameraID:'))
    cameraID += cameraName
    print(cameraID)

    #concatenating strings
    cam_log_path = "/home/trace/tarfiles/"
    now = datetime.now()
    cam_log_name = "logs-" + cameraName + '-' + now.strftime("%Y-%m-%d") + ".tar.gz"
    hostname = hostname_prefix + input(f'hostname: {hostname_prefix}')
    print(f'hostname:{hostname}')

    # get client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, port, username, password)
    except Exception as f:
        print(f)

    # get sftp
    t = client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(t)

    # tar files
    client.exec_command('rm ' + cam_log_path + cam_log_name)
    print(f'taring into {cam_log_name}')
    cmd = "cd tarfiles; tar -czf " + cam_log_name + " *.log"
    SendCommand(cmd)
    time.sleep(1)
    print("retrieving...");
    sftp.get(cam_log_path + cam_log_name, os.getcwd() + '\\' + cam_log_name, byte_count)
    print("done")


except Exception as e:
    print(e)
