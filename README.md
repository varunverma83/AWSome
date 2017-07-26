# AWSome
Automate AWS Snapshots for Volumes (by instance)

This project would help you take backups of your AWS Volumes automatically if you can setup a scheduler to invoke the scripts. As part of configuration in the settings file, you can define the number of backups you would want to keep and the frequency of taking the backups. By frequency - I do not mean the frequency of the cron job. As an example, say you have 90 volumes in AWS but you don't want to back them every day (you can do so if you set the frequency to 1). But if you define the frequency to 3, then every volume will be backed up every 3rd day or in other words, 1/3rd of the volumes will be backed up every day when the job runs. That ways you are not overloading the system and you will have a snapshot that is 3-6 days old or 1-4 days old.

1. The setup requires a PostgreSQL database with the following schema to store the snapshot information:

CREATE TABLE public.aws_ec2_boto_snapshot
	(
	id    			  SERIAL NOT NULL,
	account_name      VARCHAR (50),
	region            VARCHAR (50),
	instance_id       VARCHAR (50),
	volume_id         VARCHAR (50),
	snapshot_id       VARCHAR (50),
	device            VARCHAR (50),
	size              INTEGER,
	backup_start_time TIMESTAMP,
	backup_end_time   TIMESTAMP,
	deletion_time     TIMESTAMP
	)
	WITH (OIDS = FALSE);

2. Install the necessary drivers for PostgreSQL and psycopg2

3. Create a credentials file under ~/.aws/credentials that looks like this:

[operations]
aws_access_key_id = ABCXYZ
aws_secret_access_key = abcxyz

[production]
aws_access_key_id = OPQRST
aws_secret_access_key = ghijkl

4. The process also copies certain tags from the volume to snapshot and creates some tags of it's own. e.g. "ACCOUNT NAME", "CUSTOMER ID", "DEPLOYMENT ID", "CREATED BY". You can modify this part of the code to suit your needs.
