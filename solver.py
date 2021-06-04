from ortools.sat.python import cp_model
from itertools import combinations, permutations
from models import Schedule, Shift, ShiftId, User, ShiftPreference
from typing import List, Dict, Any, NoReturn, Tuple, Set, Iterable, Optional
from datetime import timedelta

class ShiftModel(cp_model.CpModel):
    """Shift solver

    This class takes a list of shifts, 
    and a list of preferenced shift requests.
    Then provides an optimal solution (if one exists)
    for the given parameters.
    """
    def __init__(self, schedule: Schedule):
        """Args:
            schedule: the Schedule to solver for
        """
        super().__init__()
        self.schedule = schedule
        self.variables = { # Create solver variables
            (p.shift.id, p.user.id):self.NewBoolVar(f'{p.user.id} works {p.shift.id}')
            for p in self.schedule.preferences
            }  
        # Add must-have-constraints
        self.AddNoConflict()

    def AddMaxDailyShifts(self, n: int = 1):
        """Make sure that employees only get assigned to
        maximum of n shifts on any given day.
        Args:
            n: the max number of shifts a person can work on any day.
        """
        for u in self.schedule.users:
            for shifts_for_day in self.schedule.shifts_for_day.values():
                self.AddLinearConstraint(sum([self.variables[s.id,u.id] for s in shifts_for_day if (s.id,u.id) in self.variables]), 0, n)

    def AddShiftCapacity(self):
        """Make sure that no more people are assigned to a shift than its capacity"""
        for s in self.schedule.shifts:
            self.AddLinearConstraint(
                sum([self.variables[s.id,u.id] for u in self.schedule.users
                if (s.id,u.id) in self.variables]), 0, s.capacity)

    def AddMinimumCapacityFilledNumber(self, n: int):
        """Make sure that at least n out of the sum(capacities) is filled.
        """
        self.Add(sum([assigned_val for assigned_val in self.variables.values()]) >= n)

    def AddMinMaxWorkTime(self):
        """Make sure that everyone works within their schedule time range.
        """
        for u in self.schedule.users:
            worktime = 0
            for s in self.schedule.shifts:
                if (s.id,u.id) in self.variables:
                    worktime += self.variables[s.id, u.id] * s.length.seconds
            self.AddLinearConstraint(worktime, int(u.min_hours*60*60), int(u.max_hours*60*60))

    def AddLongShifts(self):
        """Make sure that everyone works at least n long shifts.
        Args:
            n: the number of shifts one needs to work
        """
        for u in self.schedule.users:
            if u.only_long:
                self.Add(
                    sum([self.variables[s.id,u.id] for s in self.schedule.shifts if not s.is_long]) == 0
                )
            elif u.min_long > 0:
                self.Add(
                    sum([self.variables[s.id,u.id] for s in self.schedule.shifts if s.is_long]) > u.min_long    
                )

    def AddLongShiftBreak(self):
        """Make sure that if you work a long shift, you're not gonna work
        another shift on the same day.
        """
        for u in self.schedule.users:
            for s in self.schedule.shifts:
                if s.is_long and (s.id,u.id) in self.variables:
                    # Technically: for each long shift, if p works on that long shift, 
                    # Make sure that for that day,
                    # The number of shifts worked for that person is exactly one.
                    self.Add(sum([(
                        self.variables[other_s.id,u.id]) 
                        for other_s in self.schedule.shifts_for_day[s.begin.date()]
                        if (other_s.id,u.id) in self.variables]
                    ) == 1).OnlyEnforceIf(self.variables[s.id, u.id])

    def AddNoConflict(self):
        """Make sure that no one has two shifts on a day that overlap.
        """
        conflicting_pairs = set() # assuming every day has the same shifts
        for shift1, shift2 in combinations(self.schedule.shifts, r=2):
            if shift1 & shift2: # bitwise and -> overlaps
                conflicting_pairs.add((shift1.id,shift2.id))

        for u in self.schedule.users:
            for s1_id, s2_id in conflicting_pairs:
                # Both of them can't be assigned to the same person
                # => their sum is less than 2
                if (s1_id,u.id) in self.variables and (s2_id,u.id) in self.variables:
                    self.Add(self.variables[s1_id,u.id] + self.variables[s2_id,u.id] < 2)

    def AddSleep(self):
        """Make sure that no one has a shift in the morning,
        if they had a shift last evening.
        """
        conflicting_pairs = self.get_nosleep_shifts()

        for u in self.schedule.users:
            for s1, s2 in conflicting_pairs:
                if (s1,u.id) in self.variables and (s2,u.id) in self.variables:
                    # Both of them can't be assigned to the same person
                    # => their sum is less than 2
                    self.Add(self.variables[s1,u.id] + self.variables[s2, u.id] < 2)

    def AddNonFulltimerMaxShifts(self, n: int):
        """Make sure that non-fulltimers (people who can take non-long shifts)
        Can take at most n shifts.
        """
        for u in self.schedule.users:
            if not u.only_long:
                self.AddLinearConstraint(
                    sum([self.variables[s.id,u.id] for s in self.schedule.shifts if (s.id,u.id) in self.variables]),
                    0, 
                    n)

    def MaximizeWelfare(self):
        """Maximize the welfare of the employees.
        This target will minimize the dissatisfaction of the employees
        with their assigned shift.
        """
        self.Minimize(
            sum([works*self.schedule.preference[shift,user] for (shift, user), works in self.variables.items()])
        )

    # Helper methods
    def get_nosleep_shifts(self) -> Set[Tuple[Shift,Shift]]:
        """Collect pairs of shifts that conflict in the following way:
        The time between the end of one and the begin of the other is
        less than 11 hours for long shifts, and 9 hours for non-long.
        """
        conflicting = set()
        for shift, other_shift in permutations(self.schedule.shifts, r=2):
            if shift.end < other_shift.begin:
                offtime_between = other_shift.begin - shift.end
                if shift.is_long:
                    if timedelta(0) <= offtime_between <= timedelta(hours=11):
                        conflicting.add((shift.id, other_shift.id))
                else:
                    if timedelta(0) <= offtime_between <= timedelta(hours=9):
                        conflicting.add((shift.id, other_shift.id))
        return conflicting

class ShiftSolver(cp_model.CpSolver):
    def __init__(self, schedule: Schedule):
        """Args:
            schedule: the Schedule to solve for
        """
        super().__init__()
        self.schedule=schedule
        self.__model = None
    
    def Solve(self, min_capacities_filled: int = 0, timeout: Optional[int]=None) -> bool:
        """ 
        Args:
            min_workers: The minimum number of workers that have to be assigned to every shift
            hours: hours[person_id] = {'min': n1, 'max': n2} dict
            n_long_shifts: Number of long shifts for every worker
            pref_function: function that takes and returns an integer, used for weighting of the pref function
            timeout: number of seconds that the solver can take to find the optimal solution
        Returns:
            Boolean: whether the solver found a solution.
        """
        
        self.__model = ShiftModel(self.schedule)
        self.__model.AddMinimumCapacityFilledNumber(n=min_capacities_filled)
        self.__model.MaximizeWelfare()
        self.__model.AddShiftCapacity()
        self.__model.AddLongShiftBreak()
        self.__model.AddSleep()
        self.__model.AddMinMaxWorkTime()
        self.__model.AddMaxDailyShifts(1)
        self.__model.AddNonFulltimerMaxShifts(5)
        if timeout is not None:
            self.parameters.max_time_in_seconds = timeout
        super().Solve(self.__model)
        if super().StatusName() in ('FEASIBLE', 'OPTIMAL'):
            return True
        return False
    
    def get_overview(self):
        return self.get_shift_workers() + self.get_employees_hours()

    def get_shift_workers(self):
        """Human-readable overview of the shifts
        Returns:
            Multiline string
        """
        txt = ''
        for shift in self.__model.schedule.shifts:
            txt += f'{shift}'
            txt += ''.join(
                [f'\n\t{u.id} p={self.__model.schedule.preference[shift.id,u.id]}' for u in self.schedule.users 
                if (shift.id,u.id) in self.__model.variables 
                and self.Value(self.__model.variables[shift.id,u.id])])
            txt += '\n'
        return txt

    def get_employees_hours(self):
        """Human-readable hours for each employee
        Returns:
            Multiline string
        """
        txt = str()
        for u in self.__model.schedule.users:
            work_hours=0
            for shift in self.__model.schedule.shifts:
                if (shift.id,u.id) in self.__model.variables:
                    work_hours += self.Value(self.__model.variables[shift.id,u.id]) * shift.length.seconds / (60*60)
            txt += f'{u.id} works {round(u.min_hours, 2)}<={round(work_hours, 2)}<={round(u.max_hours, 2)} hours.\n'
        return txt

    @property
    def Values(self) -> dict:
        """Returns a dictionary with the solver values.
        Returns:
            assigned[shift_id, person_id] = True | False
        """
        assigned = dict()
        for s,p in self.__model.variables.keys():
            assigned[s,p] = self.Value(self.__model.variables[s,p])
        
        return assigned

    @property
    def PrefScore(self) -> float:
        return self.ObjectiveValue()

    @property
    def NShifts(self) -> int:
        return len(self.__model.schedule.shifts)

    @property
    def UnfilledCapacities(self) -> int:
        assigned = self.Values
        unfilled_capacities = 0
        for s in self.__model.schedule.shifts:
            unfilled_capacities += (s.capacity- sum([assigned[s.id,u.id] for u in self.__model.schedule.users if (s.id,u.id) in assigned]))
        return unfilled_capacities
    
    @property
    def FilledCapacities(self) -> int:
        return self.NCapacities - self.UnfilledCapacities
    @property
    def NCapacities(self) -> int:
        capacities = 0
        for shift in self.__model.schedule.shifts:
            capacities += shift.capacity
        return capacities
    @property
    def UnfilledHours(self) -> float:
        assigned = self.Values
        unfilled_hours = 0
        for shift in self.__model.schedule.shifts:
            unfilled_capacities_on_this_shift = (shift.capacity - sum([assigned[shift.id,u.id] for u in self.__model.schedule.users if (shift.id,u.id) in assigned]))
            length_of_shift_in_hours = shift.length.seconds / (60*60)
            unfilled_hours += unfilled_capacities_on_this_shift * length_of_shift_in_hours
        return unfilled_hours
    @property
    def FilledHours(self) -> float:
        return self.Hours - self.UnfilledHours
    @property
    def Hours(self) -> float:
        n_hours = 0
        for shift in self.__model.schedule.shifts:
            n_hours += shift.length.seconds / (60*60)
        return n_hours

    @property
    def NPeople(self) -> int:
        return len(self.__model.people)
