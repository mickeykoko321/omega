import datetime as dt
import enum
import json
import logging
import os
import pandas as pd
import sys

import omega.configuration as c

"""Instrument module

This module is used for anything related to customized tickers and data display.
Generic tickers have been created to simplify all usual notations. Data display can display custom spreads.

Tickers with a single-digit year and 2 digits can be used interchangeably.

Example: EDS12H7 is a spread between EDH7 and a spread 12 months apart EDH8.
"""


class InstrumentError(Exception):
    pass


class FutureType(enum.Enum):
    Outright = 1
    Spread = 2
    Butterfly = 3
    Condor = 4
    DoubleButterfly = 5
    FlyOfFly = 6

    def __str__(self):
        return self.name


type_definition = {
    FutureType.Outright: {'lambda': (lambda x: x[0]), 'weights': [1], 'contracts': 1},
    FutureType.Spread: {'lambda': (lambda x: x[0] - x[1]), 'weights': [1, -1], 'contracts': 2},
    FutureType.Butterfly: {'lambda': (lambda x: x[0] - 2 * x[1] + x[2]), 'weights': [1, -2, 1], 'contracts': 4},
    FutureType.Condor: {'lambda': (lambda x: x[0] - x[1] - x[2] + x[3]), 'weights': [1, -1, -1, 1], 'contracts': 4},
    FutureType.DoubleButterfly: {'lambda': (lambda x: x[0] - 3 * x[1] + 3 * x[2] - x[3]), 'weights': [1, -3, 3, -1], 'contracts': 8},
    FutureType.FlyOfFly: {'lambda': (lambda x: x[0] - 4 * x[1] + 6 * x[2] - 4 * x[3] + x[4]), 'weights': [1, -3, 3, -1], 'contracts': 16}
}

# Futures letter codes
letters = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']
# Months
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
# Database
json_db = json.loads(open(c.cfg['default']['database']).read())


def futures(sector=None, group=None):
    """Get all the existing futures in our universe (can also filter by sector).

    :param sector: str - Sector filtering
    :param group: str - Group filtering
    :return: list - Futures stem
    """
    if sector is not None and sector not in ['Commodity', 'Currency', 'Stock', 'Yield']:
        raise InstrumentError('Sector doesn''t exist!')
    if group is not None and group not in ['Meat', 'Other']:
        raise InstrumentError('Group doesn''t exist!')
    futs = list(json_db.keys())
    if sector is None and group is None:
        return futs
    else:
        if sector is not None:
            futs = [f for f in futs if json_db[f]['Sector'] == sector]
        if group is not None:
            futs = [f for f in futs if json_db[f]['Group'] == group]

        return futs


def create_contract(stem, ctr_mth, future_type, next_ctr_mth):
    """Create a customized ticker for a specific future

    :param stem: str - Market Stem
    :param ctr_mth: int - Maturity for the future
    :param future_type: Enum FutureType - Type of contract
    :param next_ctr_mth: int - Following maturity for the future (doesn't apply for outrights)
    :return: str - Customized ticker
    """
    if future_type == FutureType.Outright:
        contract = '{}{}'.format(stem, ym_maturity(ctr_mth))
    else:
        diff = diff_month(ctr_mth, next_ctr_mth)
        contract = '{}{}{}{}'.format(stem, str(future_type)[0], diff, ym_maturity(ctr_mth))

    return contract


def check_ticker(ticker):
    """Check that a ticker is correctly formatted.
    For now, this function only amends the ticker to long format if only one digit is sent for the year.

    :param ticker: Customized ticker
    :return: Correctly formatted ticker with 2 digits year
    """
    log = logging.getLogger(__name__)

    new_ticker = ticker
    # Check if last 2 characters are digits
    if not ticker[-2:].isdigit():
        year = 10 + int(ticker[-1])
        # TODO: Will be wrong for really far out contracts, needs to be amended eventually!
        n_y = int(dt.datetime.now().strftime('%y'))
        year = year + 10 if year < n_y else year
        new_ticker = '{}{}'.format(ticker[0:-1], year)
    return new_ticker


def int_maturity(maturity, zeros=False):
    """Convert a maturity into a year/month int.

    Example: H17 returns 201703 (or with the zeros option: 20170300
    :param maturity: Maturity with format letter code - 2 digits year
    :param zeros: bool - Set this to true if we want to get yyyymm00
    :return: Year/Month int
    """
    log = logging.getLogger(__name__)

    month = maturity[0:1]
    year = int(maturity[1:])
    # Conversion
    im = ((2000 if year < 50 else 1900) + year) * 100 + letters.index(month) + 1
    im = im * 100 if zeros else im  # Adding extra zeros

    return im


def cmed_maturity(maturity):
    """Convert a maturity into a maturity for CME Direct.

    Example: H17 returns Mar17
    :param maturity: Maturity with format letter code - 2 digits year
    :return: First 3 letters of the month with the year attached
    """
    log = logging.getLogger(__name__)

    month = maturity[0:1]
    year = int(maturity[1:])
    return '{}{}'.format(months[int(letters.index(month))][0:3], year)


def ym_maturity(maturity):
    """Convert an int maturity into a year/month format.

    Example: 20170300 returns H17
    :param maturity: Maturity with int format (CtrMth)
    :return: mY contract code format
    """
    log = logging.getLogger(__name__)

    lm = len(str(maturity))
    if lm == 8 or lm == 6:
        maturity = str(maturity)[0:6]
    else:
        raise InstrumentError('Maturity not correctly defined (expecting: yyyymm00)!')
    year = maturity[2:4]
    month = letters[int(maturity[4:6]) - 1]
    return '{}{}'.format(month, year)


def next_maturity(maturity, length, short_maturity=False):
    """Return the next maturity given a maturity and a number of months

    :param maturity: Current maturity
    :param length: Number of months
    :param short_maturity: Indicates whether or not we use the short maturity type (M7 or M17)
    :return: Next maturity
    """
    log = logging.getLogger(__name__)

    month = maturity[0:1]
    year = int(maturity[1:])

    imonth = int(letters.index(month) + length)
    iyear = year

    if imonth > 11:
        iyear += int(imonth / 12)
        imonth = imonth % 12  # This is the remainder of the division

    if short_maturity:
        iyear %= 10
        year = iyear
    else:
        year = iyear if iyear >= 10 else '0{}'.format(iyear)

    return '{}{}'.format(letters[imonth], year)


def diff_month(d1, d2):
    """Number of months between 2 maturities

    :param d1: First maturity (format is yyyymm00)
    :param d2: Second maturity (format is yyyymm00)
    :return: Integer
    """
    d1 = dt.datetime.strptime('{}01'.format(str(d1)[0:6]), '%Y%m%d')
    d2 = dt.datetime.strptime('{}01'.format(str(d2)[0:6]), '%Y%m%d')
    return (d2.year - d1.year) * 12 + d2.month - d1.month


def previous_month(maturity):
    """From an int maturity, get the month just before the maturity (mainly used for
    Goldman's roll).

    :param maturity: str - MYY Maturity style
    :return: int - yyyymm Maturity style
    """
    month = maturity[0:1]
    year = int(maturity[1:])

    imonth = int(letters.index(month))  # No need to remove -1 as index starts at 0
    iyear = year

    if imonth <= 0:
        iyear -= 1
        imonth += 12  # This is the remainder of the division

    return (2000 + iyear) * 100 + imonth


def to_short_mat(mat):
    """Convert a long maturity (example M24) into a short maturity (M4).

    :param mat: Maturity to be converted
    :return: Returns a short maturity
    """
    return '{}{}'.format(mat[0], mat[2])


def get_maturities(ticker, short_maturity=False):
    """Get all the maturities for a ticker

    :param ticker: Customized ticker
    :param short_maturity: Whether or not we should use short maturities (example: U7)
    :return: List of all the maturities for the ticker
    """
    log = logging.getLogger(__name__)

    ticker = check_ticker(ticker)
    if short_maturity:
        maturity = '{}{}'.format(ticker[-3], ticker[-1])
    else:
        maturity = ticker[-3:]
    if len(ticker) == 5:
        return [maturity]
    else:
        length = int(ticker[3:(len(ticker) - 3)])
        if 'S' in ticker:
            return [maturity, next_maturity(maturity, length, short_maturity)]
        elif 'B' in ticker:
            nm1 = next_maturity(maturity, length, short_maturity)
            return [maturity, nm1, next_maturity(nm1, length, short_maturity)]
        elif 'D' in ticker:
            nm1 = next_maturity(maturity, length, short_maturity)
            nm2 = next_maturity(nm1, length, short_maturity)
            return [maturity, nm1, nm2, next_maturity(nm2, length, short_maturity)]
        elif 'F' in ticker:
            log.error('F type is not implemented, exiting!')
            sys.exit(1)


def get_type(ticker):
    """From a ticker returns the letter associated with the type (O, S, B, D, F)

    :param ticker: Customized ticker
    :return: One letter code
    """
    log = logging.getLogger(__name__)

    ticker = check_ticker(ticker)
    if len(ticker) == 5:
        return 'O'
    else:
        return ticker[2]


def get_future_type(ticker):
    """From a ticker return the correct FutureType

    :param ticker: Customized ticker
    :return: FutureType
    """
    log = logging.getLogger(__name__)

    ticker = check_ticker(ticker)
    if len(ticker) == 5:
        return FutureType.Outright
    else:
        letter = ticker[2]
        for t in FutureType:
            if letter == str(t)[0]:
                return t

    raise InstrumentError('Ticker {} doesn''t have a type defined!'.format(ticker))


def get_length(ticker):
    """ Get length between 2 contracts for any structure (spread, flies, etc...)

    :param ticker: Customized ticker
    :return: Int number of months
    """
    log = logging.getLogger(__name__)

    return int(ticker[3:(len(ticker) - 3)])


def get_stem(stem, provider):
    """Get the stem root of the ticker

    :param stem:
    :param provider:
    :return:
    """
    s_stems = get(stem, 'Stem')
    return s_stems[provider]


def to_outright(stem, m1, provider):
    """

    For Reuters, see notice: https://customers.thomsonreuters.com/a/support/NotificationService/ViewData.aspx?id=DN070587
    Which is renaming convention (hence why the hack).
    :param stem: 
    :param m1: 
    :param provider: 
    :return: 
    """
    log = logging.getLogger(__name__)

    if 'Bloomberg' in provider:
        return '{}{}{} Comdty'.format(stem, m1[0], m1[2])
    elif 'Reuters' in provider:
        am1 = m1 if int(m1[1:]) >= 24 or (stem == 'NG' and int(m1[1:]) >= 18) else to_short_mat(m1)
        ric = '{}{}'.format(get_stem(stem, provider), am1)
        if not is_active(stem, int_maturity(m1)):
            ric = '{}^{}'.format(ric, m1[1])
        return ric
    elif 'T4' in provider:
        return '{} ({})'.format(get_stem(stem, provider), m1)
    elif 'CMED' in provider:
        return '=CMED.C("{} {}")'.format(get_stem(stem, provider), cmed_maturity(m1))
    elif 'IQFeed' in provider:
        return '{}{}'.format(get_stem(stem, provider), m1)


def to_spread(stem, m1, m2, provider):
    """
    
    :param stem: 
    :param m1: 
    :param m2: 
    :param provider: 
    :return: 
    """
    log = logging.getLogger(__name__)

    if 'Bloomberg' in provider:
        return '{0}{1}{0}{2} Comdty'.format(stem, '{}{}'.format(m1[0], m1[2]), '{}{}'.format(m2[0], m2[2]))
    elif 'Reuters' in provider:
        one = ''
        if stem in ['BO', 'C_', 'DC', 'ED', 'FC', 'FF', 'GC', 'HG', 'KW', 'LB', 'LC', 'LH', 'O_', 'RR', 'S_', 'SI', 'SM', 'W_']:
            one = '1'
        rt = 'RT' if stem in ['SI'] else ''
        am1 = m1 if int(m1[1:]) >= 24 or (stem == 'NG' and int(m1[1:]) >= 18) else to_short_mat(m1)
        am2 = m2 if int(m2[1:]) >= 24 or (stem == 'NG' and int(m2[1:]) >= 18) else to_short_mat(m2)
        ric = '{}{}{}{}-{}'.format(one, get_stem(stem, provider), rt, am1, am2)
        if not is_active(stem, int_maturity(m1)):
            ric = '{}^{}'.format(ric, m1[1])
        return ric
    elif 'T4' in provider:
        return '{} ({})-({})'.format(get_stem(stem, provider), m1, m2)
    elif 'CMED' in provider:
        return '=CMED.C("{} {}/{}")'.format(get_stem(stem, provider), cmed_maturity(m1), cmed_maturity(m2))
    elif 'IQFeed' in provider:
        return '{0}{1}-{0}{2}'.format(get_stem(stem, provider), m1, m2)


def to_butterfly(stem, m1, m2, m3, provider):
    """
    
    :param stem: 
    :param m1: 
    :param m2: 
    :param m3: 
    :param provider: 
    :return: 
    """
    log = logging.getLogger(__name__)

    if 'Bloomberg' in provider:
        return 'B{}{}{} Comdty'.format(stem, '{}{}'.format(m1[0], m1[2]), '{}{}'.format(m3[0], m3[2]))
    elif 'Reuters' in provider:
        # TODO: FIX this (use helper function)
        log.warning('This needs to be amended for Reuters! Copy implementation from to_spread!')
        return '1{}BF{}{}-{}{}-{}{}'.format(get_stem(stem, provider), m1[0], m1[2], m2[0], m2[2], m3[0], m3[2])
    elif 'T4' in provider:
        return '{} ({})-2({})({})'.format(get_stem(stem, provider), m1, m2, m3)
    elif 'CMED' in provider:
        return '=CMED.C("{} {}/{}/{}")'.format(get_stem(stem, provider), cmed_maturity(m1), cmed_maturity(m2),
                                               cmed_maturity(m3))
    elif 'IQFeed' in provider:
        log.error('IQFeed Provider Not Implemented for to_butterfly!')
        sys.exit(1)


def to_double_fly(stem, m1, m2, m3, m4, provider):
    """
    
    :param stem: 
    :param m1: 
    :param m2: 
    :param m3: 
    :param m4: 
    :param provider: 
    :return: 
    """
    log = logging.getLogger(__name__)

    if 'Bloomberg' in provider:
        return 'D{}{}{} Comdty'.format(stem, '{}{}'.format(m1[0], m1[2]), '{}{}'.format(m4[0], m4[2]))
    elif 'T4' in provider:
        return '{} ({})-3({})3({})-({})'.format(get_stem(stem, provider), m1, m2, m3, m4)
    elif 'CMED' in provider:
        return '=CMED.C("{} {}/{}/{}/{}")'.format(get_stem(stem, provider), cmed_maturity(m1), cmed_maturity(m2),
                                                  cmed_maturity(m3), cmed_maturity(m4))
    elif 'IQFeed' in provider:
        log.error('IQFeed Provider Not Implemented for to_double_fly!')
        sys.exit(1)


def convert_ticker(ticker, provider):
    """Convert customized ticker to a provider format for Data Download.

    :param ticker: Customized ticker
    :param provider: For which provider do we need the ticker
    :return: Bloomberg Ticker
    """
    log = logging.getLogger(__name__)

    ticker = check_ticker(ticker)
    if len(ticker) == 5:
        # Outright
        return to_outright(ticker[0:2], ticker[-3:], provider)
    else:
        stem = ticker[0:2]
        i_type = ticker[2]
        length = int(ticker[3:(len(ticker) - 3)])
        maturity = ticker[-3:]
        if 'S' in i_type:
            # Spread
            nm = next_maturity(maturity, length)
            return to_spread(stem, maturity, nm, provider)
        elif 'B' in i_type:
            # Butterfly
            nm1 = next_maturity(maturity, length)
            nm2 = next_maturity(nm1, length)
            # Hack for problematic tickers with T4
            if 'T4' in provider and \
                    ('EDB3M20' in ticker or 'EDB3U20' in ticker or 'EDB6Z19' in ticker or 'EDB12Z18' in ticker):
                s = 'MKT_CME_{}00_GE:BF {}-{}-{}'
                return s.format(int_maturity(maturity), '{}{}'.format(maturity[0], maturity[2]),
                                '{}{}'.format(nm1[0], nm1[2]), '{}{}'.format(nm2[0], nm2[2]))
            else:
                return to_butterfly(stem, maturity, nm1, nm2, provider)
        elif 'D' in i_type:
            # Double Butterfly
            nm1 = next_maturity(maturity, length)
            nm2 = next_maturity(nm1, length)
            nm3 = next_maturity(nm2, length)
            return to_double_fly(stem, maturity, nm1, nm2, nm3, provider)


def ctrmth(stem, we_trade=True):
    """ Get the contract month table (direct export from the database)

    :param stem: str - Market Stem
    :param we_trade: Boolean to indicate if we should get all the maturities or all the one we trade
    :return: DataFrame
    """
    log = logging.getLogger(__name__)

    # Get Future's letters (if empty list in database then use all the letters)
    i_letters = get(stem, 'Letters')
    i_letters = i_letters if i_letters else letters
    # Read Data
    ric = get_stem(stem, 'Reuters')
    file = os.path.join(c.cfg['default']['data'], 'CtrMth', '{}.csv'.format(ric))

    # Read Data from csv file
    df = pd.read_csv(file)

    # Filter out contracts that we don't trade
    if we_trade:
        df = df[df['WeTrd'] == -1]
        df.index = range(0, len(df))
    else:
        # Add Contract Letters
        df['Letter'] = df.apply(lambda x: ym_maturity(x['CtrMth'])[0], axis=1)
        if set(i_letters) != set(df['Letter'].unique()):
            log.warning('Letters in database are different than in CtrMth for: {}!'.format(stem))
            df = df[df['Letter'].isin(i_letters)]
            df.reset_index(drop=True, inplace=True)
    # Check if dataframe is not empty
    if df.empty:
        raise InstrumentError('CtrMth file for {} is empty!'.format(stem))

    return df


def is_active(stem, maturity):
    """Returns whether or not a contract is active (or expired).
    This version is based on the CtrMth tables.

    :param stem: Stem for the symbol
    :param maturity: Int representing contract month (example: 201710)
    :return:
    """
    log = logging.getLogger(__name__)

    # Get the contract table
    df = ctrmth(stem, False)
    idx = df[maturity * 100 == df['CtrMth']].index.values[0]
    # Check if Last Day Rule is valid!
    if pd.isnull(df.iloc[idx]['LTD']):
        log.error('Last Day rule returned an empty value, please check!')
        sys.exit(1)
    return df.iloc[idx]['LTD'] >= dt.datetime.today().strftime('%Y-%m-%d')


def maturity_generator(maturity, months_to_next_mat, short_maturity=False):
    """Generator of maturities

    :param maturity: Maturity where to start generating
    :param months_to_next_mat: Number of months between maturities
    :param short_maturity: Whether or not we should use short maturities (example: U7)
    :return: Next maturity
    """
    log = logging.getLogger(__name__)

    while True:
        yield maturity
        maturity = next_maturity(maturity, months_to_next_mat, short_maturity)


def to_constant_contract(ticker, maturities_list):
    """
    
    :param ticker: 
    :param maturities_list: 
    :return: 
    """
    log = logging.getLogger(__name__)

    log.debug('We assume that we use short maturities: {}, is the ticker correct?'.format(ticker))
    stem = ticker[0:2]
    maturity = ticker[-2:]
    ticker = check_ticker(ticker)
    i_type = get_type(ticker)
    length = get_length(ticker)
    number = maturities_list.index(maturity) + 1

    return '{}{}{}{}'.format(stem, number, i_type, length)


def lots(ticker):
    """
    
    :param ticker: 
    :return: 
    """
    log = logging.getLogger(__name__)

    ft = get_future_type(ticker)
    return type_definition[ft]['contracts']


def comms(account, ticker, quantity, date):
    """Calculate commissions for a trade based on the database json file.

    :param account: String account - Account
    :param ticker: String symbol - Customized ticker
    :param quantity: Int Quantity traded
    :param date: Datetime date - Date of the transaction
    :return: Float value of the corresponding commission for the trade
    """
    log = logging.getLogger(__name__)

    stem = ticker[0:2]
    s_lots = lots(ticker)
    # Get commissions data
    s_comms = get(stem, 'Comms')
    try:
        s_comms = s_comms[account]
        s_c = 0
        for k, v in s_comms.items():
            if date >= dt.datetime.strptime(k, '%Y-%m-%d'):
                s_c = (v['Lot'] * s_lots + v['Fill']) * quantity
        return s_c
    except KeyError:
        log.error('Commissions for account not defined! Please check: {}!'.format(stem))
        return 0


def raw_comms(stem, date, account='7GE1478'):
    """

    :param stem:
    :param date:
    :param account: str - Account for which we need to get the commissions
    :return:
    """
    log = logging.getLogger(__name__)

    # Get commissions data
    s_comms = get(stem, 'Comms')
    try:
        s_comms = s_comms[account]
        s_c = 0
        for k, v in s_comms.items():
            if date >= dt.datetime.strptime(k, '%Y-%m-%d'):
                s_c = (v['Lot'] + v['Fill'])
        return s_c
    except KeyError:
        log.error('Commissions for account not defined! Please check: {}!'.format(stem))
        return 0


def get(stem, name):
    """Given a symbol stem, get the specified attribute from the database

    :param stem: Symbol stem (from the RIC)
    :param name: Name of the attribute to retrieve from the db
    :return: Value from the database
    """
    log = logging.getLogger(__name__)

    try:
        return json_db[stem][name]
    except KeyError:
        raise InstrumentError('{} - Field "{}" not found!'.format(stem, name))
