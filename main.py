import argparse
import data
import json
from solver import ShiftSolver

parser = argparse.ArgumentParser()
parser.add_argument('prefs', help='Name of the CSV file containing the user-submitted preferences.', type=str)
parser.add_argument('shifts', help='Name of the JSON file containing the shifts.', type=str)
parser.add_argument('groups', help='Name of the JSON file containing the groups', type=str)
parser.add_argument('-t', '--timeout', help='The maximum time in seconds that the solver can take to find an optimal solution.', default=10, type=int)
parser.add_argument('-v', '--verbose', help='Print some extra data about the solution.', action='store_true')
parser.add_argument('-o', dest='outjson', help='Output the raw model output to a JSON file.')
args = parser.parse_args()

solver = ShiftSolver(shifts=data.shifts_from_json(args.shifts), preferences=data.preferences_from_csv(args.prefs))
for min_workers in (1, 0): 
    if solver.Solve(
        min_workers=min_workers, 
        personal_reqs=data.personal_reqs_from_groups(args.groups),
        timeout=args.timeout
                    ):
        print(solver.get_overview())
        if args.verbose:
            print(f'Unhappiness value: {solver.ObjectiveValue()} (lower is better) in {round(solver.WallTime(), 2)} seconds.')
        if args.outjson:
            with open(args.outjson, 'w', encoding='utf8') as jsonfile:
                json.dump(data.json_compatible_solve(solver.get_values()), jsonfile, indent=4, ensure_ascii=False)

        break
    
