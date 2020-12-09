"""Static data definition for the flat_shifts."""
import json
import csv
# TODO Handle file errors
def preferences_from_csv(filename="data.csv") -> list:
    """Read the preference data from a csv, 
    and return it in a solver-compatible format. 
    
    Returns:
        list of (day_id, shift_id, person_id, pref_score) tuples
    """
    firstrow = True
    preferences = []
    with open(filename, "r", encoding='utf8') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in csvreader:
            if firstrow:
                firstrow = False
                continue
            person_id = row[0]
            for day_id, daily_shifts_str in enumerate(row[1:-1]):
                if daily_shifts_str != "": # Pref list for day isn't empty
                    daily_shifts = list(map(int,daily_shifts_str.split(',')))
                    for pref_score, shift_id in enumerate(daily_shifts):
                        preferences.append((day_id, shift_id, person_id, pref_score))
    return preferences

def shifts_from_json(filename="shifts.json"):
    """Read the shift data from a json,
    and return it in a solver-compatible format.
    Expects a json structured like such:
        "day_title": [
            [capacity, begin_minutes, end_minutes],...
        ],...
    Returns:
        list of (day_id, shift_id, capacity, from_minutes, to_minutes) tuples
    """
    def to_mins(t):
        return t[0]*60 + t[1]

    with open(filename, 'r', encoding='utf8') as jsonfile:
        shift_dict = json.load(jsonfile, )

    flat_shifts = []

    for day, shifts in shift_dict.items():
        for shift_id, shift in enumerate(shifts):
            flat_shifts.append((day, shift_id, shift['capacity'], to_mins(shift['begin']), to_mins(shift['end'])))
    
    return flat_shifts

