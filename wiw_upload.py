import argparse
from wheniwork import WhenIWork
import data
import json
from pathlib import Path
import requests
import pickle
import os.path
from dateutil.parser import parse as dtparse
from datetime import datetime as dt

parser = argparse.ArgumentParser()
parser.add_argument('--email')
parser.add_argument('--password')
parser.add_argument('--userid')
parser.add_argument('--apikey')
args = parser.parse_args()

wiwcreds = None
# wiwtoken.pickle stores the WIW token.
# If it exists, assume we've already got a token, and use that to make requests.
if os.path.exists('wiwtoken.pickle'):
    with open('wiwtoken.pickle', 'rb') as wiwtokenfile:
        wiwcreds = pickle.load(wiwtokenfile)

# We've authenticated, time to make requests.

