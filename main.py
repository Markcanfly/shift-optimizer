import argparse
import data
from solver import ShiftSolver

parser = argparse.ArgumentParser()
parser.add_argument('prefs', help='Name of the csv file containing the user-submitted preferences.', type=str)
parser.add_argument('shifts', help='Name of the json file containing the shifts.', type=str)
parser.add_argument('minimum_hours', help='The minimum number of work hours for each worker.', type=int)
parser.add_argument('maximum_hours', help='The maximum number of work hours for each worker.', type=int)
parser.add_argument('long_shifts', help='The minimum number of long shifts each person needs to have.', type=int)
# TODO outfiles
args = parser.parse_args()

solver = ShiftSolver(shifts=data.shifts_from_json(args.shifts), preferences=data.preferences_from_csv(args.prefs))
for min_workers in (1, 0): 
    solver.Solve(
    min_workers=min_workers, 
    min_hours=args.minimum_hours, 
    max_hours=args.maximum_hours, 
    min_long_shifts=args.long_shifts
    )
    print(solver.get_overview())
