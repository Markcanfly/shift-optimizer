import argparse
import data
import json
from solver import ShiftSolver
import excel

parser = argparse.ArgumentParser()
parser.add_argument('prefs', help='Name of the CSV file containing the user-submitted preferences.', type=str)
parser.add_argument('shifts', help='Name of the JSON file containing the shifts.', type=str)
parser.add_argument('groups', help='Name of the JSON file containing the groups', type=str)
parser.add_argument('-t', '--timeout', help='The maximum time in seconds that the solver can take to find an optimal solution.', default=10, type=int)
parser.add_argument('-v', '--verbose', help='Print some extra data about the solution.', action='store_true')
args = parser.parse_args()

# Collect data from files
shifts = data.shifts_from_json(args.shifts)
prefs = data.preferences_from_csv(args.prefs, args.shifts)
personal_reqs = data.personal_reqs_from_groups(args.groups)

solver = ShiftSolver(shifts=shifts, preferences=prefs, personal_reqs=personal_reqs)

sum_capacities = 0
# Calculate the number of capacities total
for shift_props in shifts.values():
    sum_capacities += shift_props['capacity']

starting_capacity = int(sum_capacities*0.7)

for n in range(starting_capacity, sum_capacities+1):
    if solver.Solve(
            min_workers=0, 
            timeout=args.timeout,
            min_capacities_filled=n):
        print(f'Prefscore: {solver.ObjectiveValue()} Completely empty shifts:{solver.get_n_empty_shifts()} Unfilled capacities:{solver.get_n_unfilled_capacities()} in {solver.WallTime()} seconds')
    else:
        break

    
