from datetime import datetime, date, timedelta, tzinfo
from typing import List, Dict, Any, NewType
UserId = NewType('UserId', Any)
ShiftId = NewType('ShiftId', int)

class Shift:
    """Shift timeframe and capacity
    Sorts based on begin time
    """
    def __init__(self, id: ShiftId, begin: datetime, end: datetime, capacity: int):
        self.id = id
        self.begin = begin
        self.end = end
        self.capacity = capacity
    def __eq__(self, other: "Shift"):
        return ((self.begin, self.end, self.capacity) == (other.begin, other.end, other.capacity))
    def __ne__(self, other: "Shift"):
        return not self.__eq__(other)
    def __lt__(self, other: "Shift"):
        return self.begin < other.begin
    def __le__(self, other: "Shift"):
        return self.begin <= other.begin
    def __gt__(self, other: "Shift"):
        return self.begin > other.begin
    def __ge__(self, other: "Shift"):
        return self.begin >= other.begin
    def __and__(self, other: "Shift"):
        """Detects if two shifts overlap"""
        return ((self.begin  <= other.begin <= self.end) or
                (self.begin  <= other.end   <= self.end) or
                (other.begin <= self.begin  <= other.end) or
                (other.begin <= self.end    <= other.end))

    def __repr__(self):
        return f'{self.begin}-{self.end} Capacity {self.capacity}'
class User:
    """User requirements"""
    def __init__(self, user_id: UserId, min_hours: float, max_hours: float, only_long: bool, min_long: int):
        self.id = user_id
        self.min_hours = min_hours
        self.max_hours = max_hours
        self.only_long = only_long
        self.min_long = min_long
class ShiftPreference:
    """Stores a User-Shift relation with a preference score"""
    def __init__(self, user: User, shift: Shift, priority: int):
        self.user = user
        self.shift = shift
        self.priority = priority
class Schedule:
    """Schedule information"""
    def __init__(self, users: "List[User]", shifts: "List[Shift]", preferences: "List[ShiftPreference]"):
        self.users = users
        self.shifts = shifts
        self.preferences = preferences
        self._shifts_for_day = None
        self.user = {u.id:u for u in users} # index id
        self.shift = {s.id:s for s in shifts} # index id
        self._preference = None
    @property
    def shifts_for_day(self) -> "Dict[date]":
        """Collects shifts for a given day for each day, 
        in order of start time
        Returns:
            dict[date] = [s1, s2, ...]
        """
        if self._shifts_for_day is not None:
            return self._shifts_for_day # cached result
        self._shifts_for_day = dict()
        # Collect shifts for day
        for shift in self.shifts:
            day = shift.begin.date()
            if day not in self._shifts_for_day:
                self._shifts_for_day[day] = [shift]
            else:
                self._shifts_for_day[day].append(shift)
        # Sort
        for lst in self._shifts_for_day.values():
            lst.sort()
        return self._shifts_for_day
    @property
    def preference(self) -> "Dict[ShiftId, UserId]":
        """Collect priority number for each shift and user"""
        if self._preference is not None:
            return self._preference # cached result
        self._preference = dict()
        for pref in self.preferences:
            self._preference[pref.user.id, pref.shift.id] = pref.priority
        return self._preference