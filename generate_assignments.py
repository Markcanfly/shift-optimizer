import argparse
import data
import json
from solver import ShiftSolver
import excel
from pathlib import Path
from copy import deepcopy

parser = argparse.ArgumentParser()
parser.add_argument('prefs', help='Name of the CSV file containing the user-submitted preferences.', type=str)
parser.add_argument('shifts', help='Name of the JSON file containing the shifts.', type=str)
parser.add_argument('groups', help='Name of the JSON file containing the groups', type=str)
parser.add_argument('outpath', help='Name of the folder to put the assignments, and the file to generate the indexes in.', type=str)
parser.add_argument('-w', dest='min_workers_per_shift', help='Minimum workers on all shifts. Warning: this will massively increase the time taken to find solutions.', default=0, type=int)
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

Path(args.outpath+'/sols').mkdir(parents=True, exist_ok=True)
rows = [] # {'pref':s1, 'unfilled':s2, 'empty':s3, 'filename':s4}

for n in range(starting_capacity, sum_capacities+1):
    if solver.Solve(
            min_workers=args.min_workers_per_shift, 
            timeout=args.timeout,
            min_capacities_filled=n):       
        print(f'Prefscore: {solver.ObjectiveValue()} Completely empty shifts: {solver.EmptyShifts()} Unfilled capacities: {solver.UnfilledCapacities()} in {round(solver.WallTime(),2)} seconds', end='')
        if solver.StatusName() != 'OPTIMAL':
            print(' !SUBOPTIMAL SOLVE! Try to run with more time', end='')
        print()
        xlsxsubpath = f'sols/{n}.xlsx'
        xlsxfilepath = f'{args.outpath}/{xlsxsubpath}'
        # Write to excel and add index for the root later
        rows.append((xlsxsubpath, deepcopy(solver)))
        excel.write_to_file(xlsxfilepath, shifts, prefs, solver.Values(), personal_reqs)
    else: # No more solutions to be found
        break

if len(rows) > 0:
    excel.write_summary(f'{args.outpath}.xlsx', rows)

    
