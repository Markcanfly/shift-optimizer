from ortools.sat.python import cp_model
from data import preferences_from_csv, shifts_from_json
from itertools import combinations

def get_printable_time(minutes):
    hours = minutes // 60
    minutes = minutes % 60
    return str(hours)+':'+f'{minutes:02}'

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
        self.pdata = ShiftModel.get_prefdata(preferences, shiftlist)

        self.variables = {}
        for d, shifts in self.daily_shifts.items():
            for s in shifts:
                for p in self.people:
                    self.variables[(d, s, p)] = self.NewBoolVar(f'Day{d} Shift{s} Person{p}')
        
        self.AddPrefOnly()
        self.AddLongShiftBreak()
        self.AddNoConflict()

    def AddPrefOnly(self):
        """Make sure that employees only get assigned to a shift
        that they signed up for.
        """
        for (d, s, p) in self.variables.keys():
            if (d,s,p) not in self.pdata:
                self.Add(self.variables[(d, s, p)] == False)

    def AddShiftCapacity(self, min=1, leeway=0):
        """Make sure that there are exactly as many employees assigned
        to a shift as it has capacity.
        Args:
            min: the absolute minimum number of people assigned to each shift
            leeway: the minimum relative to the capacity
        """
        for d, shifts in self.daily_shifts.items():
            for s in shifts:
                self.Add(min <= sum(self.variables[(d, s, p)] for p in self.people)) # Minimum
                # self.Add((self.sdata[(d,s)][0] - leeway) <= sum(self.variables[(d, s, p)] for p in self.people)) # Add leeway, useful when capacity>1
                self.Add(sum(self.variables[(d, s, p)] for p in self.people) <= self.sdata[(d,s)][0])

    def AddWorkMinutes(self, min, max):
        """Make sure that everyone works the minimum number of minutes,
        and no one works too much.
        Args:
            min: the minimum number of minutes
            max: the maximum number of minutes
        """
        mins_of_shift = dict() # calculate shift hours

        for (d,s),(c, begin, end) in self.sdata.items():
            del c # Capacity is not used here
            mins_of_shift[(d,s)] = end - begin
        
        for p in self.people:
            work_mins = 0
            for d, shifts in self.daily_shifts.items():
                for s in shifts:
                    work_mins += self.variables[(d, s, p)] * mins_of_shift[(d,s)]
            self.AddLinearConstraint(work_mins, min, max)

    def AddMinLongShifts(self, n, length=300):
        """Make sure that everyone works at least n long shifts.
        Args:
            n: the number of shifts one needs to work
            length: the length (in minutes) that the shifts needs to be LONGER THAN (>) to qualify
        """
        long_shifts = set() # find long shifts
        for (d, s), (c, begin, end) in self.sdata.items():
            del c # Capacity is not used here
            if end - begin > length: # Number of minutes
                long_shifts.add((d, s))

        for p in self.people:
            self.Add(
                sum([self.variables[(d,s,p)] for (d,s) in long_shifts]) >= n
            ) # A worker has to have exactly one long shift a week

    def AddLongShiftBreak(self):
        long_shifts = set() # find long shifts
        for (d, s), (c, begin, end) in self.sdata.items():
            del c # Capacity is not used here
            if end - begin > 5*60: # Number of minutes
                long_shifts.add((d, s))
        
        for p in self.people:
            for (d,long_s) in long_shifts:
                self.Add(sum([(self.variables[d,s,p]) for s in self.daily_shifts[d]]) == 1).OnlyEnforceIf(self.variables[d,long_s,p])

    def AddNoConflict(self):
        """Make sure that no one has two shifts on a day that overlap.
        """
        conflicting_pairs = set() # assuming every day has the same shifts
        for ((d1,s1),(c1, b1, e1)), ((d2,s2),(c2, b2,e2)) in combinations(self.sdata.items(), r=2):
            del c1, c2 # Capacity is not used here
            if (d1==d2) and (((b2 < b1 < e2) or (b2 < e1 < e2)) or (((b1 < b2 < e1) or (b1 < e2 < e1)))): # Test conflict
                conflicting_pairs.add((d1,(s1,s2))) # add their ids

        # find pairs of incompatible (day,shift) ids
        for p in self.people:
            for d,(s1,s2) in conflicting_pairs:
                # Both of them can't be true for the same person
                self.Add(self.variables[(d,s1,p)] + self.variables[(d,s2,p)] < 2)

    def MaximizeWelfare(self, fun):
        """Maximize the welfare of the employees.
        This target will minimize the dissatisfaction of the employees
        with their assigned shift, given a function, which determines factors
        such as how important it is not to have outliers.

        Args:
            fun: function to plug prefscore into before summing.
        """
        pref = dict()
        for (d,s,p) in self.variables:
            pref[(d,s,p)] = self.pdata[(d,s,p)] if (d,s,p) in self.pdata else 0

        self.Minimize(
            sum([works*fun(pref[works_id]) for works_id, works in self.variables.items()])
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

    @staticmethod
    def get_prefdata(preferences, shiftlist):
        """Build a dictionary with the preference data from a preferences list
        Args:
            preferences: list of (day_id, shift_id, person_id, pref_score) tuples
            shifts: list of (day_id, shift_id, capacity, from, to) tuples where
        Returns:
            dictionary of pdata[(day_id, shift_id, person_id)] = pref_score
        """
        days = list(ShiftModel.get_daily_shifts(shiftlist).keys()) # Get day names for day indices
        pdata = dict()
        for pref in preferences:
            pdata[(days[pref[0]], pref[1], pref[2])] = pref[3]
        
        return pdata

class ShiftSolver(cp_model.CpSolver):
    def __init__(self, shifts, preferences):
        """Args:
            shifts: list of (day_id, shift_id, capacity, from, to) tuples where
            preferences: list of (day_id, shift_id, person_id, pref_score) tuples
        """
        super().__init__()
        self.shifts = shifts
        self.preferences = preferences
        self.model = None
    
    def Solve(self, min_workers, min_hours, max_hours, min_long_shifts, pref_function=lambda x:x, timeout=10):
        """ 
        Args:
            min_workers: The minimum number of workers that have to be assigned to every shift
            min_hours: The minimum number of hours every worker has to work
            max_hours: The maximum number of hours every worker has to work
            min_long_shifts: Minimum number of long shifts for every worker
            pref_function: function that takes and returns an integer, used for weighting of the pref function
            timeout: number of seconds that the solver can take to find the optimal solution
        Returns:
            Boolean: whether the solver found a solution.
        """
        
        self.model = ShiftModel(self.shifts, self.preferences)
        self.model.AddShiftCapacity(min=min_workers)
        self.model.AddWorkMinutes(min=min_hours*60, max=max_hours*60)
        self.model.MaximizeWelfare(pref_function)
        self.model.AddMinLongShifts(min_long_shifts)
        self.parameters.max_time_in_seconds = timeout
        super().Solve(self.model)
        if super().StatusName() != 'INFEASIBLE':
            print(f'Solution found for the following parameters:')
            print(f'Hours: {min_hours}<t<{max_hours}')
            print(f'Minimum people on a shift: {min_workers}')
            return True
        else:
            print(f'No solution found for {min_hours}<t<{max_hours} With a minimum of {min_workers} for each shift')
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

        for d, shifts in self.model.daily_shifts.items():
            txt += f'Day {d}:\n'
            for s in shifts:
                shift_dur_str = f'{get_printable_time(self.model.sdata[(d,s)][1])}-{get_printable_time(self.model.sdata[(d,s)][2])}'
                txt += f'    Shift {s} {shift_dur_str}\n'
                for p in self.model.people:
                    if self.Value(self.model.variables[(d,s,p)]):
                        txt += f'        {p}'
                        if with_preferences:
                            txt += f'preference {self.model.pdata[(d,s,p)]}'
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
        for p in self.model.people:
            work_hours=0
            for d, shifts in self.model.daily_shifts.items():
                for s in shifts:
                    s_hours = (self.model.sdata[(d,s)][2] - self.model.sdata[(d,s)][1]) / 60
                    work_hours += self.Value(self.model.variables[d,s,p]) * s_hours
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
        for d, shifts in self.model.daily_shifts.items():
            txt += f'Day {d}:\n'
            for s in shifts:
                if self.Value(self.model.variables[(d,s,employee_id)]):
                    shift_dur_str = f'{get_printable_time(self.model.sdata[(d,s)][1])}-{get_printable_time(self.model.sdata[(d,s)][2])}'
                    txt += f'    Shift {s} {shift_dur_str}\n'
        return txt

# TODO add employer reports to file
    # Extensive stats

# TODO add leeway instead of people per shift
# right now it doesn't really have an incentive to fill shifts
# with capacity > 1, only if it's convenient. Change that.