import argparse
import data
import json
from solver import ShiftSolver
import excel
from pathlib import Path
from copy import deepcopy

parser = argparse.ArgumentParser()
parser.add_argument('file', help='Path to the .json file with the schedule data.')
parser.add_argument('--no-solve', dest='nosolve', help="Don't solve, just create the overview excel.", action='store_true')
parser.add_argument('-t', '--timeout', help='The maximum time in seconds that the solver can take to find an optimal solution.', default=None, type=int)
parser.add_argument('-c', '--capacities', help='The percentage of capacities to fill as a minimum', default=96.0, type=float)
args = parser.parse_args()

# Collect data from files
shifts, prefs, personal_reqs = data.load_file(args.file)

solver = ShiftSolver(shifts=shifts, preferences=prefs, personal_reqs=personal_reqs)

sum_capacities = 0
# Calculate the number of capacities total
for shift_props in shifts.values():
    sum_capacities += shift_props['capacity']

starting_capacity = int(sum_capacities*(args.capacities / 100))

subfolderpath = '.'

Path(subfolderpath+'/sols').mkdir(parents=True, exist_ok=True)
rows = [] # {'pref':s1, 'unfilled':s2, 'empty':s3, 'filename':s4}

if not args.nosolve:
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
            xlsxfilepath = f'{subfolderpath}/{xlsxsubpath}'
            # Write to excel and add index for the root later
            rows.append((xlsxsubpath, deepcopy(solver)))
            excel.write_to_file(xlsxfilepath, shifts, prefs, solver.Values(), personal_reqs)

            with open(f'{subfolderpath}/sols/{n}.json', 'w', encoding='utf8') as jsonfile:
                json.dump(data.json_compatible_solve(solver.Values()), jsonfile, indent=4, ensure_ascii=False)
        

        else: # No more solutions to be found
            break

    if len(rows) > 0:
        excel.write_summary(f'{subfolderpath}/solindex.xlsx', rows)
else: # Nosolve invoked
    excel.write_to_file(f'{subfolderpath}/overview.xlsx', shifts, prefs, data.empty_assignments(shifts, prefs), personal_reqs)


