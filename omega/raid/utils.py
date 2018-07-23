import calendar as cal
import importlib as ilib
import json
import logging
import os

import backtrader as bt

import omega.core.instrument as oci
import omega.data.utils as odu


class UtilsError(Exception):
    pass


def days_in_between(calendar, first, second):
    """Number of business days in between 2 dates

    :param calendar: list - Business days calendar
    :param first: date - First Date
    :param second: date - Second Date
    :return: int - Number of days
    """
    idx1 = calendar.get_loc(first)
    idx2 = calendar.get_loc(second)

    return idx2 - idx1


def third_friday(year, month):
    """Returns the date for the 3rd Friday of the month.

    :param year: int - Year
    :param month: int - month
    :return: datetime.date - Date
    """
    c = cal.Calendar(firstweekday=cal.SUNDAY)
    month_cal = c.monthdatescalendar(year, month)
    fridays = [day for week in month_cal for day in week if day.weekday() == cal.FRIDAY and day.month == month]

    return fridays[2]


def business_days(calendar, date):
    """Returns an integer indicating the xth number day in the month.

    :param calendar: list - Business days calendar
    :param date: date - Date to be checked
    :return: int - xth day in the month
    """
    first = date.replace(day=1).strftime('%Y-%m-%d')
    days = calendar[calendar >= first]
    return days.get_loc(date) + 1


def add_reference_data(cerebro, start, end):
    """Add Reference data to Cerebro

    :param cerebro: object Cerebro - Backtesting object
    :param start: str - Start Date
    :param end: str - End Date
    :return: object Cerebro
    """
    log = logging.getLogger(__name__)
    log.info('Reference Data - Start: {} - End: {}'.format(start, end))
    data = bt.feeds.PandasData(dataname=odu.create_reference_data(start, end))
    data.plotinfo.plot = False  # Do not plot the Reference
    cerebro.adddata(data, name='Reference')

    return cerebro


class SpreadPandasData(bt.feeds.PandasData):
    """Customized Spread Data for Backtrader: Add the rollyield column"""
    lines = ('rollyield',)
    params = (('openinterest', 5), ('rollyield', 6))
    datafields = bt.feeds.PandasData.datafields + (['rollyield'])


def add_chain_data(cerebro, chains, with_comms=False):
    """Add all data from a future chain to Cerebro

    :param cerebro: object - Cerebro instance from Backtrader
    :param chains: list of object FutureChain - FutureChain to be added to Cerebro
    :param with_comms: bool - Add commissions with the data
    :return: object Cerebro
    """
    # Add Data to Cerebro
    for chain in chains:
        # Commissions - Note: When throwing margin rejects => due to missing data
        comms = bt.CommissionInfo(commission=chain.commission * 2, margin=chain.margin, mult=chain.point)
        # Add all data series
        for ct in chain.contracts:  # [0:15]
            # TODO: Check if missing data compared to Reference!
            if chain.future_type == oci.FutureType.Spread:
                data = SpreadPandasData(dataname=chain.data[ct])
            else:
                data = bt.feeds.PandasData(dataname=chain.data[ct])
            data.plotinfo.plot = False  # Do not plot this data
            cerebro.adddata(data, name=ct)
            # Commissions
            if with_comms:
                cerebro.broker.addcommissioninfo(comms, name=ct)
    return cerebro


def amend_parameters_for_optimization(params):
    """Amend Parameters for optimization. Backtrader requires tuples to be sent to the optimization engine even
    if a parameter is not to be optimized. If a parameter is to be optimized it will be given as a range.

    :param params: dict - Parameters to be transformed.
    :return: dict - Parameters transformed into a dictionary of tuples
    """
    for k, v in params.items():
        if not isinstance(v, range):
            params[k] = (v,)

    return params 
  

def load_parameters(module):
    """Get default parameters for a strategy (depends on where the module is located).

    :param module: str - Name of the module containing the strategy (the class)
    :return: json - Default Parameters database
    """
    try:
        module = ilib.import_module(module)
        path = os.path.abspath(os.path.dirname(module.__file__))
        parameters_path = os.path.join(path, 'parameters.json')
    except ModuleNotFoundError:
        raise UtilsError('Module: {} not found!'.format(module))
    try:
        return json.loads(open(parameters_path).read())
    except FileNotFoundError:
        raise UtilsError('DefaultParameters JSON file not found @ {}!'.format(parameters_path))

