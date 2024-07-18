#*******************************************************************************#
#       Copyright (c) 2017-2022 TraceUp All Rights Reserved.			        #
# 	    Author: Dean (BKeen)                                                    #
#       Date:2023.09.27 v4                                                      #
#*******************************************************************************#

#This script is used for capturing the videos and combining their screenshots.
#The combined screenshots are used to check the camera modules' alignment.

from datetime import datetime
import sys
sys.path.insert(0, r'C:\ffmpeg\bin')

from importlib.resources import read_binary
import paramiko
import time
import datetime
import ffmpeg
import cv2
import numpy as np
import os
import re
from pathlib import Path
import librosa.display
import matplotlib.pyplot as plt
from itertools import compress
import subprocess
import json
import requests
import shutil
import pygsheets

def byte_count( xfer, to_be_xfer):
    print('\rtransferred: {0:.0f} %'.format((xfer / to_be_xfer) * 100),end='')


def SendCameraHTTPCommand(camera, host, cmd):
    print(cmd)

    http = "http://"+ host + ":" + str(camera.httpport) + "/" + cmd
    r = requests.get( http, timeout=5)
    if r.status_code == requests.codes.ok:
        return r.text
    else:
        return None

def SendCommand(cmd):
    stdin, stdout, stderr = client.exec_command(cmd,get_pty=True)
    out,err = stdout.read(),stderr.read()
    # print(out.decode("utf-8"))

def TimeoutCommand(cmd):
    stdin, stdout, stderr = client.exec_command(cmd,timeout=17)
    out,err = stdout.read(),stderr.read()
    # print(out.decode("utf-8"))

def read_frame_by_time(in_file, time, out_file):
    """
    指定時間節點讀取任意幀
    """
    # ffmpeg.global_args( '-loglevel', 'quiet')
    #video = video.global_args(video, "-update")    Gives error: local variable 'video' referenced before assignment
    out, err = (
        ffmpeg.input(in_file, ss=time)
              .output(out_file, vframes=1, loglevel=0)
            #   .global_args('-loglevel', 'quiet')
              .overwrite_output()
              .run()
    )
    return out

def Blur_thresh_score(img_obj):
    # assumes openCV input image object
    img_gray = cv2.cvtColor(img_obj, cv2.COLOR_BGR2GRAY)
    fm_val = cv2.Laplacian(img_gray, cv2.CV_64F).var() # focus measure
    #print(fm_val)
    return fm_val

def ModuleAnalysis():
        print("Running module analysis...")
        usb_r = False
        usb_n = False
        stdin, stdout, stderr = client.exec_command('ifconfig', get_pty=True)
        while line := stdout.readline():
            if "usb_r" in line: usb_r = True
            if "usb_n" in line: usb_n = True
        if usb_r and usb_n: print("\nBoth modules/interfaces up")
        elif not usb_n and not usb_r: print("\nBoth modules/interfaces down")
        elif usb_r and not usb_n: print("\nR module up, N module down")
        elif not usb_r and usb_n: print("\nN module up, R module down")

def checkAudio(cameraID, name):

    # Convert video file to WAV audio format using ffmpeg
    os.system('ffmpeg -i {} -loglevel quiet -acodec pcm_s16le -ar 16000 {} -y'.format(Path(LOCAL_PATH).joinpath(cameraID, name + ".mp4").absolute(), Path(LOCAL_PATH).joinpath(cameraID, name + ".wav").absolute()))

    # Path to the audio file
    audio_path= Path(LOCAL_PATH).joinpath(cameraID, name + ".wav").absolute()

    # Load the audio file as ndarray
    # sr is the audio sample rate. Setting it to None uses the original sample rate. If not specified, the default is 22.05 kHz.
    x,sr=librosa.load(audio_path ,sr=None)
    plt.figure(figsize=(14,5))
    librosa.display.waveshow(x, sr=sr)
    plt.savefig(Path(LOCAL_PATH).joinpath(cameraID, name + ".png").absolute(), dpi=300, bbox_inches='tight')

    if np.max(x) > 0.6:
        npmax = np.max(x)
        print("Has audio - max value: ", np.max(x))
        print("audio is", npmax)
        return True, npmax
    else:
        npmax = np.max(x)
        print("No audio - max value: ", np.max(x))
        print("audio is", npmax)
        return False, npmax

# Global Variable, initialized
avg_misa_pixel = None
median_horiz_diff = None

def combinedVideoImg():
    global avg_misa_pixel, median_horiz_diff

    print("starting function: combinedVideoImg")

    out1 = read_frame_by_time(Path(LOCAL_PATH).joinpath(cameraID, SDA_NAME + ".mp4").absolute(), 5, str(Path(LOCAL_PATH).joinpath(cameraID, SDA_NAME + ".png")))
    out2 = read_frame_by_time(Path(LOCAL_PATH).joinpath(cameraID, SDB_NAME + ".mp4").absolute(), 5, str(Path(LOCAL_PATH).joinpath(cameraID, SDB_NAME + ".png")))

    img1 = cv2.imread(str(Path(LOCAL_PATH).joinpath(cameraID, SDA_NAME + ".png")))
    img2 = cv2.imread(str(Path(LOCAL_PATH).joinpath(cameraID, SDB_NAME + ".png")))

    print("\n")
    print(SDA_NAME, "Sharpness score:", Blur_thresh_score(img1).astype(int))
    print(SDB_NAME, "Sharpness score:", Blur_thresh_score(img2).astype(int))
    bstxt = "blurscore_" + cameraID + ".txt"
    blogtxt = "bscorelog_" + cameraID + ".txt"

    xfactor = str((max(Blur_thresh_score(img1), Blur_thresh_score(img2)) / min(Blur_thresh_score(img1), Blur_thresh_score(img2))).round(decimals=2))

    SDA_audio, SDA_audio_max = checkAudio(cameraID, SDA_NAME)
    SDB_audio, SDB_audio_max = checkAudio(cameraID, SDB_NAME)

    def misalignment_test():
        global avg_misa_pixel, median_horiz_diff

        misaligned_parameter = True

        if SDA_NAME == 'R':
            im1 = img1[:, 2300: -1]
            im2 = img2[:, : 400]
        else:
            im1 = img1[:, : 400]
            im2 = img2[:, 2300: -1]

        cv2.imwrite(str(Path(LOCAL_PATH).joinpath(cameraID, "CroppedImg1" + ".jpeg")), im1)
        cv2.imwrite(str(Path(LOCAL_PATH).joinpath(cameraID, "CroppedImg2" + ".jpeg")), im2)

        sift = cv2.SIFT_create()
        kp1, des1 = sift.detectAndCompute(im1, None)
        kp2, des2 = sift.detectAndCompute(im2, None)

        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=500)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)
        matches = sorted(matches, key=lambda x: x[0].distance)

        ratio_threshold = 0.7
        strong_matches = [m1 for (m1, m2) in matches if m1.distance < ratio_threshold * m2.distance]

        src_pts = np.float32([kp1[m.queryIdx].pt for m in strong_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in strong_matches]).reshape(-1, 1, 2)

        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 10, 0.999)
        matchesMask = mask.ravel().tolist()

        draw_params = dict(matchColor=(0, 255, 0), singlePointColor=(255, 0, 0), matchesMask=matchesMask, flags=2)
        img3 = cv2.drawMatches(im1, kp1, im2, kp2, strong_matches, None, **draw_params)
        cv2.imwrite(str(Path(LOCAL_PATH).joinpath(cameraID, "Match Image" + ".jpeg")), img3)

        hori_diffs = [kp1[m.queryIdx].pt[1] - kp2[m.trainIdx].pt[1] for m in compress(strong_matches, matchesMask)]

        draw_params = dict(matchColor=(0, 255, 0), singlePointColor=(255, 0, 0), flags=cv2.DrawMatchesFlags_DEFAULT)

        img3 = cv2.drawMatches(im1, kp1, im2, kp2, strong_matches, None, **draw_params)
        avg_misalignment_pixel = np.average(hori_diffs)

        avg_misa_pixel = abs(avg_misalignment_pixel)
        median_horiz_diff = abs(np.median(hori_diffs))
        print("Avg Misa Pixel: ", abs(avg_misalignment_pixel))
        print(f'Median of Horiz. Diff: {abs(np.median(hori_diffs))}')
        

        if abs(avg_misalignment_pixel) > 40:
            misaligned_parameter = True
        if abs(np.median(hori_diffs)) > 40:
            misaligned_parameter = True
        if misaligned_parameter:
            shutil.copyfile(Path(LOCAL_PATH).joinpath(cameraID).joinpath('combined.jpeg'), Path("Z:\Misaligned").joinpath(str('combined_' + cameraID + '.jpeg')))

        cv2.imwrite(str(Path(LOCAL_PATH).joinpath(cameraID, "Final Image" + ".jpeg")), img3)

    misalignment_test()

    test_data = [
        f"{SDA_NAME} Sharpness score: {Blur_thresh_score(img1).astype(int)}",
        f"{SDB_NAME} Sharpness score: {Blur_thresh_score(img2).astype(int)}",
        f"Difference Factor: {xfactor}",
        f"{SDA_NAME} GKU ID: {SDA_ID}",
        f"{SDB_NAME} GKU ID: {SDB_ID}",
        f"{SDA_NAME} Audio: {SDA_audio} {SDA_audio_max}",
        f"{SDB_NAME} Audio: {SDB_audio} {SDB_audio_max}",
        f"Avg Misa Pixel: {avg_misa_pixel}",  # Placeholder value
        f"Median of Horiz. Diff: {median_horiz_diff}",  # Placeholder value
        datetime.datetime.now().strftime("%m/%d/%Y %H:%M"),
        f"{cameraID} - {MODTYPE} - V: {voltage}."  
    ]

    # Join test data into a single string with newline characters
    test_data_joined = "\n".join(test_data)

    # Update Google Sheet
    wks = setup_google_sheets()
    #empty_row = len(wks.get_col(1, include_tailing_empty=False)) + 1 # Find the first empty row
    update_google_sheet(wks, cameraID, "Bscore & GKU IDs ⇓", test_data_joined)  # update first empty row with the joined string

    with open(Path(LOCAL_PATH).joinpath(cameraID, str(bstxt)), 'w') as f:
        f.write(SDA_NAME + " Sharpness score: " + str(Blur_thresh_score(img1).astype(int)) + "\n")
        f.write(SDB_NAME + " Sharpness score: " + str(Blur_thresh_score(img2).astype(int)) + "\n")
        f.write("Difference Factor: " + xfactor + "\n")
        f.write(SDA_NAME + " Audio: " + str(SDA_audio) + " " + str(SDA_audio_max) + "\n")
        f.write(SDB_NAME + " Audio: " + str(SDB_audio) + " " + str(SDB_audio_max) + "\n")
        f.write(SDA_NAME + " GKU ID: " + SDA_ID + "\n")
        f.write(SDB_NAME + " GKU ID: " + SDB_ID + "\n")
        f.write(cameraID + " " + MODTYPE)

    with open(Path(LOCAL_PATH).joinpath(cameraID, str(blogtxt)), 'a') as f:
        f.write(datetime.datetime.now().strftime("%m/%d/%Y %H:%M") + "\n")
        f.write(SDA_NAME + " Sharpness score: " + str(Blur_thresh_score(img1).astype(int)) + "\n")
        f.write(SDB_NAME + " Sharpness score: " + str(Blur_thresh_score(img2).astype(int)) + "\n")
        f.write("Difference Factor: " + xfactor + "\n")
        f.write(SDA_NAME + " Audio: " + str(SDA_audio) + " " + str(SDA_audio_max) + "\n")
        f.write(SDB_NAME + " Audio: " + str(SDB_audio) + " " + str(SDB_audio_max) + "\n")
        f.write(SDA_NAME + " GKU ID: " + SDA_ID + "\n")
        f.write(SDB_NAME + " GKU ID: " + SDB_ID + "\n")
        f.write(cameraID + " " + MODTYPE + " V:" + voltage)

    if "N" in SDA_NAME:
        image = np.concatenate([img2, img1], axis=1)
    else:
        image = np.concatenate([img1, img2], axis=1)

    cv2.imwrite(str(Path(LOCAL_PATH).joinpath(cameraID, "combined.jpeg")), image)

    print(datetime.datetime.now().strftime("%m/%d/%Y %H:%M"))
    print(cameraID, " - ", MODTYPE, " - ", "V:" + voltage)
    print("\n")

# Setup Sheet
def setup_google_sheets():
    gc = pygsheets.authorize(service_account_file="Z:\\Nam\\keys\\discharge-analysis-results-2ecd547a74ea.json")
    sh = gc.open_by_key("1LjVewFSjheGKwJpJFdP9sF4OkvICni6YedN8Zg8gfy8")
    wks = sh.worksheet_by_title("HW")
    return wks

# Find the column index for the date column
def find_date_column_index(wks):
    date_header = "HW Date (ctrl+colon) ⇓"
    return find_column_index(wks, date_header)

# Find the index of the column with the given header name
def find_column_index(wks, header_name):
    headers = wks.get_row(1)
    for index, header in enumerate(headers, start=1):
        if header.strip().lower() == header_name.strip().lower():
            return index
    return None

# Get the date from the specified row and column
def get_date_from_sheet(wks, row_index, date_col):
    try:
        date_cell = wks.cell((row_index, date_col))
        date_value = date_cell.value.strip() if date_cell else ""
        
        if not date_value:
            print(f"Empty date value in row {row_index}, column {date_col}.")
            return None
        
        try:
            return datetime.datetime.strptime(date_value, "%m/%d/%Y")
        except ValueError:
            print(f"Invalid date format for value: {date_value}")
            return None
    
    except Exception as e:
        print(f"Error retrieving date from row {row_index}, column {date_col}: {e}")
        return None


def find_column_index(wks, header_name):
    # Get the headers from the first row
    headers = wks.get_row(1)

    # Clean and standardize the headers for comparison
    cleaned_headers = [header.replace('\n', ' ').strip().lower() for header in headers]
    cleaned_header_name = header_name.replace('\n', ' ').strip().lower()

    for index, header in enumerate(cleaned_headers, start=1):
        if header == cleaned_header_name:
            return index
    return None

def find_most_recent_camera_id(wks, camera_id_col, target_camera_id):
    # Find the most recent occurrence of the camera ID starting from the bottom
    camera_ids = wks.get_col(camera_id_col, include_tailing_empty=True)
    for index in range(len(camera_ids) - 1, 0, -1):
        if camera_ids[index].strip() == target_camera_id:
            return index + 1
    return None

# Update sheet with date check
def update_google_sheet(wks, camera_id, header_name, data):
    # Ensure the header name matches the format used in Google Sheets
    camera_id_col = find_column_index(wks, "ID [output]".replace('\n', ' '))
    bscore_col = find_column_index(wks, header_name)
    date_col = find_date_column_index(wks)
    
    if camera_id_col is None or bscore_col is None or date_col is None:
        print(f"One of the required columns 'ID [output]', '{header_name}', or 'HW Date (ctrl+colon) ⇓' not found.")
        return
    
    # Find the most recent row with the given camera ID
    row_index = find_most_recent_camera_id(wks, camera_id_col, camera_id)
    
    if row_index is None:
        print(f"Camera ID '{camera_id}' not found in the column 'ID [output]'.")
        return
    
    # Get the date from the sheet and compare with the current date
    sheet_date = get_date_from_sheet(wks, row_index, date_col)
    current_date = datetime.datetime.now().strftime("%m/%d/%Y")
    
    if sheet_date is None:
        print("Date value is empty or could not be retrieved.")
        return
    
    if sheet_date.strftime("%m/%d/%Y") != current_date:
        print(f"Date mismatch: Sheet date {sheet_date.strftime('%m/%d/%Y')} != Current date {current_date}")
        return
    
    # Update the cell in the Bscore & GKU IDs ⇓ column
    wks.update_value((row_index, bscore_col), data)
    print(f"Updated row {row_index} with data in column '{header_name}'.")


def singleVideoImg(sda_seen, sdb_seen, trace_id, camera):
    print("starting function: singleVideoImg")
    camera_name = camera.name
    img_path = str(Path(LOCAL_PATH).joinpath(trace_id, camera_name + ".jpeg"))
    out = read_frame_by_time(Path(LOCAL_PATH).joinpath(trace_id, camera.name + ".mp4").absolute(), 5, img_path)
    img = cv2.imread(img_path)

    print("\n")
    print(camera.name , "Sharpness score:", Blur_thresh_score(img).astype(int))
    print(camera.name , "GKU ID:", SingleID)

    xfactor="N/A"
    bstxt = "blurscore_" + trace_id + ".txt"
    blogtxt = "bscorelog_" + trace_id + ".txt"

    with open(Path(LOCAL_PATH).joinpath(trace_id, str(bstxt)), 'w') as f:
        f.write(camera_name + " Sharpness score: " + str(Blur_thresh_score(img).astype(int)) + "\n")
        f.write(camera_name + " GKU ID: " + SingleID + "\n")
        f.write(camera_name + " Audio: " + str(SDA_audio) + " " + str(SDA_audio_max))
        f.write("\n" + trace_id + " " + MODTYPE)


    with open(Path(LOCAL_PATH).joinpath(trace_id, str(blogtxt)), 'a') as f:
        f.write("\n\n" + datetime.datetime.now().strftime("%m/%d/%Y %H:%M"))
        f.write("\n" + camera_name + " Sharpness score: " + str(Blur_thresh_score(img).astype(int)))
        f.write("\n" + trace_id + " " + MODTYPE)

    print(datetime.datetime.now().strftime("%m/%d/%Y %H:%M"))
    print(camera_name, "Audio: ", SDA_audio, SDA_audio_max)
    print(trace_id, " - ", MODTYPE)
    print("\n")

def checkCameraExistence(Camera):
    try:
        for i in range(3):
            try:
                # 執行ping指令
                ping_command = f'ping -c 4 -i 0.2 {Camera.ip}'
                stdin, stdout, stderr = client.exec_command(ping_command)
                # 檢查ping的輸出，如果輸出中包含"4 packets transmitted, 4 received"表示連接成功，否則表示連接失敗
                ping_output = stdout.read().decode('utf-8')
                time.sleep(3)
                if " 0%" in ping_output:
                    return True
                else: return False
            except:
                print("Attempt to Connect Again")
                time.sleep(5)
        else: return False
    except:
        SendCommand('sudo shutdown -r now')
        print("\nRESTARTING CAMERA --- PLEASE WAIT 120 SECONDS")
        time.sleep(120)
        tryConnect()


def getCameraFileList(camera):
    for i in range(3):
        try:
            # 執行getList指令
            ping_command = f'python camera_get_filelist.py {camera.ip} root gku88888 /app/sd/'
            stdin, stdout, stderr = client.exec_command(ping_command)

            # 获取副程序的输出
            output = stdout.read().decode()

            file_list  = json.loads(output)
            print(file_list)
            if file_list is []:
                print("file list empty - retrying")
                return False
            return file_list
        except:
            print("error")
    else: return False

def getCameraSN(camera):
    for i in range(3):
        camera_filelist = getCameraFileList(camera)
        for filename in camera_filelist:
            if filename.find("SN.") != -1:
                return re.search('SN.(.*).json', filename).group(1)
            elif re.search('g(.*).json', filename) is not None:
                return 'g' + re.search('g(.*).json', filename).group(1)
        return ""
    else: return False


def downloadCameraFileToTrace(camera, remote_file_path, remote_file_name, trace_path):
    # camera_n_filelist = getCameraFileList(camera)
    try:
        # 執行 python camera_download_file.py 192.168.99.1 root gku88888 /app/sd SN.g22020061.json /home/trace
        ping_command = f'python camera_download_file.py {camera.ip} root gku88888 ' + remote_file_path + " " + remote_file_name + " " + trace_path
        stdin, stdout, stderr = client.exec_command(ping_command)
        print("tried ping command")

        # 获取副程序的输出
        output = stdout.read().decode()
        print("tried decoding output")

        if "Success" in output:
            return True
        if "Fail" in output:
            return False

        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            return True
        else:
            return False

    except:
        return False

def deleteCameraFile(camera, remote_file_path, remote_file_name):
    print("--- deleteCameraFile ---")
    try:
        # 執行 python camera_file_delete.py 192.168.99.1 root gku88888 /app/sd Index.txt
        ping_command = f'python camera_file_delete.py {camera.ip} root gku88888 ' + remote_file_path + " " + remote_file_name
        print(ping_command)
        stdin, stdout, stderr = client.exec_command(ping_command)
        return True
    except:
        return False


def getCameraModuleType(camera):
    downloadCameraFileToTrace(camera, "/app/sd", "caminfo.txt", "/home/trace")
    print("tried downloadCameraFileToTrace") #FAILS HERE
    time.sleep(5)
    sftp.get("/home/trace/caminfo.txt", Path(LOCAL_PATH).joinpath(cameraID, "caminfo_" + camera.name + ".txt"))
    print("tried pulling caminfo file")
    with open(Path(LOCAL_PATH).joinpath(cameraID, "caminfo_" + camera.name + ".txt"), 'r') as file:
        lines = file.readlines()
        for row in lines:
            Mod377 = 'IMX377'
            Mod577 = 'IMX577'
            if row.find(Mod377) != -1:
                MODTYPE = Mod377
                break
            elif row.find(Mod577) != -1:
                MODTYPE = Mod577
                break
            else:
                MODTYPE = 'V100'
        file.close()
        # os.remove(Path(LOCAL_PATH).joinpath(cameraID, "caminfo_" + camera.name + ".txt"))
    print("tried reading caminfo file")
    print("gathering " + camera.name + " caminfo:" + MODTYPE)
    return MODTYPE

def playAudio():
    print("--- Play Audio ---")
    SendCommand('./camcontrol/audioon 1')
    SendCommand('amixer set Headphone 100%')
    SendCommand('aplay -D "plughw:0,0" testAudio.wav')

# read qrcode and hostname (Qrcode : traceX0108)
def tryConnect():
    global voltage, CMD_POWER_OFF,HTTP_CGI_URL,sftp,username, password,hostname_prefix,cameraID,port,client,LOCAL_PATH,SDA_PATH,SDB_PATH,SDA_NAME,SDB_NAME,SDA_ID,SDB_ID,MODTYPE,MODTYPE2,SingleID,name,SDA_audio,SDB_audio,SDA_audio_max,SDB_audio_max,npmax
    username = "trace"
    password = "trace"
    hostname_prefix = ''
    cameraID = 'traceX'
    port = 22
    client = paramiko.SSHClient()
    LOCAL_PATH = Path("Z:\\Nam").joinpath('Videos').absolute() #NEED_LOCAL_PATH
    LOCAL_DIRECTORY = Path("Z:\\Nam")
    SDA_PATH = "N"
    SDB_PATH = "R"
    SDA_NAME = "N"
    SDB_NAME = "R"
    SDA_ID = ""
    SDB_ID = ""
    MODTYPE = ""
    MODTYPE2 = ""
    SingleID = ""
    name="audiotest"
    SDA_audio=False
    SDB_audio=False
    SDA_audio_max=0.0
    SDB_audio_max=0.0
    npmax=0.1
    timeout_seconds=10

    HTTP_CGI_URL =  "cgi-bin/hi3510/"
    CMD_POWER_OFF = HTTP_CGI_URL + "systemset.cgi?-cmd=poweroff"

    class Camera:
        def __init__(self, name, ip, httpport=22, fileport=8080, sn = None, info = None):
            self.name = name
            self.ip = ip
            self.httpport = httpport
            self.fileport = fileport
            self.sn = sn
            self.info = info

        def set_sn(self, sn):
            self.sn = sn

        def set_info(self, info):
            self.info = info


    Camera_N = Camera("N", "192.168.98.1", 6126, 6128)
    Camera_R = Camera("R", "192.168.99.1",6127, 6129)

    try:
        sda_seen=False
        sdb_seen=False
        hostname = hostname_prefix + sys.argv[1]
        print(f'IP:{hostname}')

        # get client
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port, username, password, timeout=timeout_seconds)

        # get sftp
        t = client.get_transport()
        sftp = paramiko.SFTPClient.from_transport(t)


        print("---Put Test Files---")
        sftp.put(os.path.join(LOCAL_DIRECTORY,'camera_get_filelist.py'), '/home/trace/camera_get_filelist.py')
        sftp.put(os.path.join(LOCAL_DIRECTORY,'camera_download_file.py'), '/home/trace/camera_download_file.py')
        sftp.put(os.path.join(LOCAL_DIRECTORY,'camera_file_delete.py'), '/home/trace/camera_file_delete.py')
        sftp.put(os.path.join(LOCAL_DIRECTORY,"testAudio.wav"), 'testAudio.wav')

        time.sleep(10)


        print("---Setting Pi ---")
        SendCommand('/home/trace/camcontrol/microwrite 5 0')
        time.sleep(10)
        SendCommand('/home/trace/camcontrol/microwrite 5 3')
        time.sleep(10)

        SendCommand('sudo iptables -A INPUT -j ACCEPT -m state --state ESTABLISHED,RELATED')
        SendCommand('sudo sysctl -w net.ipv4.ip_forward=1')
        SendCommand('sudo iptables -t nat -I PREROUTING -p tcp -i wlan0 --dport 6124 -j DNAT --to-destination 192.168.98.1:554')
        SendCommand('sudo iptables -t nat -I PREROUTING -p tcp -i wlan0 --dport 6125 -j DNAT --to-destination 192.168.99.1:554')
        SendCommand('sudo iptables -t nat -I POSTROUTING -d 192.168.98.1 -p tcp --dport 554 -j SNAT --to 192.168.98.2')
        SendCommand('sudo iptables -t nat -I POSTROUTING -d 192.168.99.1 -p tcp --dport 554 -j SNAT --to 192.168.99.2')
        SendCommand('sudo iptables -t nat -A PREROUTING -p tcp --dport 6126 -j DNAT --to-destination 192.168.98.1:80')
        SendCommand('sudo iptables -t nat -A PREROUTING -p tcp --dport 6127 -j DNAT --to-destination 192.168.99.1:80')
        SendCommand('sudo iptables -t nat -A PREROUTING -p tcp --dport 6128 -j DNAT --to-destination 192.168.98.1:8080')
        SendCommand('sudo iptables -t nat -A PREROUTING -p tcp --dport 6129 -j DNAT --to-destination 192.168.99.1:8080')
        SendCommand('sudo iptables -t nat -A POSTROUTING -j MASQUERADE')

        time.sleep(10)

        stdin, stdout, stderr = client.exec_command('cat box.id')
        while line := stdout.readline():
            print("TraceXID:" + line, end='')
            cameraID = line.strip()

        #檢查camera在嗎?
        sda_seen = checkCameraExistence(Camera_N)
        sdb_seen = checkCameraExistence(Camera_R)


        if sda_seen and sdb_seen:

            Path(LOCAL_PATH).joinpath(cameraID).mkdir(parents=True, exist_ok=True)

            SDA_ID = getCameraSN(Camera_N)
            SDB_ID = getCameraSN(Camera_R)
            print("SDA_ID:" + SDA_ID)
            print("SDB_ID:" + SDB_ID)

            SDA_NAME = "N"
            SDB_NAME = "R"

            MODTYPE = getCameraModuleType(Camera_N)
            MODTYPE2 = getCameraModuleType(Camera_R)

            if MODTYPE != MODTYPE2:
                MODTYPE = 'MISMATCHED - Please return camera to Repair Team'

            print("--- Start Record Video ---")
            process = subprocess.Popen(["python", os.path.join(LOCAL_DIRECTORY, 'camera_record.py'), hostname, cameraID, "Start_Record"], stdout=subprocess.PIPE) #NEED_LOCAL_PATH
            process.wait()
            time.sleep(6)

            playAudio()

            time.sleep(6)
            print("--- Stop Record Video ---")
            process = subprocess.Popen(["python", os.path.join(LOCAL_DIRECTORY, 'camera_record.py'), hostname, cameraID, "Stop_Record"], stdout=subprocess.PIPE) #NEED_LOCAL_PATH
            process.wait()
            time.sleep(2)
            print("--- Download Record Video ---")
            for i in range (3):
                try:
                    process = subprocess.Popen(["python", os.path.join(LOCAL_DIRECTORY, 'camera_record.py'), hostname, cameraID, "Down_Record"], stdout=subprocess.PIPE) #NEED_LOCAL_PATH
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.terminate()


            deleteCameraFile(Camera_R, "/app/sd", "Index.txt")
            deleteCameraFile(Camera_N, "/app/sd", "Index.txt")

            #Delete persistent files
            print("Deleting persistent files...")
            PersistentFiles = ['/home/trace/module.status','/home/trace/caseinfo.txt','/home/trace/wifi_loss.txt','/home/trace/battery.status',
                               '/home/trace/tarfiles/lowvoltage.log','/home/trace/sport.txt','/home/trace/record.status','/home/trace/fall.time', '/home/trace/camera.settings',
                               '/home/trace/preview.mp4','/home/trace/test.h264']
            for files in PersistentFiles:
                SendCommand('sudo rm -rf ' + files)
                SendCommand('sync')
                time.sleep(1)
            print("Finished deleting persistent files, sending scores...")

            time.sleep(10)

            stdin, stdout, stderr = client.exec_command('/home/trace/camcontrol/battvolt')
            while line := stdout.readline():
                if "battery voltage" in line:
                    voltage = re.search(r"\d+\.\d+", line).group(0)
            print("Battery Voltage:" + voltage)

            time.sleep(3)

            SendCommand('sudo /home/trace/camcontrol/microwrite 5 0')
            
            client.close()
            t.close()

            SDA_audio, SDA_audio_max = checkAudio(cameraID, SDA_NAME)
            SDB_audio, SDB_audio_max = checkAudio(cameraID, SDB_NAME)

            combinedVideoImg() #we can only combine images if both are seen
        elif sda_seen or sdb_seen:
            Path(LOCAL_PATH).joinpath(cameraID).mkdir(parents=True, exist_ok=True)
            #new line added above

            print("NOTE: one camera not working:")
            if sda_seen:
                cam_seen= "sda"
                cam_seen = Camera_N
                print(" sdb not seen")
            else:
                cam_seen="sdb"
                cam_seen = Camera_R
                print(" sda not seen")

            Path(LOCAL_PATH).joinpath(cameraID).mkdir(parents=True, exist_ok=True)
            SingleID = getCameraSN(cam_seen)
            print(SingleID)
            print("trying to getCameraModuleType")
            MODTYPE = getCameraModuleType(cam_seen)

            print("--- Start Record Video ---")
            process = subprocess.Popen(["python", os.path.join(LOCAL_DIRECTORY, 'camera_record.py'), hostname, cameraID, "Start_Record", cam_seen.name], stdout=subprocess.PIPE) #NEED_LOCAL_PATH
            process.wait()
            time.sleep(6)

            playAudio()

            time.sleep(6)
            print("--- Stop Record Video ---")
            process = subprocess.Popen(["python", os.path.join(LOCAL_DIRECTORY, 'camera_record.py'), hostname, cameraID, "Stop_Record", cam_seen.name], stdout=subprocess.PIPE) #NEED_LOCAL_PATH
            process.wait()
            time.sleep(2)
            print("--- Download Record Video ---")
            process = subprocess.Popen(["python", os.path.join(LOCAL_DIRECTORY, 'camera_record.py'), hostname, cameraID, "Down_Record", cam_seen.name], stdout=subprocess.PIPE) #NEED_LOCAL_PATH
            process.wait()

            deleteCameraFile(Camera_N, "/app/sd", "Index.txt")

            #Deletes the module.status file which keeps track of how many "module not seens" a camera has experienced. Deleting this resets the count for refurbishment.
            print("Deleting persistent files...")
            PersistentFiles = ['/home/trace/module.status','/home/trace/caseinfo.txt','/home/trace/wifi_loss.txt','/home/trace/battery.status',
                               '/home/trace/tarfiles/lowvoltage.log','/home/trace/sport.txt','/home/trace/record.status','/home/trace/fall.time', '/home/trace/camera.settings',
                               '/home/trace/preview.mp4','/home/trace/test.h264']
            for files in PersistentFiles:
                SendCommand('sudo rm -rf ' + files)
                SendCommand('sync')
                time.sleep(1)
            print("Finished deleting persistent files, sending scores...")

            time.sleep(10)
            
            ModuleAnalysis()

            time.sleep(3)

            SendCommand('sudo /home/trace/camcontrol/microwrite 5 0')
            client.close()
            t.close()

            SDA_audio, SDA_audio_max = checkAudio(cameraID, cam_seen.name)


            singleVideoImg(sda_seen,sdb_seen,cameraID,cam_seen)

        else:
            print("NOTE: all camera not working:")
            ModuleAnalysis()

    except Exception as e:
        pass
        print(str(e))
        input("\nCaught exception, please address error before pressing enter key to retry.")
        print("Retrying in 3 seconds")
        time.sleep(3)
        tryConnect()


tryConnect()
input("Script ran successfully. Press any key to exit.")
input("Are you sure you want to exit? Press enter three times")
input("One more chance")
input("Goodbye")
time.sleep(1)
