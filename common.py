#!/usr/bin/python
import socket
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from snapshotLog import *
from settings import *
import sys
import csv

class AwsRegion():
	'''
	Class to define AWS Regions
	'''
	OHIO = 'us-east-2'
	NORTH_VIRGINIA = 'us-east-1'
	NORTH_CALIFORNIA = 'us-west-1'
	OREGON = 'us-west-2'
	MUMBAI = 'ap-south-1'
	SEOUL = 'ap-northeast-2'
	SINGAPORE = 'ap-southeast-1'
	SYDNEY = 'ap-southeast-2'
	TOKYO = 'ap-northeast-1'
	FRANKFURT = 'eu-central-1'
	IRELAND = 'eu-west-1'
	LONDON = 'eu-west-2'
	SAO_PAULO = 'sa-east-1'

	@classmethod
	def all(cls, ):
		return [value for name, value in vars(cls).items()
					if not name.startswith('__')
						and not callable(getattr(cls,name))]

def getHostname():
	'''
	Gets hostname for system
	'''
	return socket.gethostname()

def snapshotInstanceVolumes(profile, region, account):
	'''
	Creates snapshots for the Instance volumes
		a. That have not been backed up within the frequency defined in the global settings file
		b. Imposes a maximum limit of instances that can be backed up in a day (Count/frequency)
	'''
	global CONST_BKP_FREQUENCY

	# Setup connection to the region
	boto3.setup_default_session(profile_name=profile)
	ec2 = boto3.resource('ec2', region_name=region)

	# Get all running instances and snapshot volumes as per the frequency
	filter=[{'Name': 'instance-state-name', 'Values': ['running']}]
	instances = ec2.instances.filter(Filters=filter)
	total_instances = sum(1 for i in instances)
	print 'Total instances: %s' % total_instances
	maxInstancesToBackup = (total_instances / CONST_BKP_FREQUENCY) + 1
	instances_snapshotted = 0
	for i in instances:
		sl = SnapshotLog()
		i_last_ss_time = sl.getLastSnapshotTimeForInstance(i.instance_id)
		ss_cutoff_time = datetime.today() - timedelta(days=CONST_BKP_FREQUENCY)
		i_name = ''
		# Check if tags exist
		if i.tags:
			i_name = getObjectName(i.tags)
		if i_last_ss_time and (i_last_ss_time > ss_cutoff_time):
			print 'Snapshot taken recently on %s. Ignoring instance %s (%s)' % (i_last_ss_time, i_name, i.instance_id)
			continue
		if instances_snapshotted > maxInstancesToBackup:
			break
		i_backup_start_time = datetime.today()
		i_id = i.instance_id
		i_vols = i.volumes.all()
		# Iterate thruogh volumes and snapshot them with the same start timestamp
		for v in i_vols:
			v_name = ''
			v_id = v.volume_id
			v_device = v.attachments[0]['Device']
			v_size = v.size
			v_tags = v.tags
			if v_tags:
				v_name = getObjectName(v_tags)
			v_ss_description = 'Volume %s (%s) attached to %s (%s) as %s' % (v_name, v_id, i_name, i_id, v_device)
			v_ss = createSnapshot(v, v_ss_description)
			copyVolTagsToSS(v_ss, v_tags)
			dict_params = {}
			dict_params['account_name'] = account
			dict_params['region'] = region
			dict_params['instance_id'] = i_id
			dict_params['volume_id'] = v_id
			dict_params['snapshot_id'] = v_ss.id
			dict_params['device'] = v_device
			dict_params['size'] = v_size
			dict_params['backup_start_time'] = i_backup_start_time
			sl = SnapshotLog()
			sl.save(dict_params)
		instances_snapshotted += 1
		print 'All volumes snapshotted for instance %s (%s)' % (i_name, i.instance_id)

def deleteOldSnapshots(profile, region, account):
	'''
	Deletes the snapshots older than the frequency defined in the global settings file
	'''
	global CONST_BKP_FREQUENCY
	# Setup connection to the region
	boto3.setup_default_session(profile_name=profile)
	ec2 = boto3.resource('ec2', region_name=region)

	ss_cutoff_time = datetime.today() - 2*timedelta(days=CONST_BKP_FREQUENCY)
	sl = SnapshotLog()
	oldSnapshots = sl.getSnapshotsToDelete(ss_cutoff_time)
	id_deleted = []
	for dict_ss_data in [d for d in (oldSnapshots or [])]:
		try:
			deleteSnapshot(ec2.Snapshot(dict_ss_data['snapshot_id']))
			print 'Deleted snapshot %s' % (dict_ss_data['snapshot_id'])
			id_deleted.append(dict_ss_data['id'])
		except ClientError as ex:
			if ex.response['Error']['Code'] == 'InvalidSnapshot.NotFound':
				print "Snapshot %s doesn't exist in AWS. May have been manually deleted. No action needed" \
					% dict_ss_data['snapshot_id']
				id_deleted.append(dict_ss_data['id'])
		except Exception as ex:
			import traceback
			print traceback.format_exc()
	if id_deleted:
		print id_deleted
		sl.updateDeletedSnapshots(id_deleted, datetime.today())
	else:
		print 'No snapshots found older than cutoff date that can be deleted'

def setupTags(profile, region, account):
	'''
	Creates all the required tags for all instances and volumes
	'''
	from random import randint

	# Setup connection to the region
	boto3.setup_default_session(profile_name=profile)
	ec2 = boto3.resource('ec2', region_name=region)

	# Get all running instances and snapshot volumes as per the frequency
	filter=[{'Name': 'instance-state-name', 'Values': ['running']}]
	instances = ec2.instances.filter(Filters=filter)
	for i in instances:
		account_name = 'Customer # %d' % randint(1, 50)
		deployment_id = str(randint(124, 2058))
		sfid = str(randint(110019, 193758))
		tags = [{'Key':'ACCOUNT NAME', 'Value':account_name},
				{'Key':'CUSTOMER ID', 'Value':sfid},
				{'Key':'DEPLOYMENT ID', 'Value':deployment_id},
				{'Key':'CREATED BY', 'Value':'varun.verma'},
				]
		createTags(i, tags)
		i_vols = i.volumes.all()
		for v in i_vols:
			createTags(v, tags)

def reportTags(profile, account):
	'''
	Creates all the required tags for all instances and volumes
	'''
	from random import randint

	# Setup connection to the region
	boto3.setup_default_session(profile_name=profile)

	# Create CSV file for instance tag report
	instance_csvfile = open('aws_%s_instance_tags.csv' % account, 'w')
	instance_writer = csv.writer(instance_csvfile, quotechar='"', quoting=csv.QUOTE_MINIMAL)

	# Create CSV file for volume tag report
	volume_csvfile = open('aws_%s_volume_tags.csv' % account, 'w')
	volume_writer = csv.writer(volume_csvfile, quotechar='"', quoting=csv.QUOTE_MINIMAL)

	# Write headers to CSV file
	instance_header = ['region', 'instance_id', 'Name', 'ACCOUNT NAME', 'CUSTOMER ID', 'DEPLOYMENT ID', 'CREATED BY']
	instance_writer.writerow(instance_header)
	volume_header = ['region', 'volume_id', 'volume_name', 'ACCOUNT NAME', 'CUSTOMER ID', 'DEPLOYMENT ID', 'CREATED BY']
	volume_writer.writerow(volume_header)

	for region in AwsRegion.all():
		ec2 = boto3.resource('ec2', region_name=region)

		# Get all tags for instances, volumes and snapshots
		filter=[{'Name': 'instance-state-name', 'Values': ['running']}]
		#instances = ec2.instances.filter(Filters=filter)
		instances = ec2.instances.all()
		total_instances = sum(1 for i in instances)
		print 'Total instances in %s: %s' % (region, total_instances)
		for i in instances:
			name = account_name = customer_id = deployment_id = created_by = None
			tags = i.tags
			for t in [t for t in (tags or [])]:
				if t['Key'] == 'Name':
					name = t['Value']
				elif t['Key'] == 'ACCOUNT NAME':
					account_name = t['Value']
				elif t['Key'] == 'CUSTOMER ID':
					customer_id = t['Value']
				elif t['Key'] == 'DEPLOYMENT ID':
					deployment_id = t['Value']
				elif t['Key'] == 'CREATED BY':
					created_by = t['Value']
			instance_writer.writerow([region, i.instance_id, name, account_name, customer_id, deployment_id, created_by])

			# Get tags for volumes
			i_vols = i.volumes.all()
			# Iterate thruogh volumes and collect tag information
			for v in i_vols:
				name = account_name = customer_id = deployment_id = created_by = None
				tags = v.tags
				for t in [t for t in (tags or [])]:
					if t['Key'] == 'Name':
						name = t['Value']
					elif t['Key'] == 'ACCOUNT NAME':
						account_name = t['Value']
					elif t['Key'] == 'CUSTOMER ID':
						customer_id = t['Value']
					elif t['Key'] == 'DEPLOYMENT ID':
						deployment_id = t['Value']
					elif t['Key'] == 'CREATED BY':
						created_by = t['Value']
				volume_writer.writerow([region, v.volume_id, name, account_name, customer_id, deployment_id, created_by])
	instance_csvfile.close()
	volume_csvfile.close()


def getObjectName(tags):
	'''
	Iterates through the tags of an object and returns value with the 'Name' key
	'''
	name = ''
	# Iterate through multiple tags (key-value pairs)
	for tag in tags:
		# Name of the instance is in a tag with 'Key' as 'Name', e.g. {u'Value': 'frankfurt-test02', u'Key': 'Name'}
		if tag['Key'] == 'Name':
			name = tag['Value']
	return name

def createSnapshot(vol, ss_description):
	'''
	Creates a snapshot with a description for the given volume
	'''
	return vol.create_snapshot(Description=ss_description)

def deleteSnapshot(ss):
	'''
	Deletes the snapshot
	'''
	ss.delete()

def createTags(object, tags):
	'''
	Creates tags with Key:Value for the object
	'''
	return object.create_tags(Tags=tags)

def copyVolTagsToSS(ss, vol_tags):
	'''
	The volume tags are copied over to the snapshot
	'''
	tags = []
	for t in vol_tags:
		if t['Key'] == 'Name':
			tags.append({'Key':'Name', 'Value':'%s-snap' % t['Value']})
		elif t['Key'] == 'ACCOUNT NAME':
			tags.append({'Key':'ACCOUNT NAME', 'Value':t['Value']})
		elif t['Key'] == 'CUSTOMER ID':
			tags.append({'Key':'CUSTOMER ID', 'Value':t['Value']},)
		elif t['Key'] == 'DEPLOYMENT ID':
			tags.append({'Key':'DEPLOYMENT ID', 'Value':t['Value']})
		elif t['Key'] == 'CREATED BY':
			tags.append({'Key':'CREATED BY', 'Value':'Provisioning Automation'})
	createTags(ss, tags)

