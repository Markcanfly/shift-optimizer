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
parser.add_argument('-a', '--revert-on-fail', dest='revert', help='Revert all updates in case one fails.', action='store_true')
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
        local_creds = json.load(credsfile)
        response = requests.post(
            'https://api.login.wheniwork.com/login',
            headers={
                "W-Key": local_creds['apikey'],
                'content-type': 'application/json'
            },
            data='{"email":"'+local_creds['email']+'","password":"'+local_creds['password']+'"}',
        )
        wiwcreds = json.loads(response.text)
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
location_id = None
response = requests.get('https://api.wheniwork.com/2/users', headers={"W-Token": wiwcreds['token']})
if response.status_code == 200:
    rawusers = json.loads(response.text)
    users = rawusers['users']
    if len(rawusers['locations']) <= 1:
        location_id = rawusers['locations'][0]['id'] # Assume we only have one location
    else:
        raise ValueError('Multiple locations found:' + [location['id'] for location in rawusers['locations']])
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
                'user_id': osr['user_id'],
                'location_id': osr['location_id'],
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

shifts_to_add = []
for d,s,p in assigned:
    sdata = {
        'user_id': 100, # TODO after testing set to ID from dict
        'location_id': location_id,
        'start_time': shifts[d,s]['begintime'],
        'end_time': shifts[d,s]['endtime']
    }
    if sdata not in onlineshifts: # Don't create duplicate shift
        shifts_to_add.append(sdata)

failed = []
successful = []
for shift in shifts_to_add: # Upload shifts
    response = requests.post(
        'https://api.wheniwork.com/2/shifts',
        headers={
                "W-Key": wiwcreds['apikey'],
                'content-type': 'application/json'
            },
        data=json.dumps(shift)
    )
    if response.status_code == 200:
        successful.append(response)
    else:
        failed.append((shift,response))
        if args.revert:
            # Revert all successful uploads
            for resp in successful:
                sid = json.loads(resp.text)['shift']['id']
                print(f'Reverting shift with id {sid}...')
                requests.delete(
                    f'https://api.wheniwork.com/2/shifts/{sid}',
                    headers={"W-Key": wiwcreds['apikey']})
            exit(1)

print('Shifts uploaded succesfully:')
for resp in successful:
    sid = json.loads(resp.text)['shift']['id']
    print('    ' + sid)
print('Failed:')
for shift, resp in failed:
    print(f'{shift}[{resp.status_code}] {resp.text}')
