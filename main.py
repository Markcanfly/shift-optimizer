import argparse
import data
from solver import ShiftSolver

parser = argparse.ArgumentParser()
parser.add_argument('prefs', help='Name of the csv file containing the user-submitted preferences.', type=str)
parser.add_argument('shifts', help='Name of the json file containing the shifts.', type=str)
parser.add_argument('target_hours', help='The number of hours to set as goal', type=int)
parser.add_argument('hours_deviance', help="The maximum number of hours an employees weekly work hours can deviate.", type=int)
parser.add_argument('long_shifts', help='The minimum number of long shifts each person needs to have.', type=int)
parser.add_argument('timeout', help='The maximum time to look for the optimal solution, in seconds. Defaults to 10.', type=int, default=10)
# TODO outfiles
args = parser.parse_args()

solver = ShiftSolver(shifts=data.shifts_from_json(args.shifts), preferences=data.preferences_from_csv(args.prefs))
if solver.Solve(
        hours_goal=args.target_hours,
        min_workers=(1, 0),
        hours_goal_deviances=range(1,args.hours_deviance+1),
        pref_function= lambda x: x,
        min_long_shifts= args.long_shifts,
        timeout=args.timeout
        ):
    print(solver.get_overview())
