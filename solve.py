from ortools.sat.python import cp_model
from data import shifts
from models import Shift # For IntelliSense
import json

# TODO refactor to a single class, that abstracts away this horrifying mess
# it should take in a list of (day_id, shift_id, person_id, pref_score)-s,
# and a list of (day_id, shift_id, beginning, end, capacity)
# and if need be build a dictionary on that, but don't let the end user see that

model = cp_model.CpModel()

# Add data

with open('applications.json', 'r') as datafile:
    preferences = json.load(datafile)

n_shifts = 10
n_people = len(preferences)
# Create empty lists for every person for every shift of every day
applications = [[[[] for p in range(n_people)] for s in range(n_shifts)] for d in range(7)]


# Create variables 

for d in range(7):
    for s in range(n_shifts):
        for p in range(n_people): # Person ids
            applications[d][s][p] = model.NewBoolVar(f'Day:{d} Shift:{s} Person:{p}')

#
# Add constraints
# 

#
# Only add those that are on the preference lists
# (Force all vars equal to 0 where the person didn't even put it on their preference list)
#
for d in range(7):
    for s in range(n_shifts):
        for p in range(n_people): # Person ids
            try:
                # Try to access preference list. If it's not there, don't even consider it
                preferences[str(p)][str(d)][str(s)]
            except KeyError as e:
                model.Add(applications[d][s][p] == False)
            
#
# Add shift capacity constraint for every shift
#
for daily_shifts in shifts:
    for shift in daily_shifts:
        model.Add(sum(applications[shift.day_index][shift.id_]) == shift.capacity)

# Build scheduling upon this
# https://developers.google.com/optimization/scheduling/employee_scheduling

solver = cp_model.CpSolver()
