"""Static data definition for the shifts."""

from models import Shift, Time

day_names = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap']

shifts = list()
for i, day_name in enumerate(day_names):
    shifts.append([
        Shift(0, i, Time(8, 45), Time(16,00)),
        Shift(1, i, Time(11, 00), Time(15,00)), 
        Shift(2, i, Time(11, 00), Time(15,00)), 
        Shift(3, i, Time(12, 00), Time(16,00)), 
        Shift(4, i, Time(12, 00), Time(16,00)), 
        Shift(5, i, Time(12, 00), Time(17,00)), 
        Shift(6, i, Time(11, 30), Time(14,00)), 
        Shift(7, i, Time(11, 30), Time(14,00)), 
        Shift(8, i, Time(17, 00), Time(22,00)), 
        Shift(9, i, Time(18, 00), Time(21,30)), 
        Shift(10, i, Time(17, 00), Time(23,45))
        ])
