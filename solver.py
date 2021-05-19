from ortools.sat.python import cp_model
from itertools import combinations, product
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

    def AddMinimumCapacityFilledNumber(self, n: int):
        """Make sure that at least n out of the sum(capacities) is filled.
        """
        self.Add(sum([assigned_val for assigned_val in self.variables.values()]) >= n)

    def AddMinMaxMinutes(self):
        """Make sure that everyone works within their schedule time range.
        """
        for u in self.schedule.users:
            worktime = 0
            for s in self.schedule.shifts:
                if (s.id,u.id) in self.variables:
                    worktime += self.variables[s.id, u.id] * s.length.seconds
            self.Add(int(u.min_hours*60*60) <= worktime <= int(u.max_hours*60*60))

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
                    self.Add(sum([(self.variables[other_s.id,u.id]) 
                    for other_s in self.schedule.shifts_for_day[s.begin.date()]
                    if (other_s.id,u.id) in self.variables]) == 1).OnlyEnforceIf(self.variables[s.id, u.id])

    def AddNoConflict(self):
        """Make sure that no one has two shifts on a day that overlap.
        """
        conflicting_pairs = set() # assuming every day has the same shifts
        for shift1, shift2 in combinations(self.schedule.shifts, r=2):
            if shift1 & shift2: # bitwise and -> overlaps
                conflicting_pairs.add((shift1.id,shift2.id))

        # find pairs of incompatible (day,shift) ids
        for u in self.schedule.users:
            for s1_id, s2_id in conflicting_pairs:
                # Both of them can't be true for the same person
                if (s1_id,u.id) in self.variables and (s2_id,u.id) in self.variables:
                    self.Add(self.variables[s1_id,u.id] + self.variables[s2_id,u.id] < 2)

    def AddSleep(self):
        """Make sure that no one has a shift in the morning,
        if they had a shift last evening.
        """
        conflicting_pairs = self.get_nosleep_shifts() # Pairs of (d1,s1), (d2,s2)

        for u in self.schedule.users:
            for s1, s2 in conflicting_pairs:
                if (s1,u.id) in self.variables and (s2,u.id) in self.variables:
                    # Both of them can't be true for the same person
                    self.Add(self.variables[s1,u.id] + self.variables[s2, u.id] < 2)

    def MaximizeWelfare(self):
        """Maximize the welfare of the employees.
        This target will minimize the dissatisfaction of the employees
        with their assigned shift.
        """
        self.Minimize(
            sum([works*self.schedule.preference[shift,user] for (shift, user), works in self.variables.items() if (shift,user) in self.schedule.preference])
        )

    # Helper methods

    def get_nosleep_shifts(self) -> Set[Tuple[Shift,Shift]]:
        """Collect pairs of shifts that conflict in the following way:
        One is a late shift, and the other is an early shift on the following day
        """
        conflicting = set()
        prev_day_late_shifts = []
        for shifts_for_day in self.schedule.shifts_for_day.values():
            early_shifts = [s for s in shifts_for_day if s.starts_early]
            for s1, s2 in product(early_shifts, prev_day_late_shifts):
                conflicting.add((s1.id, s2.id))
            prev_day_late_shifts = [s for s in shifts_for_day if s.ends_late]

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
        self.__model.AddLongShiftBreak()
        self.__model.AddSleep()
        self.__model.AddMinMaxMinutes()
        self.__model.AddMaxDailyShifts(1)
        if timeout is not None:
            self.parameters.max_time_in_seconds = timeout
        super().Solve(self.__model)
        if super().StatusName() in ('FEASIBLE', 'OPTIMAL'):
            return True
        return False
    
    def get_overview(self):
        return self.get_shift_workers() + self.get_employees_hours()

    def get_shift_workers(self, with_preferences=False):
        """Human-readable overview of the shifts
        Args:
            with_preferences: whether to add the preference values as well.
        Returns:
            Multiline string
        """
        txt = str()

        for d, shifts in self.__model.schedule.shifts_for_day.items():
            txt += f'Day {d}:\n'
            for s in shifts:
                shift_dur_str = f'{get_printable_time(self.__model.shift_data[(d,s)][1])}-{get_printable_time(self.__model.shift_data[(d,s)][2])}'
                txt += f'    Shift {s} {shift_dur_str}\n'
                for p in self.__model.people:
                    if self.Value(self.__model.variables[(d,s,p)]):
                        txt += f'        {p}'
                        if with_preferences:
                            txt += f'preference {self.__model.pref_data[(d,s,p)]}'
                        txt += '\n'
            txt += '\n'
        if with_preferences:
            txt += f'Preference score: {self.ObjectiveValue()}\n'
        return txt

    def get_employees_hours(self):
        """Human-readable hours for each employee
        Returns:
            Multiline string
        """
        txt = str()
        for p in self.__model.people:
            work_hours=0
            for d, shifts in self.__model.shifts_for_day.items():
                for s in shifts:
                    s_hours = (self.__model.shift_data[(d,s)][2] - self.__model.shift_data[(d,s)][1]) / 60
                    work_hours += self.Value(self.__model.variables[d,s,p]) * s_hours
            txt += f'{p} works {work_hours} hours.\n'
        return txt

    def get_employee_shifts(self, employee_id):
        """Human-readable shifts for an given employee
        Args:
            employee_id: the id for the employee to look up hours the shifts for
        Returns:
            Multiline string
        """
        txt = str()
        for d, shifts in self.__model.shifts_for_day.items():
            txt += f'Day {d}:\n'
            for s in shifts:
                if self.Value(self.__model.variables[(d,s,employee_id)]):
                    shift_dur_str = f'{get_printable_time(self.__model.shift_data[(d,s)][1])}-{get_printable_time(self.__model.shift_data[(d,s)][2])}'
                    txt += f'    Shift {s} {shift_dur_str}\n'
        return txt

    def Values(self) -> dict:
        """Returns a dictionary with the solver values.
        Returns:
            assigned[shift_id, person_id] = True | False
        """
        assigned = dict()
        for s,p in self.__model.variables.keys():
            assigned[s,p] = self.Value(self.__model.variables[s,p])
        
        return assigned

    def PrefScore(self) -> float:
        return self.ObjectiveValue()

    def PrefModes(self) -> int:
        freq = dict()
        pref = self.__model.pref_data

        for (d,s,p), val in self.Values().items():
            if val == 1: # Count the pref score
                # Here we assume pref[d,s,p] is not None, because model can't assign None
                if pref[d,s,p] not in freq.keys():
                    freq[pref[d,s,p]] = 1
                else:
                    freq[pref[d,s,p]] += 1
        # Find most common elements
        maxfreq = max(freq.values())
        modes = []
        for pscore, count in freq.items():
            if count == maxfreq:
                modes.append(pscore)

        return modes

    def EmptyShifts(self) -> int:
        assigned = self.Values()
        n_empty_shifts = 0
        for s in self.__model.schedule.shifts:
            if sum([assigned[s.id,u.id] for u in self.__model.schedule.users if (s.id,u.id) in assigned]) == 0:
                n_empty_shifts += 1
        
        return n_empty_shifts

    def NShifts(self) -> int:
        return len(self.__model.schedule.shifts)

    def UnfilledCapacities(self) -> int:
        assigned = self.Values()
        unfilled_capacities = 0
        for s in self.__model.schedule.shifts:
            unfilled_capacities += (s.capacity- sum([assigned[s.id,u.id] for u in self.__model.schedule.users if (s.id,u.id) in assigned]))
        return unfilled_capacities

    def NCapacities(self) -> int:
        capacities = 0
        for capacity, begin, end in self.__model.shift_data.values():
            del begin, end
            capacities += capacity
        return capacities

    def UnfilledHours(self) -> float:
        assigned = self.Values()
        unfilled_hours = 0
        for (d,s), shift_props in self.__model.shift_data.items():
            unfilled_capacities_on_this_shift = (shift_props[0] - sum([assigned[d,s,p] for p in self.__model.people]))
            length_of_shift_in_hours = (shift_props[2] - shift_props[1]) / 60
            unfilled_hours += unfilled_capacities_on_this_shift * length_of_shift_in_hours
        return unfilled_hours

    def Hours(self) -> float:
        n_hours = 0
        for capacity, begin_mins, end_mins in self.__model.shift_data.values():
            n_hours += ((end_mins-begin_mins)/60)*capacity
        return n_hours

    def NPeople(self) -> int:
        return len(self.__model.people)
