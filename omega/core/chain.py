import collections as co
import datetime as dt
import enum
import logging
import pandas as pd
import pandas.tseries.offsets as o

import omega.data.utils as odu
import omega.core.instrument as oci

"""Module Chain
Contains class definition for Future/Option chains (Future will be implemented first)
"""


class ChainError(Exception):
    pass


class Status(enum.Enum):
    Active = 1
    ActiveLive = 2
    ActivePlus = 3
    All = 4
    Expired = 5


def find(f, seq):
    """Return first item in sequence where f(item) == True.

    :param f: lambda - Lambda function
    :param seq: list - Sequence in which to look for
    :return: object - Item which has been found
    """
    for item in seq:
        if f(item):
            return item
    raise ChainError('Item has not been found in the sequence!')


def generate_contracts(stem, ctr_mth, future_type, df, ncb):
    """For a specific contract, generate a list of contracts tickers

    :param stem: str - Market Stem
    :param ctr_mth: int - Maturity for the future
    :param future_type: Enum FutureType - Type of contract
    :param df: DataFrame - Contains the contract table
    :param ncb: int - Number of contracts in between (not for outrights)
    :return: list - List of customized tickers
    """
    idx = df[df['CtrMth'] == ctr_mth].index[0]
    t_def = oci.type_definition[future_type]
    contracts = []
    if future_type == oci.FutureType.Outright:
        contracts.append(oci.create_contract(stem, ctr_mth, future_type, None))
    else:
        for jdx in range(ncb):
            if idx + jdx + t_def['contracts'] - 1 < len(df):
                next_ctr_mth = df.iloc[idx + jdx + 1]['CtrMth']
                contracts.append(oci.create_contract(stem, ctr_mth, future_type, next_ctr_mth))

    return contracts


def get_table(date, stem, future_type, status, we_trade=True, nac=4, ncb=1, data_download=False):
    """Generate a table of all the contracts available for a market and the associated last date.

    :param date: str - Date reference for the active or expired contracts
    :param stem: str - Market Stem
    :param future_type: Enum FutureType - Type of contract
    :param status: Enum Status - Status needed for the chain
    :param we_trade: bool - Whether or not the contract is considered as traded
    :param nac: int - Number of active contracts to get (depending on the markets)
    :param ncb: int - Number of contracts in between (not for outrights)
    :param data_download: bool - Option for data download (as we need to use LTD for completeness)
    :return: A dataframe of all the available tickers with the last date
    """
    ld_rule = 'LTD' if data_download else oci.get(stem, 'Reference')
    # Get the contract table
    ct_df = oci.ctrmth(stem, we_trade)
    # Generate the contracts
    contracts = []
    active = 0
    min_ctrmth = 20000000 if future_type == oci.FutureType.Outright else 20070000
    for index, row in ct_df[ct_df['CtrMth'] > min_ctrmth].iterrows():
        cts = generate_contracts(stem, row['CtrMth'], future_type, ct_df, ncb)
        for c in cts:
            if not isinstance(row[ld_rule], str):
                raise ChainError('Problem in CtrMth table for: {}!'.format(c))
            # Add 5 days to the end if ActivePlus Status (to continue downloading data for expired contracts)
            end = (dt.datetime.strptime(row[ld_rule], '%Y-%m-%d') + o.BDay(5)).strftime('%Y-%m-%d') if status == Status.ActivePlus else row[ld_rule]
            # Add the contract depending on the status
            if status == Status.Active or status == Status.ActiveLive or status == Status.ActivePlus:
                if date > end or active >= nac * ncb:
                    continue
                if date < row[ld_rule]:  # Not counting expired contracts for data download in ActivePlus mode
                    active += 1
            elif status == Status.Expired and date < row[ld_rule]:
                break
            # Add the contract to the list of contracts
            contracts.append(co.OrderedDict({'Ticker': c, 'LastDate': row[ld_rule]}))

    return pd.DataFrame(contracts)


def aggregate(future_chain, ticker, field_name, length=5):
    """Aggregate data for a future chain. For now, it is taking the average of the last contracts (specified by length).
    TODO: Consider other types of aggregation.

    :param future_chain: Object FutureChain - FutureChain object initialized with data
    :param ticker: str - Customized ticker (calculate aggregation based on this ticker)
    :param field_name: str - Field name for the aggregation
    :param length: int - Length for the aggregation
    :return: list - Aggregated vector
    """
    log = logging.getLogger(__name__)

    # Get the days back from the first element in the data dictionary
    days_back = future_chain.days_back
    log.debug('Days back: {}'.format(days_back))
    pos = future_chain.contracts.index(ticker)
    agg = [0 for _ in range(days_back)]
    div = 0
    for i in range(0, length, 1):
        idx = pos - i
        ct = future_chain.contracts[idx]
        try:
            agg += future_chain.data[ct][field_name].values
            div += 1
        except Exception as e:
            log.error('Problem for ticker: {}! Error: {}'.format(ct, e))
    agg = [x // div for x in agg]
    return agg


class FutureChain(object):
    """FutureChain Object"""
    def __init__(self, stem, future_type):
        """Future Chain Constructor

        :param stem:  str - Market Stem
        :param future_type:  Enum FutureType - Type of contract
        """
        self.log = logging.getLogger(__name__)

        self.stem = stem
        self.future_type = future_type
        self.status = None
        self.days_back = None
        self.chain = None
        self.contracts = None
        self.data = None
        self.margin = oci.get(stem, 'Margin')
        self.commission = oci.raw_comms(stem, dt.datetime.today())
        self.point = oci.get(stem, 'Point')

    def initialize_contracts(
            self, status=Status.Active, date=None, filter=None, nac=4, ncb=1, we_trade=True, initialize_data=False,
            as_dataframe=False, days_back=90, extra_days=True, data_download=False
    ):
        """Get a DataFrame of all the contracts in the chain with the possibility to select the status or a date
        (If none of the parameters are provided, returns current active contracts).

        :param status: Enum Status - Status needed for the chain (default: Active)
        :param date: str - Specify a date for a dataframe of contracts in the chain (default: today)
        :param filter: str - Filter the list of contracts to get specific letters or a number of previous contracts
        :param nac: int - Number of active contracts to get (depending on the markets)
        :param ncb:  int - Number of contracts in between (not for outrights)
        :param we_trade: bool - Whether or not the contract is considered as traded
        :param initialize_data: bool: Set to True if we need to initialize data
        :param as_dataframe: bool - Set to True if we want to return a DataFrame
        :param days_back: int - Number of days back for the data (default: 90)
        :param extra_days: bool - Option to add a day before and the last day (LTD or FND) - Used to load data
        :param data_download: bool - Option for data download (as we need to use LTD for completeness)
        :return: DataFrame or list of contracts
        """
        if date is None:
            date = dt.datetime.today().strftime('%Y-%m-%d')
        df = get_table(date, self.stem, self.future_type, status, we_trade=we_trade, nac=nac, ncb=ncb, data_download=data_download)
        # Set Class Variables
        assert not df.empty, 'Chain DataFrame is None for {} - {}, something went wrong!'.format(self.stem, self.future_type)
        self.status = status
        self.chain = df
        self.contracts = list(df['Ticker'])
        # Initialize Data
        if initialize_data:
            self.initialize_data(days_back=days_back, extra_days=extra_days)
        # Filtering
        if filter is not None:
            if isinstance(filter, int):
                if filter > len(df):
                    self.log.error('Number of contracts: {} too high: {} - filter ignored!'.format(filter, len(df)))
                if filter > 0:
                    df = df.head(filter)
                elif filter < 0:
                    df = df.tail(abs(filter))
            elif len(filter) == 1 and filter.isalpha():
                # Filter based on month letter
                filter_df = df['Ticker'].str.contains(filter)
                if not filter_df.any():
                    self.log.error('Filter ignored - check that the letter {} is valid!'.format(filter))
                else:
                    df = df[filter_df]
            else:
                self.log.error('Filter {} not defined and ignored!')
            # This needs to be repeated... TODO: Find a better way to do this
            self.chain = df
            self.contracts = list(df['Ticker'])

        return self.chain if as_dataframe else self.contracts

    def initialize_data(self, days_back=90, extra_days=True, partial=False):
        """Get an ordered dictionary of DataFrames with the corresponding data.

        :param days_back: int - Number of days back for the data (default: 90)
        :param extra_days: bool - Option to add a day before and the last day (LTD or FND) - Used to load data
        :param partial: bool - Option to load data even if length is smaller than days_back
        :return: DataFrame
        """
        self.days_back = days_back
        if self.chain is None:
            self.initialize_contracts(Status.Expired)
        # Get all the dataframes
        dfs = co.OrderedDict()
        for index, row in self.chain.iterrows():
            sdf = odu.get_market_df(row['Ticker'])
            if sdf is not None and (len(sdf) >= self.days_back or partial):
                # Roll Yield for Spreads
                if self.future_type == oci.FutureType.Spread:
                    sdf['RollYield'] = odu.roll_yield(row['Ticker'], sdf)
                if extra_days:
                    sdf = sdf[sdf.index <= pd.to_datetime(row['LastDate'])]
                    dfs[row['Ticker']] = sdf.iloc[-(days_back+1):]
                else:
                    # LTD or FND should be excluded as they can be volatile (and can't trade FND)
                    sdf = sdf[sdf.index < pd.to_datetime(row['LastDate'])]
                    dfs[row['Ticker']] = sdf.iloc[-days_back:]
                # Find start date
                if self.status == Status.ActiveLive:
                    start = odu.get_start_date(row['LastDate'], days_back=days_back)
                    sdf = sdf[sdf.index >= start]
                    if len(sdf) > 0:
                        dfs[row['Ticker']] = sdf
                    else:
                        # Remove from the contracts and the chain DataFrame
                        self.chain.drop(index, inplace=True)
                        self.contracts.remove(row['Ticker'])
                        self.log.warning('Removing {} as too early!'.format(row['Ticker']))
            else:
                # Remove from the contracts and the chain DataFrame
                self.chain.drop(index, inplace=True)
                self.contracts.remove(row['Ticker'])
                self.log.warning('File not found or not enough data for: {}!'.format(row['Ticker']))

        self.chain.reset_index(inplace=True, drop=True)
        self.data = dfs
        return self.data

    def get_continuous(self):
        """This is to get the continuous time-serie for the chain. No adjustment made so it will show jumps.

        :return: DataFrame - Continuous DataFrame (not adjusted)
        """
        dfs = []
        previous = '1900-01-01'
        for idx, row in self.chain.iterrows():
            ct, last = row.values
            # Get current dataframe
            cdf = self.data[ct]
            cdf = cdf[-91:-1] if idx == 0 else cdf[(cdf.index >= previous) & (cdf.index < last)]
            # Update previous
            previous = row['LastDate']
            dfs.append(cdf)
        dff = pd.concat(dfs)

        return dff

    def get_start_end(self, extra_days=False):
        """Get Start and End dates for the chain

        :param extra_days: bool - Add some extra days on either side (used for Reference Creation)
        :return: str - Start and End
        """
        try:
            keys = list(self.data.keys())
            start = self.data[keys[0]].index[0].to_pydatetime()
            end = dt.datetime.strptime(self.chain.iloc[-1]['LastDate'], '%Y-%m-%d')
            if extra_days:
                start -= o.BDay(10)
                end += o.BDay(1)
            self.log.info('First Contract: {} - Last Contract: {}'.format(keys[0], keys[-1]))
            return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
        except Exception:
            raise ChainError('Problem while accessing start/end!')

    def filter_chain(self, contracts):
        """Filter the chain DataFrame with a subset of contracts to allow backtests with less contracts than the full
        chain. Filters only the DataFrame for now. This will synchronise the position with the names in the backtest.
        This is to avoid having to index the dataframe with the name (which is time-consuming).

        :param contracts: list - List of contracts to backtest
        :return: object - Returns itself
        """
        self.chain = self.chain[self.chain['Ticker'].isin(contracts)]
        self.contracts = contracts
        return self

    def last_date(self, position):
        """Method to get the last date for a specific contract in the DataFrame chain

        :param position: int - Row position
        :return: datetime date - Last Date for the Contract
        """
        return dt.datetime.strptime(self.chain.iloc[position]['LastDate'], '%Y-%m-%d')

    def ticker(self, position):
        """Method to get the ticker for a specific contract in the chain

        :param position: int - Row position
        :return: str - Ticker for the contract
        """
        return self.contracts[position]
