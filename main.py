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
parser.add_argument('-o', dest='outjson', help='Output the raw model output to a JSON file.')
parser.add_argument('-x', dest='outxlsx', help='Output to an excel file.', type=str)
args = parser.parse_args()

# Collect data from files
shifts = data.shifts_from_json(args.shifts)
prefs = data.preferences_from_csv(args.prefs, args.shifts)
personal_reqs = data.personal_reqs_from_groups(args.groups)

solver = ShiftSolver(shifts=shifts, preferences=prefs, personal_reqs=personal_reqs)
for min_workers in (1, 0): 
    if solver.Solve(
        min_workers=min_workers, 
        timeout=args.timeout
                    ):
        print(solver.get_overview())
        if args.verbose:
            print(f'Unhappiness value: {solver.ObjectiveValue()} (lower is better) in {round(solver.WallTime(), 2)} seconds.')
        if args.outjson:
            with open(args.outjson, 'w', encoding='utf8') as jsonfile:
                json.dump(data.json_compatible_solve(solver.get_values()), jsonfile, indent=4, ensure_ascii=False)
        
        if args.outxlsx:
            assignments = solver.get_values()
            excel.write_to_file(args.outxlsx, shifts, prefs, assignments, personal_reqs)

        break
    
