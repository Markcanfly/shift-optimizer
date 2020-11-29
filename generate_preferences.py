from random import sample, randint, choice

n_people = 70
days = list(range(7))

def get_requests(n_people, n_shifts, days_per_person, shifts_per_person):
    requests = list() # Dictionary of days of applications
    for p in range(n_people):
        for d in sample(range(7), days_per_person): # Choose
            for pref, s in enumerate(sample(range(n_shifts), shifts_per_person)):
                requests.append((d, s, p, pref))
            requests.append((d, choice((0,7)), p, pref))# TODO solve preference order
    return requests