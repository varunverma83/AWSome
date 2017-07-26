#!/usr/bin/python
import os, sys

#import the common file
ROOT_PATH = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_PATH, '..')) #up a level to get the files
from settings import *
from common import *

reportTags(profile='aws_test_dev',
			account='aws_test_dev')
