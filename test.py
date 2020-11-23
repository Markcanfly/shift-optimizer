"""Manual testing of the models"""

import models
from random import randint, sample
from itertools import product
from data import shifts, day_names

if __name__ == "__main__":

    # # Applications is a list(days) of lists(shifts) of lists(applications). 
    # applications = list()
    # for day_index, day in enumerate(day_names):
    #     applications.append(list())
    #     for i in range(len(shift_names)):
    #         applications[day_index].append(list())
    # # Generate people
    # n_people = 10
    # people = list()
    # for person_id in range(n_people):
    #     person = models.Person(str(person_id))
    #     people.append(person)
    #     chosen_days = sample(applications, 4) # Choose 4 random days to apply to
    #     for shift_applications in chosen_days: # Find the lists of applications for each shift
    #         shift_ids_to_apply_to = sample(range(len(shift_applications)), 3) # Find the indices of the shifts to apply to
    #         for preference_score, shift_id in enumerate(shift_ids_to_apply_to):
    #             shift_applications[shift_id].append(models.Application(person, shift_id, preference_score))
    
    # # Aggregates all choices day_index
    # day_index = 0 # Monday
    # cartesian_products_of_applications = product(*[shift_list for shift_list in applications[day_index] if len(shift_list) > 0])
    # choices = [models.Choice(applications=c) for c in cartesian_products_of_applications]

    # for choice in choices:
    #     print(choice.welfare)

    print(shifts['Hétfő'])
