"""Static data definition for the flat_shifts."""
import json
from models import Shift, Time
import csv

day_names = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap']

shifts = [
    Shift(0, 0, beginning=Time(8, 45), end=Time(16,00)),
    Shift(1, 0, beginning=Time(11, 00), end=Time(15,00), capacity=2),
    Shift(2, 0, beginning=Time(12, 00), end=Time(17,00)), 
    Shift(4, 0, beginning=Time(11, 30), end=Time(14,00)),
    Shift(5, 0, beginning=Time(17, 00), end=Time(22,00)), 
    Shift(6, 0, beginning=Time(18, 00), end=Time(21,30)), 
    Shift(7, 0, beginning=Time(17, 00), end=Time(23,45)),

    Shift(0, 1, beginning=Time(8, 45), end=Time(16,00)),
    Shift(1, 1, beginning=Time(11, 00), end=Time(15,00), capacity=2),
    Shift(2, 1, beginning=Time(12, 00), end=Time(17,00)), 
    Shift(4, 1, beginning=Time(11, 30), end=Time(14,00)),
    Shift(5, 1, beginning=Time(17, 00), end=Time(22,00)), 
    Shift(6, 1, beginning=Time(18, 00), end=Time(21,30)), 
    Shift(7, 1, beginning=Time(17, 00), end=Time(23,45)),

    Shift(0, 2, beginning=Time(8, 45), end=Time(16,00)),
    Shift(1, 2, beginning=Time(11, 00), end=Time(15,00), capacity=2),
    Shift(2, 2, beginning=Time(12, 00), end=Time(17,00)), 
    Shift(4, 2, beginning=Time(11, 30), end=Time(14,00)),
    Shift(5, 2, beginning=Time(17, 00), end=Time(22,00)), 
    Shift(6, 2, beginning=Time(18, 00), end=Time(21,30)), 
    Shift(7, 2, beginning=Time(17, 00), end=Time(23,45)),

    Shift(0, 3, beginning=Time(8, 45), end=Time(16,00)),
    Shift(1, 3, beginning=Time(11, 00), end=Time(15,00), capacity=2),
    Shift(2, 3, beginning=Time(12, 00), end=Time(17,00)), 
    Shift(4, 3, beginning=Time(11, 30), end=Time(14,00)),
    Shift(5, 3, beginning=Time(17, 00), end=Time(22,00)), 
    Shift(6, 3, beginning=Time(18, 00), end=Time(21,30)), 
    Shift(7, 3, beginning=Time(17, 00), end=Time(23,45)),

    Shift(0, 4, beginning=Time(8, 45), end=Time(16,00)),
    Shift(1, 4, beginning=Time(11, 00), end=Time(15,00), capacity=2),
    Shift(2, 4, beginning=Time(12, 00), end=Time(17,00)), 
    Shift(4, 4, beginning=Time(11, 30), end=Time(14,00)),
    Shift(5, 4, beginning=Time(17, 00), end=Time(22,00)), 
    Shift(6, 4, beginning=Time(18, 00), end=Time(21,30)), 
    Shift(7, 4, beginning=Time(17, 00), end=Time(23,45)),

    Shift(0, 5, beginning=Time(8, 45), end=Time(16,00)),
    Shift(1, 5, beginning=Time(11, 00), end=Time(15,00)),
    Shift(2, 5, beginning=Time(12, 00), end=Time(17,00)), 
    Shift(5, 5, beginning=Time(17, 00), end=Time(22,00)), 
    Shift(6, 5, beginning=Time(18, 00), end=Time(21,30), capacity=2), 
    Shift(7, 5, beginning=Time(17, 00), end=Time(23,45)),

    Shift(0, 6, beginning=Time(8, 45), end=Time(16,00)),
    Shift(1, 6, beginning=Time(11, 00), end=Time(15,00)),
    Shift(2, 6, beginning=Time(12, 00), end=Time(17,00)), 
    Shift(5, 6, beginning=Time(17, 00), end=Time(22,00)), 
    Shift(6, 6, beginning=Time(18, 00), end=Time(21,30), capacity=2), 
    Shift(7, 6, beginning=Time(17, 00), end=Time(23,45)),
]

flat_shifts = []

def from_csv(filename="data.csv") -> list:
    """Read the preference data from a csv, 
    and return it in a solver-compatible format. 
    
    Returns:
        list of (day_id, shift_id, person_id, pref_score) tuples
    """
    firstrow = True
    preferences = []
    with open(filename, "r") as csvfile:
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

for s in shifts:
    begin = s.beginning.time # in minutes
    end = s.end.time
    flat_shifts.append((s.day_index, s.id_, s.capacity, begin, end))
if __name__ == "__main__":
    # output to file
    shift_dict = dict()
    for s in flat_shifts: # Index
        shift_dict[day_names[s[0]]] = list()

    for s in flat_shifts:
        shift_dict[day_names[s[0]]].append(s)
    
    with open('shifts.json', 'w', encoding='utf8') as jsonfile:
        json.dump(shift_dict, jsonfile, indent=4, ensure_ascii=False)
