from datetime import datetime


def server_now() -> datetime:
    """
    Returns the server's local time as a naive datetime.

    Important:
    - Race start_time from the admin form is also naive local time.
    - Therefore scan received_at must use the same time basis.
    """

    return datetime.now()
