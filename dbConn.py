#!/usr/bin/python

import psycopg2
import psycopg2.extras
import os, sys

#Database Settings
DB_HOST = 'localhost'
DB_DATABASE = 'masterdb'
DB_USER = 'automation'
DB_PASSWORD = 'Acc3ll10nOps!'
DB_CONNECTION_STRING = "host=%s dbname=%s user=%s password=%s" % (DB_HOST, DB_DATABASE, DB_USER, DB_PASSWORD)

dbConn = psycopg2.connect(DB_CONNECTION_STRING)
