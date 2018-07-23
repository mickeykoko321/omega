import re

"""Module Filter Logs
Filter logs on specific criteria
"""


def by_strings(file, strings):
    """Filter logs by a list of strings. We return all the lines which contains the specific strings in the list.

    :param file: str - Log file path
    :param strings: list - Strings to find in the logs
    :return: list - Lines containing the strings
    """
    ls = len(strings)
    lines = []
    with open(file, mode='r') as f:
        for line in f:
            matches = re.findall('|'.join(strings), line)
            if ls == len(set(matches)):
                lines.append(line)

    return lines
