from random import sample, randint, choice, shuffle

n_people = 70
days = list(range(7))

def get_requests(n_people, n_shifts, days_per_person, shifts_per_person):
    requests = list() # Dictionary of days of applications
    for p in range(n_people):
        for d in sample(range(7), days_per_person): # Choose
            shifts_applied_to = set() # At least one long shift has to be already in the set
            shifts_applied_to.add(choice((0,7)))
            for shift in sample(range(n_shifts), shifts_per_person):
                shifts_applied_to.add(shift)
            preference_list = list(shifts_applied_to)
            shuffle(preference_list) # put the list in random order
            for pref_score, shift_id in enumerate(preference_list):
                requests.append((d, shift_id, p, pref_score)) # TODO solve preference order
    return requests