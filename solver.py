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
    def __init__(self, shiftlist, preferences, groups):
        """Args:
            shifts: dict of sdata[day_id, shift_id] = {
                'capacity': 2,
                'begin': 525,
                'end': 960
            }
            preferences: dict of pref[day_id,shift_id,person_id] = pref_score
            group: group[person_id] = {'min': n1, 'max': n2, 'long_shifts': n3} dict
        """
        super().__init__()
        self.people = ShiftModel.get_people(preferences)
        self.daily_shifts = ShiftModel.get_daily_shifts(shiftlist)
        self.sdata = ShiftModel.get_shiftdata(shiftlist)
        self.prefdata = ShiftModel.get_prefdata(preferences, self.sdata.keys(), self.people)
        self.pdata = ShiftModel.get_groupdata(groups, preferences)

        self.variables = {}
        for d, shifts in self.daily_shifts.items():
            for s in shifts:
                for p in self.people:
                    self.variables[(d, s, p)] = self.NewBoolVar(f'Day{d} Shift{s} Person{p}')
        
        # Add must-have-constraints
        self.AddPrefOnly()
        self.AddLongShiftBreak()
        self.AddNoConflict()
        self.AddSleep()
        self.AddWorkMinutes()

    def AddPrefOnly(self):
        """Make sure that employees only get assigned to a shift
        that they signed up for.
        """
        for (d, s, p) in self.variables.keys():
            if self.prefdata[d,s,p] is None:
                self.Add(self.variables[(d, s, p)] == False)

    def AddShiftCapacity(self, min):
        """Make sure that there are exactly as many employees assigned
        to a shift as it has capacity.
        Args:
            min: the absolute minimum number of people assigned to each shift
        """
        for d, shifts in self.daily_shifts.items():
            for s in shifts:
                self.AddLinearConstraint(sum(self.variables[(d, s, p)] for p in self.people), min, self.sdata[(d,s)][0])

    def AddWorkMinutes(self):
        """Make sure that everyone works the minimum number of minutes,
        and no one works too much.
        This is determined by the hdata dictionary.
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
            self.AddLinearConstraint(work_mins, self.pdata[p]['min']*60, self.pdata[p]['max']*60)


    def AddLongShifts(self, length=300):
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
            min_long = self.pdata[p]['min_long_shifts']
            if min_long > 0:
                self.Add(
                    sum([self.variables[(d,s,p)] for (d,s) in long_shifts]) > min_long
                )
            if self.pdata[p]['only_long_shifts']:
                non_long_shifts = set(self.sdata.keys()).difference(long_shifts)
                for d, s in non_long_shifts:
                    self.Add(self.variables[d,s,p] == False)


    def AddLongShiftBreak(self, length=300):
        """Make sure that if you work a long shift, you're not gonna work
        another shift on the some day.
        """
        long_shifts = set() # find long shifts
        for (d, s), (c, begin, end) in self.sdata.items():
            del c # Capacity is not used here
            if end - begin > length: # Number of minutes
                long_shifts.add((d, s))
        
        for p in self.people:
            for (d,long_s) in long_shifts:
                # Technically: for each long shift, if p works on that long shift, make sure that for that day,
                # The number of shifts worked for that person is exactly one.
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

    def AddSleep(self):
        """Make sure that no one has a shift in the morning,
        if they had a shift last evening.
        """ # WARN Without a catalog of all days in the week, this fails when the days are nonconsecutive.
        
        conflicting_pairs = set() # Pairs of (d1,s1), (d2,s2)
        
        first_last_list = list(self.get_first_last_shifts().items())
        for i in range(len(first_last_list)-1):
            today_last = (first_last_list[i][0], first_last_list[i][1][1]) # (d1, s1)
            next_first = (first_last_list[i+1][0], first_last_list[i+1][1][0]) # (d2, s2)
            conflicting_pairs.add((today_last, next_first))
        
        for p in self.people:
            for (d1, s1),(d2,s2) in conflicting_pairs:
                # Both of them can't be true for the same person
                self.Add(self.variables[(d1,s1,p)] + self.variables[(d2,s2,p)] < 2)

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
            pref[(d,s,p)] = self.prefdata[(d,s,p)] if (d,s,p) in self.prefdata else 0

        self.Minimize(
            sum([works*fun(pref[works_id]) for works_id, works in self.variables.items() if pref[works_id] is not None])
        )

    # Helper methods

    def get_first_last_shifts(self):
        # Create a dictionary so that
        # first_last['day'] = (firstshift_id, lastshift_id)
        first_last = dict()
        for day, shift_ids in self.daily_shifts.items():
            first = sorted(shift_ids, key= lambda s: self.sdata[day,s][1])[0] # By beginning, ascending
            last = sorted(shift_ids, key= lambda s: self.sdata[day, s][2], reverse=True)[0] # By end, descending
            first_last[day] = (first, last)

        return first_last

    @staticmethod
    def get_daily_shifts(shifts):
        """Extract a dictionary of shift ids for each day. 
        Args:
            shifts: dict of sdata[day_id, shift_id] = {
                'capacity': 2,
                'begin': 525,
                'end': 960
            }
        Returns:
            daily_shifts['day'] = list(shift1_id, shift2_id...)    
        """
        daily_shifts = dict()

        for d,s in shifts.keys():
            if d not in daily_shifts.keys():
                daily_shifts[d] = [s]
            else:
                daily_shifts[d].append(s)

        return daily_shifts

    @staticmethod
    def get_people(preferences):
        """Extract the set of people from a raw shift data list
        Args:
            preferences: dict of pref[day_id,shift_id,person_id] = pref_score
        Returns:
            set of people ids
        """
        people = set()
        for d,s,p in preferences.keys():
            del d,s
            people.add(p)
        return people

    @staticmethod
    def get_shiftdata(shifts):
        """Build a dictionary with the shift data from a shift list.
        Args:
            shifts: dict of sdata[day_id, shift_id] = {
                'capacity': 2,
                'begin': 525,
                'end': 960
            }
        Returns:
            dictionary of sdata[(day_id, shift_id)] = (capacity, from, to)
        """
        sdata = dict()
        for (d,s), data in shifts.items():
            sdata[d, s] = (data['capacity'], data['begin'], data['end'])
        
        return sdata

    @staticmethod
    def get_prefdata(preferences, day_shift_combinations, people):
        """Build a dictionary with the preference data from a preferences list
        Add None values where there is preference
        Args:
            preferences: dict of pref[day_id,shift_id,person_id] = pref_score
            day_shift_combinations: (day_id, shift_id) tuples for all shifts
            people: list of all people considered in the model
        Returns:
            dictionary of pref[day_id,shift_id,person_id] = pref_score  or None
        """
        
        pdata = dict()
        for d, s in day_shift_combinations:
            for p in people:
                if (d,s,p) in preferences.keys():
                    pdata[d,s,p] = preferences[d,s,p]
                else:
                    pdata[d,s,p] = None
        
        return pdata

    @staticmethod
    def get_groupdata(groups, preferences):
        """Create valid personal group requirement dictionary.
        Make sure that there are no person_id -s in preferences that don't have a min-max value in hours.
        Make sure that the format is correct
        Args:
            group: group[person_id] = {'min': n1, 'max': n2, 'long_shifts': n3} dict
            preferences: list of (day_id, shift_id, person_id, pref_score) tuples to validate p_ids against
        """
        person_ids_not_in_groups = set([pref[2] for pref in preferences]).difference(groups.keys())
        if len(person_ids_not_in_groups) > 0:
            raise ValueError(f"Some names were not found in the groups dictionary: {person_ids_not_in_groups}")
        for p_groupvals in groups.values():
            assert isinstance(p_groupvals['min'], int) and isinstance(p_groupvals['max'], int)
            assert p_groupvals['min'] < p_groupvals['max']
            assert isinstance(p_groupvals['min_long_shifts'], int)
            assert isinstance(p_groupvals['only_long_shifts'], bool)
        return groups

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
    
    def Solve(self, min_workers, personal_reqs, pref_function=lambda x:x, timeout=10):
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
        
        self.model = ShiftModel(self.shifts, self.preferences, personal_reqs)
        self.model.AddShiftCapacity(min=min_workers)
        self.model.MaximizeWelfare(pref_function)
        self.parameters.max_time_in_seconds = timeout
        super().Solve(self.model)
        if super().StatusName() in ('FEASIBLE', 'OPTIMAL'):
            print(f'Solution found for the following parameters:')
            print(f'Minimum people on a shift: {min_workers}')
            return True
        else:
            print(f'No solution found for minimum of {min_workers} for each shift.')
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
                            txt += f'preference {self.model.prefdata[(d,s,p)]}'
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
    
    def get_values(self):
        """Returns a dictionary with the solver values.
        Returns:
            assigned[day_id, shift_id, person_id] = True | False
        """
        assigned = dict()
        for d,s,p in self.model.variables.keys():
            assigned[d,s,p] = self.Value(self.model.variables[d,s,p])
        
        return assigned

# TODO add employer reports to file
    # Extensive stats

# TODO add leeway instead of people per shift
# right now it doesn't really have an incentive to fill shifts
# with capacity > 1, only if it's convenient. Change that.