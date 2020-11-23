"""Defines the classes to store objects relevant to the shifts in."""

day_names = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap']
shift_names = [
    '08:45-11:00', 
    '11:00-15:00', 
    '11:00-15:00', 
    '12:00-16:00', 
    '12:00-16:00', 
    '12:00-17:00', 
    '11:30-14:00', 
    '11:30-14:00', 
    '17:00-22:00', 
    '18:00-21:30', 
    '17:00-23:45'
    ]

class Shift:
    def __init__(self, id_, day_index, beggining, end):
            self.id_ = id_
            self.beggining = beggining
            self.end = end
            self.day_index = day_index
    
    @classmethod
    def conflicts(cls, shift1, shift2) -> bool:
        return (shift1.beggining > shift2.beggining and shift1.beggining < shift2.end) or (shift1.end > shift2.beggining and shift1.end < shift2.end)

    def __repr__(self):
        return f'Day:{day_names[self.day_index]} ID:{self.id_} Start:{self.beggining} End:{self.end}'

class Application:
    def __init__(self, person, shift_id, preference_score):
        self.person = person
        self.shift_id = shift_id
        self.preference_score = preference_score

    def __repr__(self): # TODO switch these out with fstrings
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

class Time:
    def __init__(self, hour, minute):
        self.hour = hour
        self.minute = minute
        self.time = hour*60 + minute

    def __gt__(self, other) -> bool:
        return self.time > other.time

    def __lt__(self, other) -> bool:
        return self.time < other.time

    def __eq___(self, other) -> bool:
        return self.time == other.time

    def __repr__(self):
        return f"{self.hour}:{self.minute:02d}"
