import datetime as dt
import logging
import pandas as pd
import sys

import omega.cabbage.risk as r
import omega.configuration as c
import omega.core.instrument as i
import omega.core.lists as li
import omega.xl.utils as oxu
import omega.xl.excel as excel

import omega.configuration as oc

from arctic import Arctic
import urllib.parse
import omega.data.utils as odu

"""Curvature module

This module is used for specific interaction between the curvature strategy and its excel sheet for monitoring.
"""

# Curvature book
book = 'curvature'


def update_risk():
    """Update risk, this will refresh all the VaR values and copy them directly to the sheet. See the relevant function
    if we need to amend the values to be calculated.
    """
    log = logging.getLogger(__name__)

    wbc = excel.init(book)
    log.debug('Update risk on Book {}'.format(book))
    excel.update_sheet(wbc, 'Analysis', 'A3:E28', r.calculate_vars(get_trades()))


def populate(provider='Reuters'):
    """Populate the sheet with current traded tickers

    :param provider: str - Data Provider
    """
    log = logging.getLogger(__name__)

    wbc = excel.init(book)
    log.debug('Populate workbook {}'.format(book))
    tickers = li.generate_curvature_list()
    excel.populate_workbook(wbc, tickers, provider)


@excel.screen_updating
def positions(symbol):
    """Refresh the positions in the Positions sheet, this is used to calculate our outright positions.

    :param symbol: Which symbol to refresh (only ED or FF)
    """
    log = logging.getLogger(__name__)

    wbc = excel.init(book)
    log.debug('Transactions Sheet')
    sheet = wbc.sheets['Transactions']
    if len(symbol) > 2:
        log.error('Symbol needs to be a stem!')
        sys.exit(1)
    if 'ED' in symbol:
        log.debug('Getting the range for  ED')
        rng = 'F4:G29'
        cell = 'F4'
    elif 'FF' in symbol:
        log.debug('Getting the range for FF')
        rng = 'F35:G46'
        cell = 'F35'
    else:
        log.error('Symbol not defined!')
        sys.exit(1)
    log.debug('Get the data and transform it')
    df = sheet.range('A1').expand().value
    df = pd.DataFrame(df[1:], columns=df[0])
    df['Position'] = df.apply(lambda x: x['Qty'] if x['Side'] == 'BUY' else -x['Qty'], axis=1)
    dfg = df[df['DateOut'].isnull() & df['Symbol'].notnull() & df['Symbol'].str.contains(symbol)]
    dfg = dfg.groupby(['Symbol'])['Position'].sum().reset_index()
    log.debug('Copy the data to the sheet')
    wbc.sheets['Positions'].range(rng).clear_contents()
    wbc.sheets['Positions'].range(cell).options(index=False, header=False).value = dfg


def snap_quotes():
    """Function to be called at 4pm to save curve history. This is then used to playback the curve changes.
    """
    log = logging.getLogger(__name__)

    wbc = excel.init(book)
    today = dt.datetime.today().strftime('%Y%m%d')
    path = '{}\{}-quotes.txt'.format(c.cfg['default']['quotes'], today)
    # Check if it's been done already today
    if excel.check_status(wbc, 'AA1'):
        log.info('Snap Quotes has already ran today!')
        return
    # Get quotes
    df = wbc.sheets['Quotes'].range('A1').expand().value
    df = pd.DataFrame(df[1:], columns=df[0])
    df = df[(df['Generated'] != 'Manual') & df['Ticker'].str.contains('ED')][['Ticker', 'WP']]
    # Only spreads or butterflies!
    df = df[df['Ticker'].str.contains('S') | df['Ticker'].str.contains('B')]
    # Get list of maturities
    lm = wbc.sheets['Monitor'].range('B7').expand('down').value
    lm = [t[-2:] for t in lm]
    # Convert to constant maturities
    df['Constant'] = df['Ticker'].map(lambda x: i.to_constant_contract(x, lm))
    df = df[['Constant', 'Ticker', 'WP']]

    df.to_csv(path, index=False, header=False, float_format='%.2f')

    # Change today's import status
    excel.update_status(wbc, 'AA1')


def get_trades():
    """Get a dictionary of the Curvature strategy active trades with the associated symbols and weights.

    :return: Dictionary of trades
    """
    log = logging.getLogger(__name__)

    wbc = excel.init(book)
    log.debug('Get Curvature active trades')
    sheet = wbc.sheets['Trades']
    df = sheet.range('A11:AC11').expand('down').value
    df = pd.DataFrame(df[1:], columns=df[0])
    # Remove None rows as this is the top row for the trade
    df = df[df['Symbol'].notnull()]
    # Get Trades
    ts = set(df['Trade'].values)
    ts = sorted(ts, key=str.lower)
    # Dictionary of trades
    trades = dict()
    for t in ts:
        t_df = df[df['Trade'] == t]
        symbols = t_df['Symbol'].values.tolist()
        weights = t_df['W'].values.tolist()
        trades[t] = {'Name': oxu.to_trade_name(t, symbols, weights), 'Symbols': symbols, 'Weights': weights}
    return trades