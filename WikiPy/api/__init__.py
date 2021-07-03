"""
This module defines functions to interact with database models. As such, models should NEVER be created, modified or
saved directly, but ALWAYS through functions from this module as they perform security and integrity checks.
"""
from ._diff import *
