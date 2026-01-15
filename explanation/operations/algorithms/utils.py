#!/usr/bin/env python
"""Provides utility functions."""
from typing import List, Tuple


def split(clauses: List) -> Tuple[List, List]:
    """
    Splits the given list of constraints/clauses into two parts.
    clauses could be a list of integers or a list of lists.
    :param clauses: a list of clauses
    :return: a tuple of two lists
    """
    half_size = len(clauses) // 2
    return clauses[:half_size], clauses[half_size:]


def diff(list_x: List, list_y: List) -> List:
    """
    Returns the difference of two lists.
    list_x and list_y could be a list of integers or a list of lists.
    :param list_x: list
    :param list_y: list
    :return: list
    """
    return [item for item in list_x if item not in list_y]


def get_hashcode(clauses: List) -> str:
    """
    Returns the hashcode of the given CNF formula.
    :param clauses: a list of clauses
    :return: the hashcode of the given CNF formula
    """
    # clauses = sorted(clauses, key=lambda x: x[0])
    clauses = sorted(clauses)
    return str(clauses)


def has_intersection(list1: List, list2: List) -> bool:
    """
    Check if two lists have at least one common element.
    Ex: has_intersection([[1, 2], [3, 4], [5, 6]], [[1, 2], [5, 6]]) returns True
    has_intersection([[1, 2], [3, 4], [5, 6]], [[7, 8], [9, 10]]) returns False
    :param list1:
    :param list2:
    :return:
    """
    return any(i in list1 for i in list2)


def contains(list_of_lists: List[List], a_list: List) -> bool:
    """
    Check if a list of lists contains a specific list.
    Ex: contains([[1, 2], [3, 4]], [1, 2]) returns True
    """
    return any(a_list == x for x in list_of_lists)


def contains_all(greater: List, smaller: List) -> bool:
    """
    Check if a list contains all elements of another list.
    Ex: contains_all([1, 2, 3, 4, 5], [1, 2]) returns True
    :param greater:
    :param smaller:
    :return:
    """
    return all(i in greater for i in smaller)
