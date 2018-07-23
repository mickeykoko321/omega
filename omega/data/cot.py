import datetime as dt
import logging
import os

import pandas as pd
import quandl as qdl

import omega.configuration as c
import omega.core.instrument as oci
import omega.data.utils as odu


# What are the different COT types
cot_types = {
    'F': 'FuturesOnly',
    'FO': 'FuturesAndOptions',
    'F_L': 'FuturesOnlyLegacy',
    'FO_L': 'FuturesAndOptionsLegacy'
}

# Quandl API Key
qdl.ApiConfig.api_key = 'SkmBQRG9gxQK4HmeSoze'


def get_release_dates():
    """Get Report and Release Dates from the Release Dates file. This is to be used as the COT data is usually prepared
    on Tuesday and released on Friday. The downloaded COT data has the report date (Tuesday as a reference), where as we
    need the release date.

    :return: DataFrame - With ReportDate as index and ReleaseDate as column
    """
    path = os.path.join(c.cfg['default']['data'], 'COT', 'ReleaseDates.txt')

    # Read Data from csv file
    dates = pd.read_csv(path, index_col=0, parse_dates=True)

    
    dates.index.names = [None]
    # Format Release Dates to Timestamp (as this is the original format and will be used later)!
    dates['ReleaseDate'] = pd.to_datetime(dates['ReleaseDate'], format='%Y-%m-%d')

    return dates


def next_release_date(date):
    """Get the next release date after the specified date.

    :param date: pandas.Timestamp - Last date
    :return: pandas.Timestamp - Next release date
    """
    df = get_release_dates()
    df = df[df['ReleaseDate'] > date]
    return df['ReleaseDate'].iloc[0]


def get_cot(stem, cot_type='F'):
    """Get the cot data and cache it (Refresh it if file is older than 7 days).
    COT Types can be:
        -- F: Futures Only
        -- FO: Futures And Options
        -- F_L: Futures Only Legacy
        -- FO_L Futures And Options Only

    :param stem: str -  Market stem (customized)
    :param cot_type: String COT Type
    :return: Dataframe with COT data
    """
    log = logging.getLogger(__name__)

    # COT from CFTC Quandl or ICE
    log.debug('Get {} COT data for: {}'.format(cot_types[cot_type], stem))
    path = os.path.join(c.cfg['default']['data'], 'COT', cot_types[cot_type], '{}.csv'.format(stem))
    if oci.get(stem, 'Exchange') == 'ICE':
        if cot_type == 'F_L' or cot_type == 'FO_L':
            raise Exception('Legacy data for COT {} is not supported'.format(stem))
        else:
            if os.path.exists(path):

                # Read Data from csv file
                cot = pd.read_csv(path, index_col=0, parse_dates=True)

                
            else:
                raise Exception('File {} is not found'.format(path))
    else:
        # Check if file exists or is not too old
        if os.path.exists(path) \
               and dt.datetime.today() - dt.timedelta(days=2) < dt.datetime.fromtimestamp(os.stat(path).st_mtime):

            # Read Data from csv file
            cot = pd.read_csv(path, index_col=0, parse_dates=True)

        else:
            if cot_type in cot_types:
                try:
                    qdl_code = oci.get(stem, 'COT')
                    cot = qdl.get('CFTC/{}_{}_ALL'.format(qdl_code, cot_type))

                    cot.to_csv(path, header=True)

                except qdl.NotFoundError:
                    log.error('Incorrect code for download: {}'.format(stem))
                    return None
            else:
                raise Exception('COT Type {} not defined!'.format(cot_type))

    return cot


def cot_data(stem, cot_type='F', with_cit=False):
    """Get COT data and transform it!

    :param stem: String customized ticker
    :param cot_type: str - COT Type (see get_cot for descriptions)
    :param with_cit: Boolean Supplemental COT Data (Database not maintained)
    :return: DataFrame
    """
    log = logging.getLogger(__name__)

    # COT data
    cot = get_cot(stem, cot_type)
    if cot is not None:
        # Check if it is a commodity (commodities have only 16 columns)
        if len(cot.columns) == 16:
            # Calculations
            cot['ManagerNet'] = cot['Money Manager Longs'] - cot['Money Manager Shorts']
            comms_long = cot['Producer/Merchant/Processor/User Longs'] + cot['Swap Dealer Longs']
            comms_short = cot['Producer/Merchant/Processor/User Shorts'] + cot['Swap Dealer Shorts']
            cot['HPH'] = (comms_long - comms_short) / (comms_long + comms_short) * 100
            cot['HPS'] = cot['ManagerNet'] / (cot['Money Manager Longs'] + cot['Money Manager Shorts']) * 100
            cot['RMN'] = cot['ManagerNet'] / cot['Open Interest'] * 100
            cot['RMS'] = cot['Money Manager Spreads'] / cot['Open Interest'] * 100  # Is this useful?
            # CIT Data
            if with_cit:
                cit = get_cit_data(stem)
                cot = odu.df_join_check(cot, cit)
                # CIT Specific Calculations
                cot['NCN'] = cot['Non-Commercial Longs'] - cot['Non-Commercial Shorts']
                cot['IndexNet'] = cot['Index Trader Longs'] - cot['Index Trader Shorts']
                cot['RIN'] = cot['IndexNet'] / cot['Open Interest'] * 100
        elif len(cot.columns) == 17:
            # TODO: Quick implementation that needs to be finished
            log.warning('Implementation not finished for non-commodities futures COT! Only HPS Implemented!')
            specs_long = cot['Asset Manager Longs'] + cot['Leveraged Funds Longs']
            specs_short = cot['Asset Manager Shorts'] + cot['Leveraged Funds Shorts']
            cot['HPS'] = (specs_long - specs_short) / (specs_long + specs_short) * 100
            cot['HPH'] = 0
            cot['RMN'] = 0
            cot['RMS'] = 0
        elif '_L' in cot_type:
            # TODO: Quick implementation that needs to be finished
            log.warning('Implementation not finished for non-commodities futures COT! Only HPS Implemented!')
            cot['HPH'] = (cot['Commercial Long'] - cot['Commercial Short']) / (cot['Commercial Long'] + cot['Commercial Short']) * 100
            cot['HPS'] = (cot['Noncommercial Long'] - cot['Noncommercial Short']) / (cot['Noncommercial Long'] + cot['Noncommercial Short']) * 100
            cot['RMN'] = 0
            cot['RMS'] = 0
        # HPS Slope same for all implementations
        cot['HPSSlope'] = cot['HPS'].rolling(10).apply(lambda x: (x[-1] - x[0]) / len(x), raw=True)
        # Transform the date (from Report Date to Release Date)
        dates = get_release_dates()
        cot = odu.df_join_check(cot, dates)
        cot.set_index('ReleaseDate', inplace=True)
        cot.index.names = [None]
        # Remove possible dupes (happens in early history with duplicated release dates)
        # TODO: Shall we drop only one line instead of both duplicates?
        cot = cot.drop(cot.index[cot.index.duplicated()])
    return cot


def get_cit_data(ticker):
    """This is to get data from the Supplemental COT data
    https://www.quandl.com/data/CFTC/083731_CITS_ALL-Commitment-of-Traders-COFFEE-C-ICUS-Commodity-Index-Trader-Supplemental-083731
    :param ticker:
    :return:
    """
    log = logging.getLogger(__name__)
    # TODO: This is probably not working anymore (need to refresh files)
    file = os.path.join(c.cfg['default']['data'], 'COT', 'Supplemental', 'T{}.PRN'.format(ticker))
    columns = ['Non-Commercial Longs', 'Non-Commercial Shorts',
               'Commercial Longs', 'Commercial Shorts',
               'Non-Reportable Longs', 'Non-Reportable Shorts',
               'Index Trader Longs', 'Index Trader Shorts']

    # Read Data from csv file
    cit = pd.read_csv(file, parse_dates=True, index_col=0, header=None, names=columns)
    

    return cit