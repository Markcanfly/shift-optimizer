import argparse
from wheniwork import WhenIWork, NoLoginError
import data
import json
from requests import HTTPError
from pathlib import Path
import pickle
import os.path

parser = argparse.ArgumentParser()
parser.add_argument('filename')
parser.add_argument('--email')
parser.add_argument('--password')
parser.add_argument('--userid')
parser.add_argument('--apikey')
args = parser.parse_args()

tokenfile_path = 'wiwtoken.pickle'

wiwcreds = None
# wiwtoken.pickle stores the WIW token.
# If it exists, assume we've already got a token, and use that to make requests.
if os.path.exists(tokenfile_path):
    with open(tokenfile_path, 'rb') as wiwtokenfile:
        wiwcreds = pickle.load(wiwtokenfile)
else: # Authenticate manually using password
    if None in (args.email, args.password, args.userid, args.apikey):
        raise NoLoginError() # Arguments are not specified
    wiwcreds = WhenIWork.get_token(args.apikey, args.email, args.password)
    wiwcreds['user_id'] = args.userid
    with open(tokenfile_path, 'wb') as wiwtokenfile:
        pickle.dump(wiwcreds, wiwtokenfile)

account_id = wiwcreds['person']['id']

# We've authenticated, time to make requests.
wiw = WhenIWork(wiwcreds['token'], wiwcreds['user_id'])
users = wiw.get_users()
location_id = wiw.get_users()['locations'][0]['id'] # Assume there's just one

# Load shifts to upload
with open(args.filename, 'r') as shiftfile:
    shifts = json.load(shiftfile)

uploaded = []
failed = []

# Upload shifts
for shift in shifts:
    try:
        uploaded_shift = wiw.create_shift(
            location=location_id, 
            start=shift['start_time'], 
            end=shift['end_time'], 
            user_id=shift['user_id'],
            position_id=shift['position_id']
        ) # Create new shift
        uploaded.append((shift, uploaded_shift))
    except HTTPError as e:
        print(str(e))
        failed.append((shift, e))

# Stats
if len(uploaded) > 0:
    print('Successfully uploaded shift ids:')
    for shift, upload in uploaded:
        print(upload['shift']['id'])

if len(failed) > 0:
    print('Failed to upload:')
    for shift, error in failed:
        print(json.dumps(shift)+' Error: '+ str(error))
