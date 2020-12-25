import argparse
import data
from solver import ShiftSolver
import excel

parser = argparse.ArgumentParser()
parser.add_argument('prefs', help='Name of the csv file containing the user-submitted preferences.', type=str)
parser.add_argument('shifts', help='Name of the json file containing the shifts.', type=str)
parser.add_argument('groups', help='Name of the json file containing the groups', type=str)
parser.add_argument('-t', '--timeout', help='The maximum time in seconds that the solver can take to find an optimal solution.', default=10, type=int)
parser.add_argument('-v', '--verbose', help='Print some extra data about the solution.', action='store_true')
parser.add_argument('-o', dest='outxlsx', help='Output to an excel file.', type=str)
# TODO outfiles
args = parser.parse_args()

# Collect data from files
stuples = data.shifts_from_json(args.shifts)
preftuples = data.preferences_from_csv(args.prefs)

solver = ShiftSolver(shifts=stuples, preferences=preftuples)
for min_workers in (1, 0): 
    if solver.Solve(
        min_workers=min_workers, 
        personal_reqs=data.personal_reqs_from_groups(args.groups),
        timeout=args.timeout
                    ):
        print(solver.get_overview())
        if args.verbose:
            print(f'Unhappiness value: {solver.ObjectiveValue()} (lower is better) in {round(solver.WallTime(), 2)} seconds.')
        
        if args.outxlsx:
            excel.write_to_file(args.outxlsx, stuples, preftuples)

        break
    
