"""Handling of raw data from files"""
import json
import csv
import requests
from requests.auth import HTTPBasicAuth

def filter_unique_ordered(l):
    """Filter a list so that the items are unique.
    When an item appears more than once, the first occurrence will be retained.
    """
    occured = set()
    filtered = []
    for elem in l:
        if elem not in occured:
            occured.add(elem)
            filtered.append(elem)
    return filtered

def shifts_from_json(shift_dict) -> dict:
    """Read the shift data from a json,
    and return it in a solver-compatible format.
    Expects a json structured like such:
        "Hétfő 04.": [
        {
            "capacity": 2,
            "begin": [
                8,
                45
            ],
            "end": [
                16,
                0
            ]
        },...
    Returns:
        dict of sdata[day_id, shift_id] = {
            'capacity': 2,
            'begin': 525,
            'end': 960
        }
    """
    def to_mins(t):
        return t[0]*60 + t[1]

    sdata = dict()

    for day_id, shifts in shift_dict.items():
        for shift_id, shift in enumerate(shifts):
            sdata[day_id,shift_id] = {
                'capacity': shift['capacity'],
                'begin': to_mins(shift['begin']),
                'end': to_mins(shift['end'])
            }
    
    return sdata

def shifts_from_jsonfile(shiftsjson) -> dict:
    """Read the shift data from a json,
    and return it in a solver-compatible format.
    Expects a json structured like such:
        "Hétfő 04.": [
        {
            "capacity": 2,
            "begin": [
                8,
                45
            ],
            "end": [
                16,
                0
            ]
        },...
    Returns:
        dict of sdata[day_id, shift_id] = {
            'capacity': 2,
            'begin': 525,
            'end': 960,
            'begintime': unixtime,
            'endtime': unixtime
        }
    """

    with open(shiftsjson, 'r', encoding='utf8') as jsonfile:
        shift_dict = json.load(jsonfile, )

    return shifts_from_json(shift_dict)

def preferences_from_csv(prefcsv, shiftsjson) -> dict:
    """Read the preference data from a csv, 
    and return it in a solver-compatible format.
    For this it needs to also read the shifts json, to get the day names.
    We expect the day names, and the shifts to be in the same order in both files.
    
    Returns:
        dict of pref[day_id,shift_id,person_id] = pref_score 
    """

    # Find daynames
    unique_daynames = list()
    for day_id, shift_id in shifts_from_json(shiftsjson).keys():
        if day_id not in unique_daynames:
            unique_daynames.append(day_id)

    firstrow = True
    pref = dict()

    with open(prefcsv, "r", encoding='utf8') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in csvreader:
            if firstrow:
                firstrow = False
                continue
            person_id = row[0]
            for day_index, daily_shifts_str in enumerate(row[1:-1]):
                if daily_shifts_str != "": # Pref list for day isn't empty
                    daily_shifts = list(map(int,daily_shifts_str.split(',')))
                    for pref_score, shift_id in enumerate(daily_shifts):
                        pref[unique_daynames[day_index], shift_id, person_id] = pref_score
    
    return pref

def data_from_pageclip(foldername, urlname):
    """Get all necessary data straight from the web
    Expects a webdata.json formatted as such:
    {
    "website": "{INPUTSITE_URL}
    "apikey": "{API_KEY}",
    "groups": {
        "Fulltimer": {
            "long_shifts_only": true
        },
        "Diák": {
            "long_shifts_only": false
        }
        }
    }
    Take care to use the most recent version of entry data from everyone.
    Args:
        urlname: the location
    Returns:
        (shifts, preferences, personal_reqs)
    """
    with open('webdata.json', 'r', encoding='utf8') as webdatafile:
        webdata = json.load(webdatafile)

    # Get shifts from inputsite
    js = requests.get(f'{webdata["website"]}/{foldername}/{urlname}.js').text
    shiftsraw = json.loads(js[js.index('{'):]) # beginning of JSON shifts
    shifts = shifts_from_json(shiftsraw)

    # Find urlname of form
    # Awful blackmagicfuckery, but works for now
    formurlname_begin = js.index('const urlname = "') + len('const urlname = "')
    formurlname_end = js.index('"', formurlname_begin)
    formurlname = js[formurlname_begin:formurlname_end]

    response = requests.get(
        f'https://api.pageclip.co/data/{formurlname}', # Prefdata from pageclip
        auth=HTTPBasicAuth(webdata['pageclip-key'],''),
        headers={'Accept': 'application/vnd.pageclip.v1+json'},
        params={'archived': False} # Don't get archived
    )
    
    # Get prefs & preqs
    rawdata = json.loads(response.text)
    # Time order -> reversed, make sure latest mods are in the system
    rows = [item['payload'] for item in rawdata['data']]

    # Check 
    # For now we need to manually delete the old inputs
    # Because I am unsure of dealing with str timestamps
    pid_count = dict()
    for row in rows:
        pid = row['email']
        if pid not in pid_count:
            pid_count[pid] = 1
        else:
            pid_count[pid] += 1

    duplicate_emails = set()
    for pid, n in pid_count.items():
        if n > 1:
            duplicate_emails.add(pid)
    if len(duplicate_emails) > 0:
        raise ValueError(f"Duplicate email addresses found: {duplicate_emails}")
    
    # Get preferences & personal requirements
    prefscore = dict()
    preqs = dict()
    for row in rows:
        for d in shiftsraw.keys():
            if row['day_prefs'][d] != '': # No prefs for that day
                pref_order = filter_unique_ordered(list(map(int, row['day_prefs'][d].split(","))))
                for pref, shift in enumerate(pref_order):
                    prefscore[d,shift,row['email']] = pref
        preqs[row['email']] = {
            'min': list(map(int, row['hours'].split(',')))[0],
            'max': list(map(int, row['hours'].split(',')))[1],
            'min_long_shifts': webdata['groups'][row['group']]["min_long_shifts"],
            'only_long_shifts': webdata['groups'][row['group']]["long_shifts_only"]
        }
    return (shifts, prefscore, preqs)

def personal_reqs_from_groups(filename) -> dict:
    """Read the group data from a json,
    and return it in a solver-compatible format.
    Make sure it's valid.
    Expects a json structured like:
        "group_name": {
            "people": [
                "p_id1",
                "p_id2",...
            ],
            "min_hours": 25,
            "max_hours": 35,
            "min_long_shifts":1,
            "only_long_shifts": true
        },...
    Returns:
        preqs: preqs[person_id] = {
            'min': n1, 
            'max': n2, 
            'min_long_shifts': n3, 
            'only_long_shifts': bool1
            } dict
    """
    
    with open(filename, 'r', encoding='utf8') as jsonfile:
        groups_raw = json.load(jsonfile)
    
    preqs = dict()

    people_list = [] # For validating that one name is in one group only
    for g in groups_raw.values():
        people_list += g['people'] # For validation
        for person_id in g['people']:
            preqs[person_id] = {
                'min': g['min_hours'], 
                'max': g['max_hours'], 
                'min_long_shifts': g['min_long_shifts'],
                'only_long_shifts': g['only_long_shifts']
                }
    
    if len(set(people_list)) != len(people_list):
        raise ValueError('One or more person_id is assigned to multiple groups.')
    
    return preqs

def hours_for_everyone(preferences, min_hours, max_hours) -> dict:
    """Create an hour specification for all people in the preferences,
    with equal required hours.
    As if there was a single that everybody was part of.
    Returns:
        hours: hours[person_id] = {'min': n1, 'max': n2} dict
    """
    hours = dict()

    people = set([pref[2] for pref in preferences])
    for person in people:
        hours[person] = {
            'min': min_hours,
            'max': max_hours
        }
    
    return hours

def json_compatible_solve(values):
    """Create a JSON-compatible dict from
    a solver values dict.
    Args:
        values: [(day,shift,person)] = True | False
    Returns:
        assigned[day][shift][person] = True | False
    """
    assigned = dict()
    for d,s,p in values.keys():
        if d not in assigned.keys():
            assigned[d] = {s: {p: values[d,s,p]}}
        if s not in assigned[d].keys():
            assigned[d][s] = {p: values[d,s,p]}
        assigned[d][s][p] = values[d,s,p]
    return assigned

def solve_from_json_compatible(jsondict):
    """Create a solver values dict from
    a JSON-converted dict
    Args:
        assigned[day][shift][person] = True | False
    Returns:
        values: [(day,shift,person)] = True | False
    """
    values = dict()
    for d, v1 in jsondict.items():
        for s, v2 in v1.items():
            for p, assigned_status in v2:
                values[d,int(s),p] = assigned_status
    return values

def empty_assignments(shifts, preferences):
    """Generate empty assignments
    Args:
        shifts: dict of sdata[day_id, shift_id] = {
            'capacity': 2,
            'begin': 525,
            'end': 960
        }
        preferences: dict of pref[day_id,shift_id,person_id] = pref_score
    """
    people = sorted(list(set([p for d,s,p in preferences.keys()])))

    assignments = dict()

    for d, s in shifts.keys():
        for p in people:
            assignments[d,s,p] = False
    
    return assignments

def override_preqs(filename, preqs):
    """Use the .json file at the given path to override the personal reqs dict
    Args:
    filename: the JSON file to override with
    preqs: the preqs[person_id] = {
            'min': n1, 
            'max': n2, 
            'min_long_shifts': n3, 
            'only_long_shifts': bool1
            } dict to override
    """
    with open(filename, 'r', encoding='utf8') as jsonfile:
        override = json.load(jsonfile)
    
    for person in override:
        preqs[person] = override[person]
