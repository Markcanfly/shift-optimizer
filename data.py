"""Static data definition for the shifts."""

from models import Shift, Time

day_names = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap']

shifts = []
for i, day_name in enumerate(day_names):
    shifts.append([
        Shift(0, i, beginning=Time(8, 45), end=Time(16,00)),
        Shift(1, i, beginning=Time(11, 00), end=Time(15,00), capacity=2),
        Shift(2, i, beginning=Time(12, 00), end=Time(16,00), capacity=2), 
        Shift(3, i, beginning=Time(12, 00), end=Time(17,00)), 
        Shift(4, i, beginning=Time(11, 30), end=Time(14,00), capacity=2),
        Shift(5, i, beginning=Time(17, 00), end=Time(22,00)), 
        Shift(6, i, beginning=Time(18, 00), end=Time(21,30)), 
        Shift(7, i, beginning=Time(17, 00), end=Time(23,45))
        ])

flat_shifts = []
for day_shifts in shifts:
    for s in day_shifts:
        begin = s.beginning.time # in minutes
        end = s.end.time
        flat_shifts.append((s.day_index, s.id_, s.capacity, begin, end))

