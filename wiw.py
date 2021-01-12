import argparse
import data
import json
from pathlib import Path
import requests
import pickle
import os.path
from dateutil.parser import parse as dtparse
import datetime

parser = argparse.ArgumentParser()
parser.add_argument('dirpath', help='The path of the directory of the inputsite. This should contain the js file with the shifts.', type=str)
parser.add_argument('urlname', help='The name of the form in the directory.', type=str)
parser.add_argument('solvepath', help='Path to the .json file with the solution.', type=str)
args = parser.parse_args()

wiwcreds = None
# wiwtoken.pickle stores the WIW token.
# If it exists, assume we've already got a token, and use that to make requests.
if os.path.exists('wiwtoken.pickle'):
    with open('wiwtoken.pickle', 'rb') as wiwtokenfile:
        wiwcreds = pickle.load(wiwtokenfile)

if not wiwcreds:
    # No token found, use wiwcreds.json
    with open('wiwcreds.json', 'r') as credsfile:
        wiwcreds = json.load(credsfile)
        response = requests.post(
            'https://api.login.wheniwork.com/login',
            headers={
                "W-Key": wiwcreds['apikey'],
                'content-type': 'application/json'
            },
            data='{"email":"'+wiwcreds['email']+'","password":"'+wiwcreds['password']+'"}',
            
        )
    # If auth was successful, store token
    if response.status_code == 200:
        with open('wiwtoken.pickle', 'wb') as wiwtokenfile:
            pickle.dump(wiwcreds, wiwtokenfile)
    else:
        # Both methods of authentication failed, raise error.
        raise Exception('Unable to authenticate WIW.')

# We've authenticated, time to make requests.

# Build a dict of email:userids for shift assignment
userid = dict()
response = requests.get('https://api.wheniwork.com/2/users', headers={"W-Token": wiwcreds['token']})
if response.status_code == 200:
    users = json.loads(response.text)
    for user in users:
        # userid[user['email']] = user['id']
        userid[user['email']] = 100 # Constant for testing
else:
    raise Exception('Failed to get userlist.')

# WARNING: Non-atomic. This is the reason multiple instances can't run at the same time.
# List shifts to avoid adding duplicates

## Get shiftdata
shifts, prefs, preqs = data.data_from_pageclip(args.dirpath, args.urlname)
## Find timerange to search in
searchbegin = shifts.values()[0]['begintime']
searchend = 0
for shift in shifts.values():
    searchbegin = min(searchbegin, shift['begintime'])
    searchend = max(searchend, shift['endtime'])

## Get list of shifts in timerange
response = requests.get(
    'https://api.wheniwork.com/2/shifts', 
    headers={"W-Token": wiwcreds['token']},
    params={'start':str(searchbegin), 'end':str(searchend)}
    )
if response.status_code == 200:
    onlineshiftsraw = json.loads(response.text)
    onlineshifts = []
    for osr in onlineshiftsraw['shifts']:
        onlineshifts.append(
            {
                'user_id':osr['user_id'], 
                'start_time': dtparse(osr['start_time']).timestamp(),
                'end_time': dtparse(osr['end_time']).timestamp()
            }
        )
else:
    raise Exception('Failed to get existing shifts')

## Add shifts
### List of ids added for optional rollback
shifts_added = []

### Get solver values
solvepath = None
if os.path.exists(f'{args.urlname}-{args.dirpath}/sols/{args.solvepath}'): # Look for solver output folder first
    with open(f'{args.urlname}-{args.dirpath}/sols/{args.solvepath}', 'r', encoding='utf8') as solvefile:
        assignments = data.solve_from_json_compatible(json.load(solvefile))
elif os.path.exists(args.solvepath):
    with open(args.solvepath, 'r', encoding='utf8') as solvefile:
        assignments = data.solve_from_json_compatible(json.loads(solvefile))
else:
    raise FileNotFoundError('Solution JSON file not found.')

assigned = [(d,s,p) for (d,s,p) in assignments.keys() if assignments[d,s,p]]


