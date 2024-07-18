#*******************************************************************************#
#       Copyright (c) 2017-2021 TraceUp All Rights Reserved.			        #
# 	    Author: Hayden Yu                                                       #
#       Date: 7/27/2021			                                                #
#*******************************************************************************#

#This script downloads case/camera log.
#Please enter your S3 credential below to execute

import tarfile as tarfile
from time import sleep
from pathlib import Path
from datetime import datetime, timedelta, date
from pytz import timezone
import boto3
import botocore
import os
import shutil as sh

LOCAL_DIR = str(Path(__file__).parent.joinpath("Log").absolute())

#enter s3 cred below
KEY = ""
SECRET = ""
BUCKET_NAME = "soccer-app-data"
s3 = boto3.client('s3', aws_access_key_id=KEY, aws_secret_access_key=SECRET)
s3_object = boto3.resource('s3')


def download_log(ID):
    flag = False
    #concatenate camera ID with recent dates
    todays_date = date.today()
    s3_path = "trace-data/logs-"+ID+"-"+todays_date.strftime("%Y-%m-%d")+".tar.gz"
    log_name = "logs-"+ID+"-"+todays_date.strftime("%Y-%m-%d")+".tar.gz"
    print(s3_path)
    
    #making local directory for a log
    newpath = LOCAL_DIR+"/"+ID
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    else:
        for file in os.scandir(newpath):
            os.remove(file.path)
    sleep(1)

    #download log from s3 to the directory
    try:
            s3_object.Object(BUCKET_NAME, s3_path).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            # The object does not exist.
            flag = True
            print("log doesn't exist")
        else:
            # Something else has gone wrong.
            raise
    else:
        s3.download_file(BUCKET_NAME, s3_path,
                        newpath+"/"+log_name)
        flag = False
        
    #if the log is 'i' days old
    for i in range(1, 7): #log from the past week
        if flag:
            flag = False
            d = todays_date - timedelta(days=i) 
            temp3 = "trace-data/logs-"+ID+"-"+d.strftime("%Y-%m-%d")+".tar.gz"
            print(temp3)
            try:
                s3_object.Object(BUCKET_NAME, temp3).load()
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "404":
                    # The object does not exist.
                    flag = True
                    print("log doesn't exist")
                else:
                    # Something else has gone wrong.
                    raise
            else:
                temp4 = "logs-"+ID+"-"+d.strftime("%Y-%m-%d")+".tar.gz"
                s3.download_file(BUCKET_NAME, temp3,
                            newpath+"/"+temp4)

    #extract log
    if not flag:
        print('extracting '+ID)

        p = Path(newpath)
        if (p.is_dir()):
            tarfilelist = os.listdir(newpath)
            if(tarfilelist):
                tarpath = newpath + "/" + tarfilelist[0]
                if tarpath.endswith("tar.gz"):
                    tar = tarfile.open(tarpath, "r:gz")
                    tar.extractall(path=newpath)
                    tar.close()
            else:
                print("no file in this folder")
        else:
            print("no such directory")


def main():
    print("enter ID: ")
    ID = input()
    download_log(ID)

if __name__ == "__main__":
    main()



