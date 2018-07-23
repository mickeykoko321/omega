import dateutil.relativedelta as rd
import datetime as dt
import logging
import pandas as pd

import omega.data.cot as odc
import omega.data.utils as odu
import omega.core.instrument as i


def calculate_vars(trades):
    """
    
    :return: 
    """
    log = logging.getLogger(__name__)

    # Get Dates
    months = [1, 3, 6, 12]
    today = dt.datetime.today()
    dates = [today + rd.relativedelta(months=-m) for m in months]
    # Calculate standard deviations for each number of months
    df_vars = []
    for k, t in trades.items():
        # Do not process IN trades
        if 'IN' not in k or 'SP' not in k:
            log.debug('Process trade: {}'.format(k))
            df = odu.read_csv(*t['Symbols'], weights=t['Weights'],
                              start_date=dates[-1].strftime('%Y-%m-%d'), date_as_index=False)
            stds = [df[df['Date'] >= d]['Close'].std() for d in dates]
            df_vars.append([k] + stds)
    # Return dataframe
    return pd.DataFrame(df_vars, columns=['Trade'] + ['m{}'.format(m) for m in months])


def calculate_stds(df, length=20):
    """Calculate standard deviations for the spread in the specified dataframe. Returns a dataframe with a few
    extra columns. This is to be used in Excel.

    :param df: DataFrame universe of traded symbols
    :param length: Length for the standard deviation
    :return: DataFrame with results
    """
    log = logging.getLogger(__name__)

    df_stds = []
    for idx, row in df.iterrows():
        ticker = row['Ticker']
        log.debug('Process spread: {}'.format(ticker))
        # STD
        dfm = odu.get_market_df(ticker)
        if dfm is not None:
            dfm = dfm.tail(length)
            std = dfm['Close'].std()
        else:
            std = 0
        # COT
        cdf = odc.cot_data(ticker[0:2])
        hps = cdf.iloc[-1]['HPS']
        hph = cdf.iloc[-1]['HPH']
        # Add data
        df_stds.append({'Ticker': ticker, 'LastDate': row['LastDate'], 'DaysTo': row['DaysTo'],
                        'HPS': hps, 'HPH': hph, 'PVol':  std, 'IVol': std * i.get(ticker[0:2], 'Point')})
    # Return dataframe
    return pd.DataFrame(df_stds, columns=['Ticker', 'LastDate', 'DaysTo', 'HPS', 'HPH', 'PVol', 'IVol'])

