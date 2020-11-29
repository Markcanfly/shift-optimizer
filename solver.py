from ortools.sat.python import cp_model
from data import flat_shifts
from generate_preferences import get_requests
from models import Shift # For IntelliSense
from itertools import combinations

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
        self.shifts = ShiftModel.get_shifts(shiftlist)
        self.days = ShiftModel.get_days(shiftlist)
        self.sdata = ShiftModel.get_shiftdata(shiftlist)
        self.preferences = preferences
        self.variables = {}
        for d in self.days:
            for s in self.shifts:
                for p in self.people:
                    self.variables[(d, s, p)] = self.NewBoolVar(f'Day{d} Shift{s} Person{p}')
        self.constraint_pref_only()
        self.constraint_shift_capacity()
        #self.constraint_work_mins(5*60, 35*60)
        #self.constraint_long_shift()

    def constraint_pref_only(self):
        """Make sure that employees only get assigned to a shift
        that they signed up for.
        """
        has_pref = dict() # index
        for d in self.days:
            for s in self.shifts:
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
        for d in self.days:
            for s in self.shifts:
                self.Add(sum(self.variables[(d, s, p)] for p in self.people) >= 1)
                self.Add(sum(self.variables[(d, s, p)] for p in self.people) <= self.sdata[(d,s)][0])

    def constraint_work_mins(self, min, max):
        """Make sure that everyone works the minimum number of minutes,
        and no one works too much.
        Args:
            min: the minimum number of minutes
            max: the maximum number of minutes
        """
        mins_of_shift = dict() # calculate shift hours

        for (d,s),vals in enumerate(self.sdata):
            mins_of_shift[(d,s)] = vals[2] - vals[1]

        for p in self.people:
            work_mins = 0
            for d in self.days:
                for s in self.shifts:
                    work_mins += self.variables[(d, s, p)] * mins_of_shift[(d,s)]
            self.Add(min < work_mins and work_mins < max)

    # def constraint_long_shift(self):
    #     """Make sure that everyone works at least one long shift.
    #     """
    #     long_shifts = set() # find long shift ids
    #     for shift in self.shifts:
    #         if shift[4] - shift[3] > 5: # Number of hours
    #             long_shifts.add(shift[1])
    #     for person_id in range(self.n_people):
    #         self.Add(
    #             sum(
    #                 [sum([self.variables[(d,s,person_id)] for s in long_shifts]) for d in range(7)]
    #             ) > 0
    #         ) # Any one of these has to be true -> sum > 0

    # def constraint_no_conflict(self):
    #     """Make sure that no one has two shifts on a day that overlap.
    #     """
    #     conflicting_pairs = set() # assuming every day has the same shifts
    #     for s1, s2 in combinations(self.shifts):
    #         if (s2[3] < s1[3] and s1[3] < s2[4]) or (s2[3] < s1[4] and s1[4] < s2[4]): # Test conflict
    #             conflicting_pairs.add((s1[1], s2[1])) # add their ids

    #     # find pairs of incompatible (day,shift) ids
    #     for p in range(self.n_people):
    #         for d in range(7):
    #             for s1_id, s2_id in conflicting_pairs:
    #                 # Both of them can't be true for the same person
    #                 self.Add(not(self.variables[(d, s1_id, p)] and self.variables[(d, s2_id, p)]))

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

    def on_solution_callback(self):
        print(f'Solution #{self._sol_count}')
        for d in self._m.days:
            print(f'Day {d}:')
            for s in self._m.shifts:
                print(f'    Shift {s}')
                for p in self._m.people:
                    if self.Value(self._m.variables[(d,s,p)]):
                        print(f'        Person {p}')
        print()
        self._sol_count += 1

    def solution_count(self):
        return self._sol_count

if __name__ == "__main__":
    requests = get_requests(20, 8, 3, 4)
    model = ShiftModel(flat_shifts, requests)
    solver = cp_model.CpSolver()
    sol_printer = ShiftSolutionPrinter(model, range(5))
    solver.SearchForAllSolutions(model, sol_printer)

# TODO add function to Minimize: preference cost
    # the simplest approach is to just sum up the preference scores for each shift

# Hint https://developers.google.com/optimization/scheduling/employee_scheduling
