"""Handling of raw data from files"""
import json
from typing import Tuple
from typing import List, Dict
from requests.auth import HTTPBasicAuth
from datetime import datetime
import pytz

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

timestamp = int
def datetime_string(ts: timestamp) -> str:
    return datetime.fromtimestamp(int(ts)).isoformat()

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
            'end': 960,
            'begintime': unixtime,
            'endtime': unixtime,
            'position': position_name
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
                'end': to_mins(shift['end']),
                'begintime': shift['begintime'],
                'endtime': shift['endtime'],
                'position': shift['position']
            }
    
    return sdata

def get_days_sorted(shifts: "List[Dict]", timezone) -> list:
    """Takes a dict with items
    {'begin': timestamp}
    and returns sorted list of day ids"""
    days = set()
    for shift in shifts:
        days.add(datetime.fromtimestamp(shift['begin']).astimezone(pytz.timezone(timezone)).date())
    days = list(sorted(days))
    days = [d.day for d in days]
    return days

def shift_dict(rshifts: "List[Dict]", days: "List[str]", timezone: str) -> "Dict[str, int]":
    """Creates the necessary shift dict format
    Arguments:
        rshifts: rshifts
        days: list of ordered day numbers
        timezone: timezone name
    Returns:
        shifts[day, shift] = {cap, begin, end}
    """
    lshifts = {d:[] for d in days} # List of shifts for each day
    for shift in rshifts:
        begin = datetime.fromtimestamp(int(float(shift['begin']))).astimezone(pytz.timezone(timezone))
        end = datetime.fromtimestamp(int(float(shift['end']))).astimezone(pytz.timezone(timezone))
        lshifts[begin.day].append(
            {
                'id': shift['id'],
                'capacity': shift['capacity'],
                'begin': begin.hour * 60 + begin.minute,
                'end': end.hour * 60 + end.minute
            }
        )
    # Sort then add to (day,shift) keyed dict
    shifts = {}
    for day, shiftarray in lshifts.items():
        shiftarray.sort(key=lambda s:s['begin'])
        for shift in shiftarray: # Organize by id
            shifts[day, int(shift['id'])] = {
                'capacity': shift['capacity'],
                'begin': shift['begin'],
                'end': shift['end']
            }
    return shifts

def prefscores(shifts: "Dict[int, int]", users: "Dict") -> "Dict[int, int, int]":
    """
    Arguments:
        shifts: sdata[day, shiftid]
        users: [userdata]
    Returns:
        prefscore[day,shift,person] = int
    """
    prefscore_for_id = {sid:[] for day,sid in shifts.keys()}
    for user in users:
        for sid, pref in user['preferences'].items():
            prefscore_for_id[int(sid)].append((user['email'],pref))
    prefscore = {}
    for day, shift in shifts:
        for person, pref in [elem for elem in prefscore_for_id[shift]]:
            prefscore[day,shift,person] = pref
    return prefscore

def requirements(users: "List[Dict]", min_ratio=0.6) -> "Dict[str]":
    """Get the schedule requirements for this person
    Arguments:
        users: [
            {
                email
                hours_adjusted
                hours_max
                preferences
            }
        ]
        min_ratio: float, ratio of min hours to max hours
    Returns:
        req[userid] = {
            'min': minimum number of hours
            'max': maximum number of hours
            'min_long_shifts': minimum number of long shifts for this person,
            'only_long_shifts': whether this user can only take long shifts
        }
    """ # WARNING highly custom code for Wolt Hungary
    reqs = {}
    for user in users:
        reqs[user['email']] = {
            'min':int(user['hours_adjusted'] * min_ratio) if user['hours_adjusted'] < 40 else 35,
            'max':int(user['hours_adjusted'] if user['hours_adjusted'] > 0 else user['hours_max']),
            'min_long_shifts': 1, # Everybody needs at least one
            'only_long_shifts': user['hours_max'] >= 35
        }
    return reqs

def load_data(data: dict) -> Tuple[dict, dict, dict]:
    """
    Args:
        data: {
            'shifts': [
                {
                    'id': int
                    'begin': timestamp
                    'end': timestamp
                    'capacity': int
                    'position': wiw_id
                }
            ]
            'timezone': tzname
            'users' [
                {
                    'email': str
                    'hours_adjusted': float
                
                    'hours_max': float
                    'wiw_id': wiw_id
                    'preferences': {
                        shiftid: priority
                    }
                }
            ]
        }
    And returns a tuple of
    (
        shifts: dict[dayid, shiftid] = {}
        preferences
        requirements
    )"""
    rshifts = data['shifts']
    rtimezone = data['timezone']
    rusers = data['users']
    days = get_days_sorted(rshifts, rtimezone)
    shifts = shift_dict(rshifts, days, rtimezone)
    prefs = prefscores(shifts, rusers)
    reqs = requirements(rusers)
    return shifts, prefs, reqs

def json_compatible_solve(values: dict, data: dict) -> "dict[list,list]":
    """Create a solution object
    Args:
        values: [(day,shift,person)] = True | False
        data: {
            'shifts': [
                {
                    'id': int
                    'begin': timestamp
                    'end': timestamp
                    'capacity': int
                    'position': wiw_id
                }
            ]
            'timezone': tzname
            'users' [
                {
                    'email': str
                    'hours_adjusted': float
                
                    'hours_max': float
                    'wiw_id': wiw_id
                    'preferences': {
                        shiftid: priority
                    }
                }
            ]
        }
    Returns:
        shifts: [
            {
                user_id: wiw_user_id,
                position_id: wiw_pos_id,
                start_time: datetimestring
                end_time: datetimestring
            }
        ]
    """
    user_wiw_for_email = dict()
    for user in data['users']:
        user_wiw_for_email[user['email']] = user['wiw_id']
    shift_for_id = dict()
    capacity = dict() # capacity for shift id
    for s in data['shifts']:
        shift_for_id[s['id']] = {
            # Capacity is determined by number of shifts in solution
            'start_time': datetime_string(s['begin']),
            'end_time': datetime_string(s['end']),
            'position_id': s['position']
        }
        capacity[s['id']] = s['capacity']
    # Add assigned shifts
    shifts = []
    filled = {k[1]: 0 for k in values.keys()} # n of capacities for shift id
    for (day, shift_id, user_email), assigned in values.items():
        if assigned:
            shift = shift_for_id[shift_id].copy()
            shift['user_id'] = user_wiw_for_email[user_email]
            shifts.append(shift)
            filled[shift_id] += 1
    # Add openshifts
    for shift_id in capacity.keys():
        # Add as many shifts to openshifts as many capacities are unfilled
        for _ in range(capacity[shift_id] - filled[shift_id]):
            shift = shift_for_id[shift_id].copy()
            shift['user_id'] = 0
            shift['is_shared'] = True
            shifts.append(shift)
    return shifts

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
            for p, assigned_status in v2.items():
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
