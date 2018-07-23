import datetime as dt
import logging
import pandas.tseries.offsets as o

import omega.xl.spreading as oxs


def to_trade_name(trade, symbols, weights):
    """Given a trade, symbols and weight - Create a Trade Name (used for Curvature trade display)

    :param trade: str - Trade name
    :param symbols: list - All symbols in the trade
    :param weights: list - All weights per symbol
    :return: str - Trade Name
    """
    log = logging.getLogger(__name__)

    name = ''
    for idx, s in enumerate(symbols):
        w = '{} * '.format(abs(weights[idx])) if abs(weights[idx]) != 1 else ' '
        sign = (' + ' if weights[idx] > 0 else ' - ') if idx > 0 else ''
        name += '{}{}{}'.format(sign, w, s)
    trade_name = '{}:{}'.format(trade, name)
    log.debug('Trade name: {}'.format(trade_name))

    return trade_name


def daily_differences(universe=None, date=None):
    """ Daily differences in the symbols. Tracks additions and deletions (new symbol and expired).

    :param universe: list: Not necessary, if not specified will use Excel.
    :param date: If specified, returns the differences for a specific date (today is set to default)
    :return: list - Tuple of lists
    """
    log = logging.getLogger(__name__)

    day = dt.datetime.today() if date is None else dt.datetime.strptime(date, '%Y-%m-%d')
    to = oxs.daily_trade(universe, day.strftime('%Y-%m-%d'))
    ye = oxs.daily_trade(universe, (day - o.BDay(1)).strftime('%Y-%m-%d'))

    sto = set(to['Ticker'])
    log.debug('Today''s Markets: {}'.format(sto))
    sye = set(ye['Ticker'])
    log.debug('Yesterday''s Markets: {}'.format(sye))
    # Adds - Dels
    adds = list(sto.difference(sye))
    dels = list(sye.difference(sto))
    log.info('Additions (to check): {}'.format(adds))
    log.info('Deletions (to check): {}'.format(dels))

    return adds, dels
