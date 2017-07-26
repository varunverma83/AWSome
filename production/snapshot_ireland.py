#!/usr/bin/python
import os, sys
import boto3
from account_settings import *

#import the common file
ROOT_PATH = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_PATH, '..')) #up a level to get the files
from settings import *
from common import *

# Create snapshots for Instance volumes
backup_result = snapshotInstanceVolumes(profile=CONST_AWS_PROFILE, 
										region=AwsRegion.IRELAND, 
										account=CONST_AWS_ACCT_NAME)
# Delete snapshots
delete_result = deleteOldSnapshots(profile=CONST_AWS_PROFILE, 
									region=AwsRegion.IRELAND, 
									account=CONST_AWS_ACCT_NAME)
