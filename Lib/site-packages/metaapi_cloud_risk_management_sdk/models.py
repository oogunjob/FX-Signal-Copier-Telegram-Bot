from datetime import datetime
from typing_extensions import TypedDict
from typing import List, Optional
import iso8601
import random
import string
import pytz
import traceback


def date(date_time: str or float or int or datetime) -> datetime:
    """Parses a date string into a datetime object."""
    if isinstance(date_time, float) or isinstance(date_time, int):
        return datetime.fromtimestamp(max(date_time, 100000)).astimezone(pytz.utc)
    elif isinstance(date_time, datetime):
        return date_time
    else:
        return iso8601.parse_date(date_time)


def format_date(date_object: datetime or str) -> str:
    """Converts date to format compatible with JS"""
    if isinstance(date_object, datetime):
        return date_object.astimezone(pytz.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    else:
        return date_object


def random_id(length: int = 32) -> str:
    """Generates a random id of 32 symbols."""
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


class ValidationDetails(TypedDict):
    """Object to supply additional information for validation exceptions."""
    parameter: str
    """Name of invalid parameter."""
    value: Optional[str]
    """Entered invalid value."""
    message: str
    """Error message."""


class ExceptionMessage(TypedDict):
    """A REST API response that contains an exception message"""
    id: int
    """Error id"""
    error: str
    """Error name"""
    numericCode: Optional[int]
    """Numeric error code"""
    stringCode: Optional[str]
    """String error code"""
    message: str
    """Human-readable error message"""
    details: Optional[List[ValidationDetails]]
    """Additional information about error. Used to supply validation error details."""


def convert_iso_time_to_date(data):
    """Converts time fields of incoming data into datetime."""
    if not isinstance(data, str):
        for field in data:
            if isinstance(data,  dict):
                value = data[field]
            else:
                value = field
            if isinstance(value, str) and field in ['closeAfter', 'stoppedAt', 'stoppedTill', 'startTime', 'time',
                                                    'updateTime']:
                data[field] = date(value)
            if isinstance(value, list):
                for item in value:
                    convert_iso_time_to_date(item)
            if isinstance(value, dict):
                convert_iso_time_to_date(value)


def format_request(data: dict or list):
    """Formats datetime fields of a request into iso format."""
    if not isinstance(data, str):
        for field in data:
            if isinstance(data, dict):
                value = data[field]
            else:
                value = field
            if isinstance(value, datetime):
                data[field] = format_date(value)
            elif isinstance(value, list):
                for item in value:
                    format_request(item)
            elif isinstance(value, dict):
                format_request(value)


def format_error(err: Exception or any):
    """Formats and outputs metaApi errors with additional information.

    Args:
        err: Exception to process.
    """
    error = {'name': err.__class__.__name__, 'message': err if isinstance(err, str) or err is None else (
        err.args[0] if len(err.args) else None)}
    if hasattr(err, 'status_code'):
        error['status_code'] = err.status_code
    if err.__class__.__name__ == 'ValidationException':
        error['details'] = err.details
    if err.__class__.__name__ == 'TradeException':
        error['string_code'] = err.stringCode
    if err.__class__.__name__ == 'TooManyRequestsException':
        error['metadata'] = err.metadata
    error['trace'] = traceback.format_exc()
    return error
