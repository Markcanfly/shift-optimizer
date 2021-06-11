"""Handling of raw data from files"""
import json
from solver import ShiftSolver
from typing import List, Dict, Tuple
from requests.auth import HTTPBasicAuth
from datetime import datetime
from models import Schedule, User, Shift, ShiftPreference
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

def get_shifts(rshifts: List[Dict], timezone: str) -> List[Shift]:
    """Creates the necessary shift dict format
    Arguments:
        rshifts: rshifts
        timezone: timezone name
    Returns:
        list of Shifts
    """
    shifts = list()
    for shift in rshifts:
        begin = datetime.fromtimestamp(int(float(shift['begin']))).astimezone(pytz.timezone(timezone))
        end = datetime.fromtimestamp(int(float(shift['end']))).astimezone(pytz.timezone(timezone))
        shifts.append(
            Shift(
                id=int(shift['id']),
                begin=begin,
                end=end,
                capacity=shift['capacity'],
                position=shift['position']
            )
        )
    return shifts

def get_users(rusers: List[Dict]) -> List[User]:
    """Get the schedule requirements for this person
    Arguments:
        users: [
            {
                email
                hours_adjusted
                hours_max
                preferences
                positions
            }
        ]
        min_ratio: float, ratio of min hours to max hours
    Returns:
        list of users
    """ # WARNING highly custom code for Wolt Hungary
    users = list()
    for user in rusers:
        min_hours = user['hours_adjusted']**0.89 if user['hours_max'] >= 35 else 0.6 * user['hours_adjusted']
        users.append(
            User(
                id=user['email'],
                min_hours=min_hours,
                max_hours=user['hours_adjusted'],
                only_long=(user['hours_max'] >= 35), # Fulltimer or not
                min_long=1,
                positions=user['positions']
            )
        )
    return users

def get_preferences(users: List[User], shifts: List[Shift], rusers: List[dict]) -> List[ShiftPreference]:
    # Index by id
    user = {u.id:u for u in users}
    shift = {s.id:s for s in shifts}
    preferences = []
    for ruser in rusers:
        for rshiftid, priority in ruser['preferences'].items():
            preferences.append(ShiftPreference(
                user=user[ruser['email']],
                shift=shift[int(rshiftid)],
                priority=priority
            ))
    return preferences

def load_data(data: dict) -> Schedule:
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
    Returns:
        Schedule with the associated data"""
    rshifts = data['shifts']
    rtimezone = data['timezone']
    rusers = data['users']
    shifts = get_shifts(rshifts, rtimezone)
    users = get_users(rusers)
    preferences = get_preferences(users, shifts, rusers)
    return Schedule(users,shifts,preferences)

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
                    'positions': [
                        position_id
                    ]
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
    filled = {k: 0 for k in capacity.keys()} # n of capacities for shift id
    for (shift_id, user_email), assigned in values.items():
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

def write_report(filename: str, solutions: List[Tuple[str,ShiftSolver]]):
    """Generate and write to file a report about the several solutions"""
    txt = ''
    for sol_file, sol in solutions:
        txt += f"""----- {sol_file} -----
Capacities filled: {sol.FilledCapacities}/{sol.NCapacities} ({round(sol.FilledCapacities/sol.NCapacities*100,2)}%)
Hours filled: {sol.FilledHours}/{sol.Hours} ({round(sol.FilledHours/sol.Hours*100,2)}%)
Prefscore: {sol.PrefScore}
-------
"""
    with open(filename, 'w', encoding='utf8') as txtfile:
        txtfile.write(txt)