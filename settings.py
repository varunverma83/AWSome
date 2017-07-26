#!/usr/bin/python

# 'n' days between which the backups within a region would be split (1/'n' backups taken every day)
CONST_BKP_FREQUENCY = 3
# Number of snapshots that will exists for a volume before the deletion process deletes them
CONST_NUM_BKPS_TO_KEEP = 2
