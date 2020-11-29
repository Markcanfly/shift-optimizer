from ortools.sat.python import cp_model
from data import flat_shifts
from generate_preferences import get_requests
from models import Shift # For IntelliSense
from itertools import combinations
import pickle

class ShiftModel(cp_model.CpModel):
    """Shift solver

    This class takes a list of shifts, 
    and a list of preferenced shift requests.
    Then provides an optimal solution (if one exists)
    for the given parameters.
    """
    def __init__(self, shiftlist, preferences):
        """Args:
            shifts: list of (day_id, shift_id, capacity, from, to) tuples where
            preferences: list of (day_id, shift_id, person_id, pref_score) tuples
        """
        super().__init__()
        self.people = ShiftModel.get_people(preferences)
        self.daily_shifts = ShiftModel.get_daily_shifts(shiftlist)
        self.sdata = ShiftModel.get_shiftdata(shiftlist)
        self.preferences = preferences
        self.variables = {}
        for d, shifts in self.daily_shifts.items():
            for s in shifts:
                for p in self.people:
                    self.variables[(d, s, p)] = self.NewBoolVar(f'Day{d} Shift{s} Person{p}')
        
        self.constraint_pref_only()
        self.constraint_shift_capacity()
        self.constraint_long_shift()
        self.constraint_work_mins(18*60, 22*60)
        self.constraint_no_conflict()
        self.maximize_welfare()

    def constraint_pref_only(self):
        """Make sure that employees only get assigned to a shift
        that they signed up for.
        """
        has_pref = dict() # index
        for d, shifts in self.daily_shifts.items():
            for s in shifts:
                for p in self.people:
                    has_pref[(d,s,p)] = False # default every pref to False
        for pref in self.preferences: # overwrite to two if the employee signed up with any pref score
            has_pref[(pref[0],pref[1],pref[2])] = True

        for (d, s, p) in self.variables.keys():
            if not has_pref[(d,s,p)]:
                self.Add(self.variables[(d, s, p)] == False)

    def constraint_shift_capacity(self):
        """Make sure that there are exactly as many employees assigned
        to a shift as it has capacity.
        """
        for d, shifts in self.daily_shifts.items():
            for s in shifts:
                self.Add(1 <= sum(self.variables[(d, s, p)] for p in self.people))
                self.Add(sum(self.variables[(d, s, p)] for p in self.people) <= self.sdata[(d,s)][0])

    def constraint_work_mins(self, min, max):
        """Make sure that everyone works the minimum number of minutes,
        and no one works too much.
        Args:
            min: the minimum number of minutes
            max: the maximum number of minutes
        """
        mins_of_shift = dict() # calculate shift hours

        for (d,s),(c, begin, end) in self.sdata.items():
            mins_of_shift[(d,s)] = end - begin
        # TODO MAKE THIS CLEANER. This atrocity is ugly, but it works. Figure out how to set upper and lower bounds manually.
        for p in self.people:
            work_mins = 0
            for d, shifts in self.daily_shifts.items():
                for s in shifts:
                    work_mins += self.variables[(d, s, p)] * mins_of_shift[(d,s)]
            self.Add(min < work_mins)
        for p in self.people:
            work_mins = 0
            for d, shifts in self.daily_shifts.items():
                for s in shifts:
                    work_mins += self.variables[(d, s, p)] * mins_of_shift[(d,s)]
            self.Add(work_mins < max)

    def constraint_long_shift(self):
        """Make sure that everyone works at least one long shift.
        """
        long_shifts = set() # find long shifts
        for (d, s), (c, begin, end) in self.sdata.items():
            if end - begin > 5*60: # Number of minutes
                long_shifts.add((d, s))
        
        for p in self.people:
            self.Add(
                sum([self.variables[(d,s,p)] for (d,s) in long_shifts]) > 0
            ) # Any one of these has to be true -> sum > 0

    def constraint_no_conflict(self):
        """Make sure that no one has two shifts on a day that overlap.
        """
        conflicting_pairs = set() # assuming every day has the same shifts
        for ((d1,s1),(c1, b1, e1)), ((d2,s2),(c2, b2,e2)) in combinations(self.sdata.items(), r=2):
            if (d1==d2) and (((b2 < b1 < e2) or (b2 < e1 < e2)) or (((b1 < b2 < e1) or (b1 < e2 < e1)))): # Test conflict
                conflicting_pairs.add((d1,(s1,s2))) # add their ids

        # find pairs of incompatible (day,shift) ids
        for p in self.people:
            for d,(s1,s2) in conflicting_pairs:
                # Both of them can't be true for the same person
                self.Add(self.variables[(d,s1,p)] + self.variables[(d,s2,p)] < 2)

    def maximize_welfare(self):
        pref = dict() # Index preference scores
        for praw in self.preferences:
            pref[(praw[:3])] = praw[3]
        
        for works_id in self.variables.keys():
            if works_id not in pref.keys():
                pref[works_id] = 0

        self.Minimize(
            sum([works*pref[works_id] for works_id, works in self.variables.items()])
        )
        

    @staticmethod
    def get_daily_shifts(shiftlist):
        """Extract a dictionary of shift ids for each day. 
        Args:
            shiftlist: list of (day_id, shift_id, capacity, from, to) tuples
        Returns:
            daily_shifts['day'] = list(shift1_id, shift2_id...)    
        """
        daily_shifts = dict()
        for sraw in shiftlist:
            daily_shifts[sraw[0]] = set() # Initialize with empty sets
        for sraw in shiftlist:
            daily_shifts[sraw[0]].add(sraw[1])

        return daily_shifts

    @staticmethod
    def get_people(preferences):
        """Extract the set of people from a raw shift data list
        Args:
            preferences: list of (day_id, shift_id, person_id, pref_score) tuples
        Returns:
            set of people ids
        """
        people = set()
        for pref in preferences:
            people.add(pref[2])
        return people

    @staticmethod
    def get_days(shiftlist):
        """Extract the set of days from a shiftlist
        Args:
            shiftlist: list of (day_id, shift_id, capacity, from, to) tuples
        Returns:
            set of day ids
        """
        days = set()
        for sraw in shiftlist:
            days.add(sraw[0])
        return days

    @staticmethod
    def get_shifts(shiftlist):
        """Extract the set of shift ids from a shiftlist
        Args:
            shiftlist: list of (day_id, shift_id, capacity, from, to) tuples
        Returns:
            set of shift ids
        """
        shifts = set()
        for shift in shiftlist:
            shifts.add(shift[1])
        return shifts
    
    @staticmethod
    def get_shiftdata(shiftlist):
        """Build a dictionary with the shift data from a shift list.
        Args:
            shiftlist: list of (day_id, shift_id, from, to, capacity) tuples
        Returns:
            dictionary of sdata[(day_id, shift_id)] = (from, to, capacity)
        """
        shiftdata = dict()
        for sraw in shiftlist:
            shiftdata[(sraw[0], sraw[1])] = tuple(sraw[2:])
        return shiftdata

class ShiftSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""
    def __init__(self, model, sols):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._m = model
        self._sols = set(sols)
        self._sol_count = 0

    def count_work_hours(self, person_id):
        work_hours = 0
        for d, shifts in self._m.daily_shifts.items():
            for s in shifts:
                s_hours = (self._m.sdata[(d,s)][2] - self._m.sdata[(d,s)][1]) / 60
                work_hours += self.Value(self._m.variables[d,s,person_id]) * s_hours
        return work_hours

    def on_solution_callback(self):
        for d, shifts in self._m.daily_shifts.items():
            print(f'Day {d}:')
            for s in shifts:
                print(f'    Shift {s}')
                for p in self._m.people:
                    if self.Value(self._m.variables[(d,s,p)]):
                        print(f'        Person {p}')
        print()
        for p in self._m.people:
            print(f"Person {p} works {self.count_work_hours(p)} hours")
        print()
        print(f'Solution #{self._sol_count}')
        self._sol_count += 1

    def solution_count(self):
        return self._sol_count

if __name__ == "__main__":
    with open('pref.pickle', 'rb') as preffile:
        requests = pickle.load(preffile)
    model = ShiftModel(flat_shifts, requests)
    solver = cp_model.CpSolver()
    solver.Solve(model)
    pref = dict() # Index preference scores
    for praw in model.preferences:
        pref[(praw[:3])] = praw[3]
    
    try:
        for d, shifts in model.daily_shifts.items():
            print(f'Day {d}:')
            for s in shifts:
                print(f'    Shift {s}')
                for p in model.people:
                    if solver.Value(model.variables[(d,s,p)]):
                        print(f'        Person {p} with preference {pref[(d,s,p)]}')
            print()
        print(solver.ObjectiveValue())

        for p in model.people:
            work_hours=0
            for d, shifts in model.daily_shifts.items():
                for s in shifts:
                    s_hours = (model.sdata[(d,s)][2] - model.sdata[(d,s)][1]) / 60
                    work_hours += solver.Value(model.variables[d,s,p]) * s_hours
            print(f'{p} works {work_hours} hours.')

    except IndexError:
        print('No solution found.')
# Hint https://developers.google.com/optimization/scheduling/employee_scheduling
# TODO no other shift on long shif day(s)