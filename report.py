from solver import ShiftModel, ShiftSolver
from data import from_csv, flat_shifts

if __name__ == "__main__":
    requests = from_csv()
    parameters = {
        'hours_goal': 20,
        'min_workers': (1, 0),
        'hours_goal_deviances': range(0,4)
    }
    solver = ShiftSolver(flat_shifts, requests)
    solver.Solve(parameters)
    # TODO write to file
