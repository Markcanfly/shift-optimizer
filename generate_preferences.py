from data import shifts, day_names
from random import sample, randint
from models import Shift
import json

n_people = 70
days = list(range(7))

person_applications = dict() # Dictionary of days of applications

def get_random_shifts(shifts) -> list:
    """Get a list of randomly chosen shifts that don't overlap, 
    in a random order, which will be the preference order.

    Args:
        shifts: list of shift objects
    """
    chosen_shifts = sample(shifts, randint(1,4))

    for chosen_shift in chosen_shifts:
        # For each shift, starting from the beginning,
        # Keep only those, that don't conflict with this shift.
        does_not_conflict = lambda other: not Shift.conflicts(chosen_shift, other)
        filter(does_not_conflict, chosen_shifts)
    
    return chosen_shifts

for person_id in range(n_people):
    application_days = person_applications[person_id] = dict()
    for day_index in sample(days, 3): # Choose 3 random days to apply to
        preferences_for_day = application_days[day_index] = list()
        # Choose a few (randint(1,4)) shifts to apply to
        for pref_score, shift in enumerate(get_random_shifts(shifts[int(day_index)])):
            # add a formatted (int-only) version of the shift to the
            # person[day] dictionary
            preferences_for_day.append((day_index, shift.id_, person_id, pref_score))
if __name__ == "__main__":
    with open('applications.json', 'w') as outfile:
        json.dump(person_applications, outfile, indent=4, sort_keys=True)
