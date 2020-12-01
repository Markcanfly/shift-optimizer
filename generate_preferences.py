from random import sample, randint, choice, shuffle
from data import flat_shifts

def generate_requests(n_people, days_per_person, shifts_per_day):
    shifts = dict()
    for shift in flat_shifts:
        day = shift[0]
        shifts[day] = set()
    
    for shift in flat_shifts:
        day = shift[0]
        shifts[day].add(shift)
    # Shifts is now a shift['day'] = ((id, day, ...), (id2, day2,...)) dict
    
    requests = set() # Dictionary of days of applications
    for p in range(n_people):
        days = sample(shifts.keys(), days_per_person)
        for day in days:
            shiftlist = shifts[day]
            # Find a long shift
            long_shifts = set()
            for id_, d, capacity, begin, end in shiftlist:
                del d, capacity # We don't care about capacity here, and day is redundant
                if end-begin >= 5*60: # Shift is longer than 5 hours
                    long_shifts.add(id_)
            
            temp_applied = set() # Shift ids that this person applies to
            temp_applied.add(choice(list(long_shifts))) # Apply to a long shift on the day

            for shift in sample(shiftlist, shifts_per_day):
                temp_applied.add(shift[1]) # Apply to other shifts
            
            applied = list(temp_applied)
            shuffle(applied) # Random order will indicate preference
            for pref, s_id in enumerate(applied):
                requests.add((day, s_id, p, pref))
    return requests