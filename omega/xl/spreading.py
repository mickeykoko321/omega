import datetime as dt
import json
import logging

import pandas as pd
import pandas.tseries.offsets as o

import omega.configuration as c
import omega.cabbage.risk as r
import omega.core.chain as cc
import omega.core.instrument as i
import omega.xl.excel as excel

"""Spreading module

This module is used for specific interaction between the spreading strategy and its excel sheet for monitoring.
"""

# Spreading book
book = 'spreading'


def update_json_database():
    """Update JSON DB File
    Might need to be deprecated as not really used much, or will be part of a wider module to manage database
    """
    log = logging.getLogger(__name__)

    wbs = excel.init(book)
    log.debug('Update JSON database')
    # Get Universe Dataframe
    universe = wbs.sheets['Universe'].range('A1').expand().value
    universe = pd.DataFrame(universe[1:], columns=universe[0])
    universe.set_index('RIC', inplace=True)
    universe.index.names = [None]

    for index, row in universe.iterrows():
        # Check if CTicker is in the database
        if row['CTicker'] not in i.json_db:
            i.json_db[row['CTicker']] = dict()
        # Add values to the database
        i.json_db[row['CTicker']]['Point'] = row['PointValue']
        i.json_db[row['CTicker']]['Letters'] = []
        i.json_db[row['CTicker']]['Stem'] = {'T4': '', 'CMED': '', 'Reuters': index, 'IQFeed': row['IQFeed']}

    # Save to JSON
    with open(c.cfg['default']['database'], 'w') as json_file:
        json.dump(json.loads(str(i.json_db).replace('\'', '"')), json_file)


def populate(universe=None, provider='Reuters'):
    """Populate the sheet with current traded tickers

    :param universe: list: Not necessary, if not specified will use Excel.
    :param provider: Which data provider
    """
    log = logging.getLogger(__name__)

    wbs = excel.init(book)
    log.debug('Populate workbook {}'.format(book))
    tickers = daily_trade(universe)['Ticker'].tolist()
    # Add outrights
    outrights = []
    for t in tickers:
        ticker = '{}{}'.format(t[0:2], t[-3:])
        outrights.append(ticker)
    tickers = outrights + tickers
    # Populate Workbook
    excel.populate_workbook(wbs, tickers, provider)


def update_risk(universe=None, date=None):
    """Update risk, this will refresh all the std values and copy them directly to the sheet. See the relevant function
    if we need to amend the values to be calculated.

    :param universe: list: Not necessary, if not specified will use Excel.
    :param date: Set a date for the calculations
    """
    log = logging.getLogger(__name__)

    wbs = excel.init(book)
    log.debug('Update risk on Book {}'.format(book))
    df = r.calculate_stds(daily_trade(universe, date))
    excel.update_sheet(wbs, 'Analysis', 'A3:E63', df)


def get_universe(subset='Trade'):
    """Get the commodities universe as described in the excel sheet (with various necessary fields).
    Possibility to bypass this function and provide the traded universe directly.

    :param subset: Traded subset (All, Trade, Research) - Look at sheet for selected universe
    :return: DataFrame with RIC as index
    """
    log = logging.getLogger(__name__)

    wbs = excel.init(book)
    log.debug('Get Universe')
    # Get Universe Dataframe
    universe = wbs.sheets['Universe'].range('A1').expand().value
    universe = pd.DataFrame(universe[1:], columns=universe[0])
    universe.set_index('RIC', inplace=True)
    universe.index.names = [None]
    # Traded subset
    return universe[universe[subset]] if subset != 'All' else universe


def daily_trade(universe=None, date=None, days_back=90):
    """Returns a list of all the current traded spread (which are set to Trade in the universe)

    :param universe: list: Not necessary, if not specified will use Excel.
    :param date: If specified, returns the list for a specific date (today is set to default)
    :param days_back: int - Number of business days to expiration
    :return: DataFrame
    """
    log = logging.getLogger(__name__)

    log.debug('Daily Trade list')
    universe = list(get_universe()['CTicker']) if universe is None else universe
    day = dt.datetime.now().strftime('%Y-%m-%d') if date is None else date
    dfs = []
    for ct in universe:
        fc = cc.FutureChain(ct, i.FutureType.Spread)
        fc.initialize_contracts(cc.Status.Active, nac=4)  # Trade the first 2 spreads
        dfs.append(fc.chain)
    rdf = pd.concat(dfs)
    rdf['DaysTo'] = rdf.apply(lambda x: len(pd.date_range(day, x['LastDate'], freq=o.BDay())), axis=1)
    rdf = rdf[rdf['DaysTo'] <= days_back + 3]  # Added 3

    return rdf.reset_index(drop=True)


if __name__ == '__main__':
    populate()
    # update_risk('2017-10-25')
