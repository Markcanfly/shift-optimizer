class Shift:
    def __init__(self, id_, day_index, beggining, end):
            self.id_ = id_
            self.beggining = beggining
            self.end = end
            self.day_index = day_index

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

class Time:
    def __init__(self, hour, minute):
        self.hour = hour
        self.minute = minute
        elf.time = hour*60 + minute
    
    def __gt__(self, other) -> bool:
        return self.time > other.time

    def __lt__(self, other) -> bool:
        return self.time < other.time

    def __eq___(self, other) -> bool:
        return self.time == other.time

    def __repr__(self):
        return f"{hour}:{minute:02d}"