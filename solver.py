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
    def __init__(self, shifts: dict, preferences: dict, personal_requirements: dict):
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
        self.shifts_for_day = ShiftModel.get_daily_shifts(shifts)
        self.shift_data = ShiftModel.get_shiftdata(shifts)
        self.preq_data = ShiftModel.get_personal_requirements(personal_requirements, self.people)
        self.pref_data = ShiftModel.get_prefdata(preferences, self.shift_data.keys(), self.people, self.preq_data)

        self.variables = {}
        for d, shifts in self.shifts_for_day.items():
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
            if self.pref_data[d,s,p] is None:
                self.Add(self.variables[(d, s, p)] == False)

    def AddShiftCapacity(self, min):
        """Make sure that there are exactly as many employees assigned
        to a shift as it has capacity.
        Args:
            min: the absolute minimum number of people assigned to each shift
        """
        for d, shifts in self.shifts_for_day.items():
            for s in shifts:
                self.AddLinearConstraint(sum(self.variables[(d, s, p)] for p in self.people), min, self.shift_data[(d,s)][0])

    def AddMinimumFilledShiftRatio(self, ratio):
        """Make sure that at least ratio * sum(capacities) is filled.
        """
        sum_capacities = sum([shift_props[0] for shift_props in self.shift_data.values()])

        self.Add(sum([assigned_val for assigned_val in self.variables.values()]) >= int(sum_capacities*ratio))

    def AddMinimumCapacityFilledNumber(self, n):
        """Make sure that at least n out of the sum(capacities) is filled.
        """
        self.Add(sum([assigned_val for assigned_val in self.variables.values()]) >= n)

    def AddWorkMinutes(self):
        """Make sure that everyone works the minimum number of minutes,
        and no one works too much.
        This is determined by the hdata dictionary.
        """
        mins_of_shift = dict() # calculate shift hours

        for (d,s),(c, begin, end) in self.shift_data.items():
            del c # Capacity is not used here
            mins_of_shift[(d,s)] = end - begin
        
        for p in self.people:
            work_mins = 0
            for d, shifts in self.shifts_for_day.items():
                for s in shifts:
                    work_mins += self.variables[(d, s, p)] * mins_of_shift[(d,s)]
            self.AddLinearConstraint(work_mins, self.preq_data[p]['min']*60, self.preq_data[p]['max']*60)


    def AddLongShifts(self, length=300):
        """Make sure that everyone works at least n long shifts.
        Args:
            n: the number of shifts one needs to work
            length: the length (in minutes) that the shifts needs to be LONGER THAN (>) to qualify
        """
        long_shifts = set() # find long shifts
        for (d, s), (c, begin, end) in self.shift_data.items():
            del c # Capacity is not used here
            if end - begin > length: # Number of minutes
                long_shifts.add((d, s))

        for p in self.people:
            min_long = self.preq_data[p]['min_long_shifts']
            if min_long > 0:
                self.Add(
                    sum([self.variables[(d,s,p)] for (d,s) in long_shifts]) > min_long
                )
            if self.preq_data[p]['only_long_shifts']:
                non_long_shifts = set(self.shift_data.keys()).difference(long_shifts)
                for d, s in non_long_shifts:
                    self.Add(self.variables[d,s,p] == False)


    def AddLongShiftBreak(self, length=300):
        """Make sure that if you work a long shift, you're not gonna work
        another shift on the some day.
        """
        long_shifts = set() # find long shifts
        for (d, s), (c, begin, end) in self.shift_data.items():
            del c # Capacity is not used here
            if end - begin > length: # Number of minutes
                long_shifts.add((d, s))
        
        for p in self.people:
            for (d,long_s) in long_shifts:
                # Technically: for each long shift, if p works on that long shift, make sure that for that day,
                # The number of shifts worked for that person is exactly one.
                self.Add(sum([(self.variables[d,s,p]) for s in self.shifts_for_day[d]]) == 1).OnlyEnforceIf(self.variables[d,long_s,p])

    def AddNoConflict(self):
        """Make sure that no one has two shifts on a day that overlap.
        """
        conflicting_pairs = set() # assuming every day has the same shifts
        for ((d1,s1),(c1, b1, e1)), ((d2,s2),(c2, b2,e2)) in combinations(self.shift_data.items(), r=2):
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
            pref[(d,s,p)] = self.pref_data[(d,s,p)] if (d,s,p) in self.pref_data else 0

        self.Minimize(
            sum([works*fun(pref[works_id]) for works_id, works in self.variables.items() if pref[works_id] is not None])
        )

    # Helper methods

    def get_first_last_shifts(self):
        # Create a dictionary so that
        # first_last['day'] = (firstshift_id, lastshift_id)
        first_last = dict()
        for day, shift_ids in self.shifts_for_day.items():
            first = sorted(shift_ids, key= lambda s: self.shift_data[day,s][1])[0] # By beginning, ascending
            last = sorted(shift_ids, key= lambda s: self.shift_data[day, s][2], reverse=True)[0] # By end, descending
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
    def get_prefdata(preferences, day_shift_combinations, people, preqs):
        """Build a dictionary with the preference data from a preferences list
        Add None values where there is preference
        Args:
            preferences: dict of pref[day_id,shift_id,person_id] = pref_score
            day_shift_combinations: (day_id, shift_id) tuples for all shifts
            people: list of all people considered in the model
            preqs[person_id] = {'min': n1, 'max': n2, 'long_shifts': n3} dict
        Returns:
            dictionary of pref[day_id,shift_id,person_id] = pref_score  or None
        """
        
        pdata = dict()
        for d, s in day_shift_combinations:
            for p in people:
                if (d,s,p) in preferences.keys():
                    # 0-min-hour compensation:
                    # If a person has a 0-hour requirement,
                    # Transform their preferences, so that
                    # The global minimum can include them
                    # being assigned to their first 3 shifts.
                    # if preqs[p]['min'] == 0:
                    #     pdata[d,s,p] = -(3-preferences[d,s,p])
                    # else:
                    pdata[d,s,p] = preferences[d,s,p]
                else:
                    pdata[d,s,p] = None
        
        return pdata

    @staticmethod
    def get_personal_requirements(personal_requirements, people):
        """Create valid personal personal requirement dictionary.
        Make sure that there are no person_id -s in preferences that don't have a min-max value in hours.
        Make sure that the format is correct
        Args:
            personal_requirements: preqs[person_id] = {'min': n1, 'max': n2, 'long_shifts': n3} dict
            people: a set of people_ids to validate against
        """
        person_ids_not_in_groups = set(people).difference(personal_requirements.keys())
        if len(person_ids_not_in_groups) > 0:
            raise ValueError(f"Some names were not found in the groups dictionary: {person_ids_not_in_groups}")
        for p_groupvals in personal_requirements.values():
            assert isinstance(p_groupvals['min'], int) and isinstance(p_groupvals['max'], int)
            assert p_groupvals['min'] < p_groupvals['max']
            assert isinstance(p_groupvals['min_long_shifts'], int)
            assert isinstance(p_groupvals['only_long_shifts'], bool)
        return personal_requirements

class ShiftSolver(cp_model.CpSolver):
    def __init__(self, shifts: dict, preferences: dict, personal_reqs: dict):
        """Args:
            shifts: list of (day_id, shift_id, capacity, from, to) tuples where
            dict of pref[day_id,shift_id,person_id] = pref_score,
            personal_reqs: preqs: preqs[person_id] = {
                'min': n1, 
                'max': n2, 
                'min_long_shifts': n3, 
                'only_long_shifts': bool1
            } dict
        """
        super().__init__()
        self.shifts = shifts
        self.preferences = preferences
        self.personal_reqs = personal_reqs
        self.__model = None
    
    def Solve(self, min_workers: int, min_capacities_filled: int = 0, min_capacities_filled_ratio: float = 0, pref_function=lambda x:x, timeout=10) -> bool:
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
        
        self.__model = ShiftModel(self.shifts, self.preferences, self.personal_reqs)
        self.__model.AddShiftCapacity(min=min_workers)
        self.__model.AddMinimumCapacityFilledNumber(n=min_capacities_filled)
        self.__model.AddMinimumFilledShiftRatio(ratio=min_capacities_filled_ratio)
        self.__model.MaximizeWelfare(pref_function)
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

        for d, shifts in self.__model.shifts_for_day.items():
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
            assigned[day_id, shift_id, person_id] = True | False
        """
        assigned = dict()
        for d,s,p in self.__model.variables.keys():
            assigned[d,s,p] = self.Value(self.__model.variables[d,s,p])
        
        return assigned

    def EmptyShifts(self) -> int:
        assigned = self.Values()
        n_empty_shifts = 0
        for d,s in self.__model.shift_data.keys():
            if sum([assigned[d,s,p] for p in self.__model.people]) == 0:
                n_empty_shifts += 1
        
        return n_empty_shifts

    def UnfilledCapacities(self) -> int:
        assigned = self.Values()
        unfilled_capacities = 0
        for (d,s), shift_props in self.__model.shift_data.items():
            unfilled_capacities += (shift_props[0] - sum([assigned[d,s,p] for p in self.__model.people]))
        return unfilled_capacities

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
