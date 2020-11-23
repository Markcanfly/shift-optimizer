from ortools.sat.python import cp_model
from data import shifts
import json

model = cp_model.CpModel()

# Add data

with open('applications.json', 'r') as datafile:
    preferences = json.load(datafile)

n_shifts = 10
n_people = len(preferences)
# Create empty lists for every person for every shift of every day
shifts = [[[[] for p in range(n_people)] for s in range(n_shifts)] for d in range(7)]


# Create variables 

for d in range(7):
    for s in range(n_shifts):
        for p in range(n_people): # Person ids
            shifts[d][s][p] = model.NewBoolVar(f'Day:{d} Shift:{s} Person:{p}')

#
# Add constraints
# 

#
# Force all vars equal to 0 where the person didn't even put it on their preference list
#
for d in range(7):
    for s in range(n_shifts):
        for p in range(n_people): # Person ids
            try:
                # Try to access preference list. If it's not there, don't even consider it
                preferences[str(p)][str(d)][str(s)]
            except KeyError as e:
                model.Add(shifts[d][s][p] == False)
            
            
# TODO shift capacity

solver = cp_model.CpSolver()
