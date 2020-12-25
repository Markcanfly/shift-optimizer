import argparse
import data
from solver import ShiftSolver

parser = argparse.ArgumentParser()
parser.add_argument('prefs', help='Name of the csv file containing the user-submitted preferences.', type=str)
parser.add_argument('shifts', help='Name of the json file containing the shifts.', type=str)
parser.add_argument('groups', help='Name of the json file containing the groups', type=str)
parser.add_argument('-t', '--timeout', help='The maximum time in seconds that the solver can take to find an optimal solution.', default=10, type=int)
parser.add_argument('-v', '--verbose', help='Print some extra data about the solution.', action='store_true')
# TODO outfiles
args = parser.parse_args()

solver = ShiftSolver(shifts=data.shifts_from_json(args.shifts), preferences=data.preferences_from_csv(args.prefs))
for min_workers in (1, 0): 
    if solver.Solve(
        min_workers=min_workers, 
        groups=data.groups_from_json(args.groups),
        timeout=args.timeout
                    ):
        print(solver.get_overview())
        if args.verbose:
            print(f'Unhappiness value: {solver.ObjectiveValue()} (lower is better) in {round(solver.WallTime(), 2)} seconds.')
        break
    
