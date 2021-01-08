import argparse
import data
import json
from solver import ShiftSolver
import excel
from pathlib import Path
from copy import deepcopy

parser = argparse.ArgumentParser()
parser.add_argument('dirpath', help='The path of the directory of the inputsite. This should contain the js file with the shifts.', type=str)
parser.add_argument('urlname', help='The name of the form in the directory.', type=str)
parser.add_argument('-t', '--timeout', help='The maximum time in seconds that the solver can take to find an optimal solution.', default=10, type=int)
args = parser.parse_args()

# Collect data from files
shifts, prefs, personal_reqs = data.data_from_pageclip(args.dirpath, args.urlname)

solver = ShiftSolver(shifts=shifts, preferences=prefs, personal_reqs=personal_reqs)

sum_capacities = 0
# Calculate the number of capacities total
for shift_props in shifts.values():
    sum_capacities += shift_props['capacity']

starting_capacity = int(sum_capacities*0.75)

Path(args.urlname+'/sols').mkdir(parents=True, exist_ok=True)
rows = [] # {'pref':s1, 'unfilled':s2, 'empty':s3, 'filename':s4}

for n in range(starting_capacity, sum_capacities+1):
    if solver.Solve(
            min_workers=0,
            timeout=args.timeout,
            min_capacities_filled=n):       
        print(f'Prefscore: {solver.ObjectiveValue()} Completely empty shifts: {solver.EmptyShifts()} Unfilled capacities: {solver.UnfilledCapacities()} in {round(solver.WallTime(),2)} seconds', end='')
        if solver.StatusName() != 'OPTIMAL':
            print(' !SUBOPTIMAL SOLVE! Try to run with more time', end='')
        print()
        xlsxsubpath = f'sols/{n}.xlsx'
        xlsxfilepath = f'{args.urlname}/{xlsxsubpath}'
        # Write to excel and add index for the root later
        rows.append((xlsxsubpath, deepcopy(solver)))
        excel.write_to_file(xlsxfilepath, shifts, prefs, solver.Values(), personal_reqs)
    else: # No more solutions to be found
        break

if len(rows) > 0:
    excel.write_summary(f'{args.urlname}/solindex.xlsx', rows)

    
