#!/usr/bin/python
import traceback
from settings import *
from dbConn import *

class SnapshotLog(object):
	'''
	Class to manage the Snapshot DB logs
	'''

	def save(self, dict_params):
		'''
		Save new Snapshot log information to DB
		'''
		global dbConn
		cur = dbConn.cursor()

		account_name = dict_params['account_name']
		region = dict_params['region']
		instance_id = dict_params['instance_id']
		volume_id = dict_params['volume_id']
		snapshot_id = dict_params['snapshot_id']
		device = dict_params['device']
		size = dict_params['size']
		backup_start_time = dict_params['backup_start_time']

		try:
			qInsert = """INSERT INTO aws_ec2_boto_snapshot(account_name, region, 
							instance_id, volume_id, snapshot_id, device, size, backup_start_time)
							VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
						"""
			cur.execute(qInsert, (account_name, region, instance_id, volume_id, 
				snapshot_id, device, size, backup_start_time))
			dbConn.commit()
		except:
			print "An exception of type {0} occurred. Arguments:\n{1!r}".format(type(ex).__name__, ex.args)
			dbConn.rollback()

	def getLastSnapshotTimeForInstance(self, instance_id):
		'''
		Gets the last snapshot timestamp for the InstanceID
		Returns None if no current snapshot exists for instance volumes
		'''
		global dbConn
		cur = dbConn.cursor(cursor_factory = psycopg2.extras.DictCursor)
		
		qSelect = """SELECT backup_start_time 
						FROM aws_ec2_boto_snapshot 
						WHERE instance_id = %s
							AND deletion_time IS NULL
						ORDER BY id DESC LIMIT 1
					"""
		cur.execute(qSelect, [instance_id])
		results = cur.fetchall()
		if results:
			return results[0]['backup_start_time']
		else:
			return None

	def getSnapshotsToDelete(self, cutoff_time):
		'''
		Gets the active snapshots older than the cutoff_time and greater than backup limit
		'''
		global CONST_NUM_BKPS_TO_KEEP
		global dbConn
		cur = dbConn.cursor(cursor_factory = psycopg2.extras.DictCursor)

		ss_to_delete = []
		# Get volumes that have more than 2 snapshots
		qSelect = """SELECT volume_id, count(*)
						FROM aws_ec2_boto_snapshot 
						WHERE deletion_time IS NULL
						GROUP BY volume_id
						HAVING count(*) > %s;
					"""
		cur.execute(qSelect, [CONST_NUM_BKPS_TO_KEEP])
		vol_results = cur.fetchall()
		for row in vol_results:
			# Remove the oldest snapshot from the volumes above
			qSelect = """SELECT id, snapshot_id, backup_start_time FROM aws_ec2_boto_snapshot
							WHERE volume_id = %s
							ORDER BY backup_start_time DESC
							OFFSET %s
						"""
			cur.execute(qSelect, (row['volume_id'], CONST_NUM_BKPS_TO_KEEP))
			ss_results = cur.fetchall()
			for row in ss_results:
				if row['backup_start_time'] < cutoff_time:
					ss_to_delete.append({'id':row['id'], 'snapshot_id':row['snapshot_id']})

		return ss_to_delete

	def updateDeletedSnapshots(self, ss_id_deleted, deletion_time):
		'''
		Updates the deletion time for snapshots in the DB
		'''
		global dbConn
		cur = dbConn.cursor()

		try:
			qUpdate = """UPDATE aws_ec2_boto_snapshot
							SET deletion_time = %s
							WHERE id = ANY(%s)
						"""
			cur.execute(qUpdate, (deletion_time, ss_id_deleted))
			dbConn.commit()
		except Exception as ex:
			print "An exception of type {0} occurred. Arguments:\n{1!r}".format(type(ex).__name__, ex.args)
			dbConn.rollback()

