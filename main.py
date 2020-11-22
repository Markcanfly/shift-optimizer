from random import randint, sample
from itertools import product
from tqdm import tqdm

day_names = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap']
shift_names = ['8:45-11:00', '11:00-15:00', '11:00-15:00', '12:00-16:00', '12:00-16:00', '12:00-17:00', '11:30-14:00', '11:30-14:00', '17:00-22:00', '18:00-21:30', '17:00-23:45']

class Shift:
    def __init__(self, id_, beggining, end):
            self.id_ = id_
            self.beggining = beggining
            self.end

class Application:
    def __init__(self, person, shift_id, preference_score):
        self.person = person
        self.shift_id = shift_id
        self.preference_score = preference_score

    def __repr__(self):
        return "{0} {1} #{2}".format(self.person, shift_names[self.shift_id], self.preference_score)

class Person:
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return "Name:{0}".format(self.name)

class Choice:
    def __init__(self, applications):
        self.applications = applications
        self.welfare = 0
        for application in applications:
            self.welfare += application.preference_score

    def __repr__(self):
        return "Welfare score: " + str(self.welfare)

    def overlaps(self) -> bool:
        pass

# Applications is a list(days) of lists(shifts) of lists(applications). 
applications = list()
for day_index, day in enumerate(day_names):
    applications.append(list())
    for i in range(len(shift_names)):
        applications[day_index].append(list())

# Generate people
n_people = 10
people = list()
for person_id in range(n_people):
    person = Person(str(person_id))
    people.append(person)
    chosen_days = sample(applications, 4) # Choose 4 random days to apply to
    for shift_applications in chosen_days: # Find the lists of applications for each shift
        shift_ids_to_apply_to = sample(range(len(shift_applications)), 3) # Find the indices of the shifts to apply to
        for preference_score, shift_id in enumerate(shift_ids_to_apply_to):
            shift_applications[shift_id].append(Application(person, shift_id, preference_score))

# Aggregates all choices day_index
day_index = 0 # Monday
cartesian_products_of_applications = product(*[shift_list for shift_list in applications[day_index] if len(shift_list) > 0])
choices = [Choice(applications=c) for c in cartesian_products_of_applications]

for choice in choices:
    print(choice.welfare)
