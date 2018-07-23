import datetime as dt
import logging
import os
import pandas as pd
import pandas_market_calendars as pmc
import sys

import omega.configuration as oc
import omega.core.instrument as oci

from arctic import Arctic
import urllib.parse

def business_date_range(start, end):
    """From a start and end date, returns a list of business days dates

    :param start: str/datetime - Start Date
    :param end: str/datetime - End Date
    :return: list - Business Dates
    """
    # Convert to datetime
    if not isinstance(start, dt.datetime):
        start = dt.datetime.strptime(start, '%Y-%m-%d')
    if not isinstance(end, dt.datetime):
        end = dt.datetime.strptime(end, '%Y-%m-%d')

    return [d for d in [start + dt.timedelta(days=i) for i in range((end - start).days + 1)] if d.weekday() < 5]


def get_start_date(end, days_back=90, exchange='CME'):
    """From and end date, returns the start date which is the end date minus a number of days back

    :param end: str - End Date (Last Date)
    :param days_back: int - Number of days back for the data (default: 90)
    :param exchange: str - Exchange (used for finding business days)
    :return:
    """
    start = (dt.datetime.strptime(end, '%Y-%m-%d') - dt.timedelta(days=days_back + 60)).strftime('%Y-%m-%d')
    days = pmc.get_calendar(exchange).valid_days(start, end)
    new_start = days[-93:][0]

    return str(new_start)[0:10]


def create_reference_data(start, end):
    """Create a dummy file to contains dates for the whole backtest - this is used as a reference for the backtest
    when not all time series are aligned properly.

    :param start: str/datetime - Start Date
    :param end: str/datetime - End Date
    """
    path = get_file_path('Reference')
    # Go through all the dates
    dates = business_date_range(start, end)
    ld = []
    fields = ['Open', 'High', 'Low', 'Close', 'Volume', 'OI']
    for d in dates:
        ld.append({'Date': d, 'Open': 1, 'High': 2, 'Low': 3, 'Close': 4, 'Volume': 5, 'OI': 6})
    # Create DataFrame
    df = pd.DataFrame(ld)
    df = df.set_index('Date', drop=True)
    df.index.names = [None]
    df = df[fields]

    df.to_csv(path, header=False)

    return df


def roll_yield(ticker, sdf):
    """Calculate the Roll Yield column

    :param ticker: str - Customized Ticker
    :param sdf: DataFrame - Spread DataFrame
    :return: Serie - Roll Yield Serie
    """
    log = logging.getLogger(__name__)

    ms = oci.get_maturities(oci.check_ticker(ticker))
    odf = get_market_df('{}{}'.format(ticker[0:2], ms[0]))
    diff = oci.diff_month(oci.int_maturity(ms[0]), oci.int_maturity(ms[1]))

    return (sdf['Close'] / odf['Close']) * (12 / diff) * 100


def to_index(df, window=20):
    """Provided a serie, calculates its index by normalizing it (this is used for the COT Report)

    :param df: Dataframe
    :param window: Rolling window
    :return: Dataframe
    """
    log = logging.getLogger(__name__)

    return 100 * (df - df.cummin()) / (df.cummax() - df.cummin())


# TODO: Method needs to be amended as this is not correct!
def normalize(df, window=20):
    """Provided a serie, normalize it between -1 and 1 (this is used for the COT Report)

    :param df: Dataframe
    :param window: Rolling window
    :return: Dataframe
    """
    log = logging.getLogger(__name__)

    return 2 * (df - df.cummin()) / (df.cummax() - df.cummin()) - 1


def get_file_path(ticker):
    """Get data path for the ticker (Also returns the path for the dummy reference).

    :param ticker: str - Customized ticker
    :return: str - Path
    """

    root = oc.cfg['default']['data']
    if ticker == 'Reference':
        path = os.path.join(root, 'Reference.txt')
    else:
        ft = oci.get_future_type(ticker)
        path = os.path.join(root, 'Daily', ticker[0:2], str(ft), '{}.txt'.format(ticker))

    return path

def conn_database():
    username = oc.cfg['database']['username']
    password = oc.cfg['database']['password']
    url = oc.cfg['database']['url']
    port = oc.cfg['database']['port']
    auth_db = oc.cfg['database']['auth_db']

    name = urllib.parse.quote_plus(username)
    passw = urllib.parse.quote_plus(password)

    conn = Arctic('mongodb://%s:%s@%s:%s/%s' % (name,passw,url,port,auth_db))
    conn.initialize_library('username.scratch')
    lib = conn['username.scratch']

    return lib

def get_from_database(symbol):
    lib = conn_database()
    df = lib.read(symbol).data
    return df

def save_to_database(symbol, df):
    lib = conn_database()
    lib.write(symbol,df)


def get_market_df(ticker, start_date=None, end_date=None):
    """From a ticker get the data from the data repository and store into a dataframe

    :param ticker: Customized ticker
    :param start_date: Optional parameter start date
    :param end_date: Optional parameter start date
    :return: Dataframe containing the data or None if there's nothing in the database
    """
    log = logging.getLogger(__name__)

    log.debug('Get dataframe for: {}'.format(ticker))
    file = get_file_path(ticker)
    if os.path.exists(file):
        fields = ['Open', 'High', 'Low', 'Close', 'Volume', 'OI']

        ver = oc.cfg['mode']['version']
        if ver == '1':
            # Read Data from csv file
            df = pd.read_csv(file, sep=',', parse_dates=True, header=None, names=fields)
        else:
            # Read Data from database
            it = oci.get_future_type(ticker)
            ticker = 'Daily-{}-{}-{}'.format(ticker[0:2],str(it),format(ticker))
            df = get_from_database(ticker)

        # Remove week end data
        df = df[df.index.dayofweek < 5]
        # Check if data needs to be truncated
        if start_date is not None:
            df = df[df.index >= start_date]
        if end_date is not None:
            df = df[df.index <= end_date]
        # Check if missing data
        if df.isnull().values.any():
            log.warning('Missing data in: {} - Count: {}, please check!'.format(ticker, df.isnull().sum().sum()))
        return df
    else:
        return None


# TODO: Add interval!
def save_market_df(ticker, df):
    """ Save a dataframe to the datastore, this is to be used after a dataframe has been downloaded.

    :param ticker: String customized ticker
    :param df: Dataframe data to be saved to the file
    """
    log = logging.getLogger(__name__)

    log.debug('Save dataframe for {}'.format(ticker))
    it = oci.get_future_type(ticker)
    file = os.path.join(oc.cfg['default']['data'], 'Daily', ticker[0:2], str(it), '{}.txt'.format(ticker))
    if os.path.exists(file):
        ndf = get_market_df(ticker)
        # Filter out all data prior to first date of df
        ndf = ndf[ndf.index < df.index[0]]
        # Concatenate DataFrames
        df = pd.concat([ndf, df])
    else:
        # Create folders if they don't exist
        path_ticker = os.path.join(oc.cfg['default']['data'], 'Daily', ticker[0:2])
        if not os.path.exists(path_ticker):
            os.mkdir(path_ticker)
        path_type = os.path.join(oc.cfg['default']['data'], 'Daily', ticker[0:2], str(it))
        if not os.path.exists(path_type):
            os.mkdir(path_type)
    # Change Volume and OI to Integer
    df['Volume'] = df['Volume'].astype(int)
    df['OI'] = df['OI'].astype(int)

    ver= oc.cfg['mode']['version']
    if ver == '1':
        # Save to file
        df.to_csv(file, header=False)
    else:
        ticker = 'Daily-{}-{}-{}'.format(ticker[0:2],str(it),format(ticker))
        # Save to database
        save_to_database(ticker, df)
        


def df_join_check(left_df, right_df):
    """Perform a left join on 2 dataframes with check on lengths!

    :param left_df: DataFrame - Left DataFrame to be joined
    :param right_df: DataFrame - Right DataFrame to be joined
    :return: DataFrame - DataFrame join
    """
    df = left_df.join(right_df)
    assert len(left_df) == len(df), 'Original length and new length don''t match after merging, please check!'

    return df


def get_index(index, start=None):
    """Get Index Serie from the Data Folder
    
    :param index: str - Index Name
    :param start: str - Start Data
    :return: Serie - Index Serie
    """
    log = logging.getLogger(__name__)

    df = pd.read_csv(os.path.join(oc.cfg['default']['data'], 'Index', '{}.csv'.format(index)))
    
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    df.set_index('Date', inplace=True)
    df.index.names = [None]
    if start is not None:
        df = df[df.index >= start]
    return df.resample('M').mean()


def read_csv(*args, weights=None, start_date=None, date_as_index=True, multiplier=1):
    """Read a csv file from the data repository and returns a dataframe.
    If weights is not provided, it will assume weights for spreads and butterflies.

    :param args: Customized tickers to be retrieved
    :param weights: Weights for the structure
    :param start_date: Optional parameter start date
    :param date_as_index: Date should be returned as an index
    :param multiplier: Int used to multiply the entire timeserie by (used for spreads/flies in curvature trading)
    :return:
    """
    log = logging.getLogger(__name__)

    fields = ['Open', 'High', 'Low', 'Close']
    if len(args) == 0:
        raise Exception('Need at least one argument for a ticker!')
    df = get_market_df(oci.check_ticker(args[0]), start_date)
    if df is None:
        log.error('No data found!')
        sys.exit(1)
    df *= multiplier
    if len(args) == 2:
        w = [1, -1] if weights is None else weights
        df2 = (get_market_df(oci.check_ticker(args[1]), start_date)) * multiplier
        if df2 is None:
            log.error('No data found!')
            sys.exit(1)
        df[fields] = w[0] * df[fields] + w[1] * df2[fields]
    elif len(args) == 3:
        w = [1, -2, 1] if weights is None else weights
        df2 = (get_market_df(oci.check_ticker(args[1]), start_date)) * multiplier
        df3 = (get_market_df(oci.check_ticker(args[2]), start_date)) * multiplier
        if df2 is None or df3 is None:
            log.error('No data found!')
            sys.exit(1)
        df = w[0] * df[fields] + w[1] * df2[fields] + w[2] * df3[fields]

    # High-Low adjustments
    df.loc[df.High < df.Open, 'High'] = df[df.High < df.Open]['Open']
    df.loc[df.High < df.Close, 'High'] = df[df.High < df.Close]['Close']
    df.loc[df.Low > df.Close, 'Low'] = df[df.Low > df.Close]['Close']
    df.loc[df.Low > df.Open, 'Low'] = df[df.Low > df.Open]['Open']

    # Check if date should not be index but a column
    if not date_as_index:
        df = df.reset_index()
        df.rename(columns={'index': 'Date'}, inplace=True)

    return df

