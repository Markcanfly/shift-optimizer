from models import Shift, Time

day_names = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap']
shift_names = ['08:45-11:00', '11:00-15:00', '11:00-15:00', '12:00-16:00', '12:00-16:00', '12:00-17:00', '11:30-14:00', '11:30-14:00', '17:00-22:00', '18:00-21:30', '17:00-23:45']

shifts = dict()

for i, day_name in enumerate(day_names):
    shifts[day_name] = [Shift(0, i, Time(8, 45), Time(16,00)), Shift(1, i, Time(11, 00), Time(15,00)), Shift(2, i, Time(11, 00), Time(15,00)), Shift(3, i, Time(12, 00), Time(16,00)), Shift(4, i, Time(12, 00), Time(16,00)), Shift(5, i, Time(12, 00), Time(17,00)), Shift(6, i, Time(11, 30), Time(14,00)), Shift(7, i, Time(11, 30), Time(14,00)), Shift(8, i, Time(17, 00), Time(22,00)), Shift(9, i, Time(18, 00), Time(21,30)), Shift(10, i, Time(17, 00), Time(23,45))]
