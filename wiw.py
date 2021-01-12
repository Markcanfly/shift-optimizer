import argparse
import data
import json
from pathlib import Path
import requests
import pickle
import os.path

# parser = argparse.ArgumentParser()
# args = parser.parse_args()


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
        userid[user['email']] = user['id']


