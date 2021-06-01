from datetime import datetime, date, timedelta, tzinfo, time
from typing import List, Dict, Tuple, Any, NewType
UserId = NewType('UserId', Any)
ShiftId = NewType('ShiftId', int)

class Shift:
    """Shift timeframe and capacity
    Sorts based on begin time
    """
    def __init__(self, id: ShiftId, begin: datetime, end: datetime, capacity: int, position: int):
        self.id = id
        assert begin < end
        self.begin = begin
        self.end = end
        self.capacity = capacity
        self.position = position
    @property
    def length(self) -> timedelta:
        return self.end - self.begin
    @property
    def is_long(self) -> bool:
        return self.length > timedelta(hours=6)
    @property
    def starts_early(self) -> bool:
        return self.begin.time() < time(9, 00)
    @property
    def ends_late(self) -> bool:
        return self.end.time() > time(22,00) or self.begin.date() < self.end.date()
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
    def __init__(self, id: UserId, positions: List[int], min_hours: float, max_hours: float, only_long: bool, min_long: int):
        self.id = id
        self.positions = positions
        assert min_hours < max_hours
        self.min_hours = min_hours
        self.max_hours = max_hours
        self.only_long = only_long
        self.min_long = min_long
    def can_take(self, shift: Shift) -> bool:
        return shift.position in self.positions
class ShiftPreference:
    """Stores a User-Shift relation with a preference score"""
    def __init__(self, user: User, shift: Shift, priority: int):
        self.user = user
        self.shift = shift
        self.priority = priority
class Schedule:
    """Schedule information"""
    def __init__(self, users: List[User], shifts: List[Shift], preferences: List[ShiftPreference]):
        self.users = users
        self.shifts = shifts
        self.preferences = preferences
        self._shifts_for_day = None
        self.user = {u.id:u for u in users} # index id
        self.shift = {s.id:s for s in shifts} # index id
        self._preference = None
    @property
    def shifts_for_day(self) -> Dict[date, List[Shift]]:
        """Collects shifts for a given day for each day, 
        in order of start time
        Returns:
            dict[date] = [s1, s2, ...]
        """
        if self._shifts_for_day is not None:
            return self._shifts_for_day # cached result
        # Collect days in order
        days = []
        for s in self.shifts:
            day = s.begin.date()
            if day not in days:
                days.append(day)
        days.sort()
        self._shifts_for_day = {day:[] for day in days}
        # Collect shifts for day
        for shift in self.shifts:
            day = shift.begin.date()
            self._shifts_for_day[day].append(shift)
        # Sort
        for lst in self._shifts_for_day.values():
            lst.sort()
        return self._shifts_for_day
    @property
    def preference(self) -> Dict[Tuple[ShiftId, UserId], int]:
        """Collect priority number for each shift and user"""
        if self._preference is not None:
            return self._preference # cached result
        self._preference = dict()
        for pref in self.preferences:
            self._preference[pref.shift.id, pref.user.id] = pref.priority
        return self._preference