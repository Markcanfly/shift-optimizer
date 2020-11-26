from random import sample, randint

n_people = 70
days = list(range(7))

requests = list() # Dictionary of days of applications

n_people = 20
n_shifts = 8

for p in range(n_people):
    for d in sample(range(7), 4): # Choose
        for pref, s in enumerate(sample(range(n_shifts), 3)):
            requests.append((d, s, p, pref))
