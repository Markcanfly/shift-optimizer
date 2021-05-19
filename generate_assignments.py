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

with open(args.file, 'r') as f:
    jsondata = json.load(f)
    schedule = data.load_data(jsondata)

solver = ShiftSolver(schedule)

sum_capacities = 0
# Calculate the number of capacities total
for shift in schedule.shifts:
    sum_capacities += shift.capacity

starting_capacity = int(sum_capacities*(args.capacities / 100))

subfolderpath = '.'

Path(subfolderpath+'/sols').mkdir(parents=True, exist_ok=True)
rows = [] # {'pref':s1, 'unfilled':s2, 'empty':s3, 'filename':s4}

if not args.nosolve:
    for n in range(starting_capacity, sum_capacities+1):
        if solver.Solve(
                timeout=args.timeout,
                min_capacities_filled=n):       
            print(f'Prefscore: {solver.ObjectiveValue()} Unfilled capacities: {solver.UnfilledCapacities} in {round(solver.WallTime(),2)} seconds', end='')
            if solver.StatusName() != 'OPTIMAL':
                print(' !SUBOPTIMAL SOLVE! Try to run with more time', end='')
            print()
            filename = f'{n}.json'
            # Write to excel and add index for the root later
            rows.append((filename, deepcopy(solver)))

            with open(f'{subfolderpath}/sols/{n}.json', 'w', encoding='utf8') as jsonfile:
                json.dump(data.json_compatible_solve(solver.Values, jsondata), jsonfile, indent=4, ensure_ascii=False)
        else: # No more solutions to be found
            break
    if len(rows) > 0:
        data.write_report(f'{subfolderpath}/sols/solindex.txt', rows)
