"""

"""
from random import randint

#** Variables **#
__all__ = ['new_message_id']

#** Functions **#

def new_message_id() -> int:
    """
    generate a new valid id for a dns message packet

    :return: new valid message-id integer
    """
    return randint(1, 2 ** 32)
