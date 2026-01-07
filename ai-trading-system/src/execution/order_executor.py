"""Order execution logic."""

from .broker_api import place_order


def execute_order(order):
    return place_order(order)
