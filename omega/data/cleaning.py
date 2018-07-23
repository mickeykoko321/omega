import logging
import math
import os
import os.path as op
import pandas as pd

import omega.configuration as oc
import omega.core.instrument as oci
import omega.core.chain as occ
import omega.core.lists as ocl
import omega.data.utils as odu


"""Cleaning module

This module is used for data cleaning purposes. Following methods:
-- Inspect Files: Find missing data in all files
-- Inspect Contracts: Based on letters and table, find where we are missing data files
"""


class CleaningError(Exception):
    pass


def inspect_files(stems=None, future_type=None):
    """File inspection. Go through all the datafiles in the Daily folder and check for missing values.

    :param stems: list - List of Futures to inspect
    :param future_type: enum FutureType - Type of Futures to inspect (Outright, Spread, etc...)
    :return: dict - Problematic tickers to be checked
    """
    log = logging.getLogger(__name__)

    inspect = {}
    for root, dirs, files in os.walk(op.join(oc.cfg['default']['data'], 'Daily')):
        for f in files:
            ticker = f.split('.')[0]
            if stems is not None and ticker[0:2] not in stems:
                continue
            if future_type is not None and oci.get_future_type(ticker) != future_type:
                continue
            df = odu.get_market_df(ticker)
            if df is not None:
                missing = df.isnull().sum().sum()
                if missing > 0:
                    inspect[ticker] = missing

    return inspect


def check_has_data(stems=None):
    """Check if all tickers in the table have data

    :param stems: list - List of Futures to inspect
    :return: list - Problematic tickers to be checked
    """
    if not isinstance(stems, list):
        raise CleaningError('A list must be provided as an argument!')

    check = []
    symbols = oci.json_db if stems is None else stems
    for m in symbols:
        # Expired + Active Tickers (All would give too many tickers in the future)
        dfe = ocl.generate_tickers_df(m, occ.Status.Expired)
        dfa = ocl.generate_tickers_df(m, occ.Status.Active)
        df = pd.concat([dfe, dfa])
        for idx, row in df.iterrows():
            ticker = row['Ticker']
            file = odu.get_file_path(ticker)
            if not op.exists(file):
                check.append(ticker)

    return check


def try_fix_missing(ticker):
    """Attempt to fix missing values in DataFrame by using rules

    :param ticker: str - Customized ticker
    :return: Number of missing values left
    """
    log = logging.getLogger(__name__)

    # Get DataFrame
    df = odu.get_market_df(ticker)
    before = df.isnull().sum().sum()
    log.debug('Missing values before: {}'.format(before))

    fields = ['Open', 'High', 'Low', 'Close']
    for idx in range(len(df)):
        row = df.iloc[idx]
        rvals = row[fields]
        missing = rvals.isnull().sum()
        # Rule 1: If 3 missing values, then all values should be equal!
        if missing == 3:
            value = rvals.dropna()[0]
            df.iloc[idx] = row.fillna(value)
        # Rule 2: If Open and Close are missing, then Low goes to Open and High to Close
        if missing == 2 and math.isnan(row['Open']) and math.isnan(row['Close']):
            df.iloc[idx]['Open'] = row['Low']
            df.iloc[idx]['Close'] = row['High']
    # Save DataFrame
    odu.save_market_df(ticker, df)
    after = df.isnull().sum().sum()
    log.warning('Missing values after: {} - fixed: {}'.format(after, before - after))

    return after
