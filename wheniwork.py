"""
Wrapper for the WhenIWork API

The get methods return the exact JSON response,
unless stated otherwise.
"""

from datetime import datetime
import requests
from typing import List

class WhenIWorkError(Exception):
    pass

class NoTokenError(WhenIWorkError):
    pass

class WhenIWork:
    def __init__(self, token, user_id):
        self.token = token
        if token is None:
            raise NoTokenError("User doesn't have token specified")
        self.user_id = user_id
    def __get(self, address, params={}) -> dict:
        """
        Send a GET request to WhenIWork, 
        and returns the result as a dictionary
        Args:
            params (dict): the parameters to pass along
        Returns:
            response (dict): the response dictionary
        """
        headers= {"W-Token": self.token, "W-UserId": str(self.user_id)}
        response = requests.get(
            f'https://api.wheniwork.com{address}',
            headers=headers,
            params=params
        )
        response.raise_for_status() # throw if not 200
        return response.json()
    def __post(self, address, data={}):
        """
        Send a POST request to WhenIWork.
        Args:
            data (dict): the data to send
        """
        headers = {"W-Token": self.token, "W-UserId": str(self.user_id)}
        response = requests.post(
            f'https://api.wheniwork.com{address}',
            headers=headers,
            data=data
        )
        response.raise_for_status()
        return response.json()
    @classmethod
    def get_token(cls, api_key: str, email: str, password: str) -> dict:
        response = requests.post(
            'https://api.login.wheniwork.com/login',
            headers={
                "W-Key": api_key,
                'content-type': 'application/json'
            },
            data='{"email":"'+email+'","password":"'+password+'"}',
        )
        response.raise_for_status()
        return response.json()
    def get_locations(self, only_unconfirmed=False) -> "list[dict]":
        """
        Get the locations associated with this workplace
        Args:
            only_unconfirmed (bool): Include only unconfirmed schedules/locations
        Returns:
            resp (list): array of location objects
        """
        params = {'only_unconfirmed': only_unconfirmed}
        locations = self.__get('/2/locations', params=params)['locations']
        return locations
    def create_location(self, params: dict):
        """Create Schedule(Location)
        https://apidocs.wheniwork.com/external/index.html#tag/Schedules-(Locations)/paths/~12~1locations/post
        Arguments:
            params: {
                account_id: int
                name: str
                address: str
                coordinates: [float, float]
                deleted_at: str<date-time>
                ip_address: str<ipv4>
                is_default: bool
                is_deleted: bool
                latitude: float
                longitude: float
                max_hours: int
                place: {
                    address: str
                    business_name: str
                    country: str,
                    id: int,
                    latitude: float,
                    locality: str,
                    longitude: float,
                    place_id: str
                    place_type: [],
                    postal_code: [str,...]
                    region: str,
                    street_name": str,
                    street_number": str,
                    sub_locality": str,
                    updated_at": str<date-time>
                }
                place_confirmed: bool
                place_id: str
                radius: int
                sort: int
                created_at: str<date-time>
                updated_at: str<date-time>
            }
        """
        self.__post('locations', data=params)
    def get_users(self, show_pending=True, show_deleted=False, search=None) -> dict:
        """
        Get users from the workplace
        Returns:
            resp (dict): array under key `users`
        """
        params = {
            'show_pending': show_pending,
            'show_deleted': show_deleted,
            'search': search
        }
        return self.__get('/2/users', params=params)
    def get_positions(self, show_deleted=False) -> dict:
        """
        Get positions from the workplace
        Returns:
            resp (dict): array under key `positions`
        """
        params = { 'show_deleted': show_deleted }
        return self.__get('/2/positions', params=params)
    def get_timeoff_types(self) -> dict:
        """
        Get Time Off Types
        Returns:
            resp (dict): array under key `request-types`
        """
        return self.__get('/2/requesttypes')
    def __get_timeoff_requests_pagination(
            self, 
            start: datetime,
            end: datetime,
            user_id: int = None,
            location_id: int =None,
            max_id: int = None,
            limit: int = 5,
            page: int = 0,
            since_id: int = None,
            sortby: str = None,
            include_deleted_users: bool = False,
            type: int = None
        ) -> dict:
        """
        Get Time Off Requests
        Used for pagination
        Returns:
            resp (dict): array under key `requests`
        """
        params = {
            'start': start,
            'end': end,
            'user_id': user_id,
            'location_id': location_id,
            'max_id': max_id,
            'limit': limit,
            'page': page,
            'since_id': since_id,
            'sortby': sortby,
            'include_deleted_users': include_deleted_users,
            'type': type
        }
        return self.__get('/2/requests', params=params)
    def get_timeoff_requests(
            self, 
            start: datetime,
            end: datetime,
            user_id: int = None,
            location_id: int =None,
            max_id: int = None,
            since_id: int = None,
            sortby: str = None,
            include_deleted_users: bool = False,
            type: int = None
        ) -> "list[dict]":
        """
        Get all Time Off request objects
        Returns:
            resp (list): array of requests 
        """
        timeoff = []
        total = 201 # default total, will be reset
        page = 0
        while page * 200 < total:
            resp = self.__get_timeoff_requests_pagination(
                start, 
                end, 
                user_id=user_id, 
                location_id=location_id,
                max_id=max_id,
                since_id=since_id,
                sortby=sortby,
                include_deleted_users=include_deleted_users,
                type=type,
                limit=200,
                page=page
            )
            page += 1
            total = resp['total'] # Make sure the total is right
            timeoff += resp['requests'] # Add request objects
        return timeoff
    def get_availabilities(self, start:datetime=None, end:datetime=None, user_id=None, include_all=None) -> dict:
        """
        Returns:
            resp (dict): array under the key `availabilityevents`
        """
        params = {
            'start': start,
            'end': end,
            'user_id': user_id,
            'include_all': include_all
        }
        return self.__get('/2/availabilityevents', params=params)
    def get_shifts(self, start:datetime, end:datetime, unpublished: bool=False, **kwargs) -> "List[dict]":
        kwargs.update(
            {
                'start': start.isoformat(),
                'end': end.isoformat(),
                'unpublished': unpublished
            }
        )
        return self.__get('shifts', params=kwargs)
    def create_shift(self, location, start:datetime, end:datetime, **kwargs):
        kwargs.update(
            {
                'location_id': location,
                'start_time': start.isoformat(),
                'end_time': end.isoformat()
            }
        )
        self.__post('shifts', data=kwargs)
