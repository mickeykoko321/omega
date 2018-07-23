import datetime as dt
import eikon as ek
import json
import logging
import os
import pandas as pd
import pandas.tseries.offsets as o
import requests as req
import subprocess as sub
import time

import omega.core.instrument as oci
import omega.core.lists as ocl
import omega.data.cleaning as odc
import omega.data.utils as odu


"""Download module

This module is used for anything related to download data from Reuters. Will be used mainly for Daily download although
it should support minute download.
"""


def eikon(func):
    """Check if Eikon has been started, start it if it hasn't. Will be used as a decorator.

    :param func: Function to be decorated
    """
    def wrapper_func(*args, **kwargs):
        log = logging.getLogger(__name__)

        # Check if Eikon is running (if not start it)
        ps = os.popen('tasklist').read()
        if 'EikonBox' not in ps:
            log.info('Start Eikon and wait 60 seconds for initialization')
            sub.Popen(r'C:\Program Files (x86)\Thomson Reuters\Eikon\Eikon.exe')
            time.sleep(120)
        # API Key for Eikon
        ek.set_app_id('a3613aeaa2a14b6ea8aaff7950114a2d19bdc03a')
        # Execute Function
        ret_val = func(*args, **kwargs)
        return ret_val
    return wrapper_func


def eikon_proxy(func):
    """Check if Eikon proxy has been started, start it if it hasn't. Will be used as a decorator.

    :param func: Function to be decorated
    """
    def wrapper_func(*args, **kwargs):
        log = logging.getLogger(__name__)

        p = None
        # Check if Proxy is running (if not start it)
        ps = os.popen('tasklist').read()
        if 'EikonAPIProxy' not in ps:
            log.info('Start Eikon Proxy and wait 60 seconds for initialization')
            p = sub.Popen(r'C:\Users\Laurent\AppData\Local\Eikon API Proxy\EikonAPIProxy.exe')
            time.sleep(60)
        # API Key for Eikon
        ek.set_app_id('a3613aeaa2a14b6ea8aaff7950114a2d19bdc03a')
        # Execute Function
        ret_val = func(*args, **kwargs)
        # Terminate process
        if p is not None:
            p.terminate()
        return ret_val
    return wrapper_func


@eikon
def get_ohlcv_data(ticker, interval, start, end):
    """Download OHLCV data from Reuters, can either be daily or minute data

    :param ticker: String customized ticker
    :param interval: Interval for the data download (daily or minute)
    :param start: String start date
    :param end: String end date
    :return: Dataframe OHLCV format
    """
    log = logging.getLogger(__name__)

    ric = oci.convert_ticker(ticker, 'Reuters')
    log.info('Download data for: {} - RIC: {}'.format(ticker, ric))
    try:
        # Directly prints to the console if there's an issue - TODO: how to catch this?
        df = ek.get_timeseries(ric, start_date=start, end_date=end, interval=interval, fields=['HIGH', 'LOW', 'OPEN', 'CLOSE', 'VOLUME'])
        df.index.names = [None]
        df.columns = ['High', 'Low', 'Open', 'Close', 'Volume']
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        # Remove weekend days
        df = df[df.index.dayofweek < 5]
        # Settlement Fix (old spreads don't have settlements so need to get the close)
        close = pd.isnull(df['Close'])
        if len(close[close]) > 1 and oci.get_future_type(ticker) == oci.FutureType.Spread:
            df = fix_settlement(ticker, df)
        # Fill NAs
        df['Open'].fillna(df['Close'], inplace=True)
        df['High'].fillna(df['Close'], inplace=True)
        df['Low'].fillna(df['Close'], inplace=True)
        df['Volume'].fillna(0, inplace=True)
        # Add OI: Only for outrights and if the outright has traded
        vdf = df[df['Volume'] > 0]
        if len(vdf) > 0 and oci.get_future_type(ticker) == oci.FutureType.Outright:
            # Have to do this as the OI would shift it we start early (and there's no OI for some days)
            first_trade = str(vdf.index[0])[0:10]
            df = add_oi(ticker, df, first_trade, end) if interval is 'daily' else df
        else:
            df['OI'] = pd.Series([0 for _ in range(len(df.index))], index=df.index)
        # Check if first line has NAs and discard them
        # TODO: Move this in a function?
        if oci.get_future_type(ticker) == oci.FutureType.Outright and len(df) > 20:
            drop = []
            for i in range(20):
                if df.iloc[i].isnull().sum():
                    drop.append(i)
            if drop:
                log.warning('Dropping lines: {}'.format(drop))
                df = df.drop(df.index[drop])
    except (TypeError, IndexError, req.HTTPError, ek.eikonError.EikonError, json.decoder.JSONDecodeError) as e:
        log.error('Problem downloading data for {}, see: {}'.format(ticker, e))
        df = None

    return df


@eikon
def fix_settlement(ticker, df, replace=True):
    """This is a hack as for spreads, the settlement wasn't published so get_timeseries returns NaN. We need to replace
    this by the close (there's no option in Reuters unfortunately).

    :param ticker: String customized ticker
    :param df: Dataframe OHLCV format
    :param replace: bool - if we need to replace the missing closes (if False, returns the closes)
    :return: Dataframe
    """
    log = logging.getLogger(__name__)

    ric = oci.convert_ticker(ticker, 'Reuters')
    log.info('Fix Settlement for: {} - RIC: {}'.format(ticker, ric))
    # Get Data
    fields = ['TR.CLOSEPRICE.date', 'TR.CLOSEPRICE']
    cdf = get_data(ric, str(df.index[0])[0:10], str(df.index[-1])[0:10], fields, ['Instrument', 'Close2'])
    # Replace
    if replace:
        df = df.join(cdf['Close2'])  # Hack to avoid having to convert from string to datetime index
        # TODO: See if we can do that only for missing values???
        df['Close'].fillna(df['Close2'], inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    else:
        return cdf


def add_oi(ticker, df, start, end):
    """Download Open Interest and add it to an already existing Dataframe. Only works for daily data

    :param ticker: String customized ticker
    :param df: Dataframe OHLCV format
    :param start: String start date
    :param end: String end date
    :return: Dataframe
    """
    log = logging.getLogger(__name__)

    ric = oci.convert_ticker(ticker, 'Reuters')
    log.info('Add OI to: {} - RIC: {}'.format(ticker, ric))
    # Get Data and add it to the DataFrame
    fields = ['TR.OPENINTEREST.date', 'TR.OPENINTEREST']
    oi = get_data(ric, start, end, fields, ['Instrument', 'OI'])
    df = df.join(oi['OI'])
    # Fill NAs
    df['OI'].fillna(0, inplace=True)

    return df


def get_data(ric, start, end, fields, columns):
    """Generic Function to get data from Reuters, format the DataFrame to how we use the data in the application.

    :param ric: String ric
    :param start: String start date
    :param end: String end date
    :param fields: List fields to download
    :param columns: List column names to use in the new Dataframe
    :return: Dataframe
    """
    log = logging.getLogger(__name__)

    log.debug('Get Data for {}, fields: '.format(ric, fields))
    df, err = ek.get_data(ric, fields, parameters={'SDate': start, 'EDate': end})
    # Transform
    df['Date'] = df.apply(lambda x: str(x['Date'])[0:10], axis=1)
    df.set_index('Date', inplace=True)
    df.index.names = [None]
    df.columns = columns

    return df


@eikon
def download_list(status, symbols=None, interval='daily', override_last=False):
    """Download all data for a specific list as defined in the list module.

    :param status: Enum Status - Active/ActivePlus/All/Expired Status
    :param symbols: List of symbols to download (Stem should be provided) - If not provided, will go through the universe
    :param interval: String data interval, possible values: 'minute', 'daily' or both
    :param override_last: bool - To force re-downloading data for current day
    """
    log = logging.getLogger(__name__)

    log.info('Download {}'.format(interval))
    symbols = oci.json_db if symbols is None else symbols
    for m in symbols:
        log.debug('Download data for {}'.format(m))
        # Generate tickers for download
        sdf = ocl.generate_tickers_df(m, status)
        # Go through all tickers
        for idx, row in sdf.iterrows():
            ticker = row['Ticker']
            # Get last entry
            odf = odu.get_market_df(ticker)
            last_date = '1900-01-01'
            start = '1900-01-01'
            if odf is not None:
                last_date = dt.datetime.strftime(odf.index[-1], '%Y-%m-%d')
                start = dt.datetime.strftime(odf.index[-1] - o.BDay(3), '%Y-%m-%d')
            if last_date != dt.datetime.today().strftime('%Y-%m-%d') or override_last:
                # Download Data & Save to the file
                df = get_ohlcv_data(ticker, interval, start, dt.datetime.today().strftime('%Y-%m-%d'))
                if df is not None:
                    odu.save_market_df(ticker, df)
            else:
                log.info('Do not download {} as it has already been downloaded'.format(ticker))


@eikon
def download_missing(symbols=None, filter=None):
    """Download missing maturities (a missing maturity means that it doesn't have a text file in the
    database).

    :param symbols: List of symbols to download (Stem should be provided) - If not provided, will go through the universe
    :param filter: number - If provided will filter out the no data list
    """
    log = logging.getLogger(__name__)

    symbols = oci.json_db if symbols is None else symbols
    for m in symbols:
        log.debug('Download missing data for {}'.format(m))
        check = odc.check_has_data([m])
        if filter:
            assert isinstance(filter, int), 'Provided filter is not an integer!'
            check = [c for c in check if int(c[-2:]) >= filter]
        for ticker in check:
            log.debug('Get data for: {}'.format(ticker))
            df = get_ohlcv_data(ticker, 'daily', '1900-01-01', dt.datetime.today().strftime('%Y-%m-%d'))
            if df is not None:
                odu.save_market_df(ticker, df)
            else:
                log.debug('No data for {}'.format(ticker))

