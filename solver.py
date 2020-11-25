from ortools.sat.python import cp_model
from data import shifts
from models import Shift # For IntelliSense

class ShiftModel(cp_model.CpModel):
    """Shift solver

    This class takes a list of shifts, 
    and a list of preferenced shift requests.
    Then provides an optimal solution (if one exists)
    for the given parameters.
    """
    def __init__(self, shifts, preferences):
        """Args:
            shifts: list of (day_id, shift_id, capacity, from, to) tuples where
            preferences: list of (day_id, shift_id, person_id, pref_score) tuples
        """
        super.__init__()
        self.n_people = len(ShiftModel.get_people(preferences))
        self.n_shifts = len(shifts)
        self.shifts = shifts
        self.preferences = preferences
        self.variables = {}
        for shift in shifts: # Create variables
            day_id = shift[0]
            shift_id = shift[1]
            for person_id in range(self.n_people):
                self.variables[(day_id, shift_id, person_id)] = self.NewBoolVar(f'Day{day_id} Shift{shift_id} Person{person_id}')
        self.constraint_pref_only()
        self.constraint_shift_capacity()
        self.constraint_work_hours(25, 35)

    def constraint_pref_only(self):
        """Make sure that employees only get assigned to a shift
        that they signed up for.
        """
        has_pref = dict() # index
        for day_id in range(7):
            has_pref[day_id] = dict()
            for shift_id in range(self.n_shifts):
                has_pref[day_id][shift_id] = dict()
                for person_id in range(self.n_people):
                    has_pref[day_id][shift_id][person_id] = False # default every pref to False
        for pref in self.preferences: # overwrite to two if the employee signed up with any pref score
            has_pref[pref[0]][pref[1]][pref[2]] = True

        for (day_id, shift_id, person_id), variable in enumerate(self.variables):
            if not has_pref[day_id][shift_id][person_id]:
                self.Add(variable == False)

    def constraint_shift_capacity(self):
        """Make sure that there are exactly as many employees assigned
        to a shift as it has capacity.
        """
        capacity = dict() # index capacities
        for day_id in range(7):
            capacity[day_id] = dict()
        for shift in self.shifts:
            day_id = shift[0]
            shift = shift[1]
            capacity = shift[2]
            capacity[day_id][shift] = capacity
        
        for day_id in range(7):
            for shift_id in range(self.n_shifts):
                self.Add(sum([self.variables[(day_id, shift_id, person_id)] for person_id in range(self.n_people)]) == capacity[day_id][shift_id])

    def constraint_work_hours(self, min, max):
        """Make sure that everyone works the minimum number of hours,
        and no one works too much.
        Args:
            min: the minimum number of hours
            max: the maximum number of hours
        """
        hours_of_shift = dict() # calculate shift hours

        for shift in self.shifts:
            hours_of_shift[(shift[0], shift[1])] = shift[4] - shift[3]

        for person_id in range(self.n_people):
            work_hours = 0
            for day_id in range(7):
                for shift_id in range(self.n_shifts):
                    work_hours += self.variables[(day_id, shift_id, person_id)] * hours_of_shift[day_id][shift_id]
            self.Add(min < work_hours and work_hours < max)

    @staticmethod
    def get_people(preferences):
        """Extract the set of people from a raw list
        Args:
            preferences: list of (day_id, shift_id, person_id, pref_score) tuples
        Returns:
            set of people
        """
        people = set()
        for preference in preferences:
            people.add(preference[2])
        return people

    @staticmethod
    def get_days(preferences):
        """Extract days data from preferences list
        Args:
            preferences: list of (day_id, shift_id, person_id, pref_score) tuples
        Returns:
            set of days
        """
        days = set()
        for pref in preferences:
            days.add(pref[0])
        return days

# TODO add minimum one long shift criteria
# TODO add no overlapping shifts assigned to the same person criteria
# TODO add function to Minimize: preference cost
    # the simplest approach is to just sum up the preference scores for each shift

# Hint https://developers.google.com/optimization/scheduling/employee_scheduling
