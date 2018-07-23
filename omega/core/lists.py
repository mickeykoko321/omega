import datetime as dt
import logging
import pandas as pd

import omega.core.chain as occ
import omega.core.instrument as oci

import omega.configuration as oc
import omega.data.utils as odu


"""Lists module

This module is used to create lists for data download or lists of active tickers for trading.

Type of lists:
-- Provider File: This is creating a file of tickers with their respective provider specific ticker. There's also the 
option to return the dataframe (used mainly for testing). The file is used by external 3rd party applications for 
data retrieval (example: IQFeed, eSignal, etc...).
-- Tickers DF: Generate a dataframe of tickers with a specific status (see core.chain). This is to be used by the
internal download functionality (using Reuters Eikon). Option to download data for expired contracts (historical data)
or data for active contracts (to be ran on a daily basis).
-- Curvature List: This creates a list of active tickers for the curvature strategy. The list is only used in Excel, to
get live quotes (and is used in the Monitor's tab).
-- Tickers for Curvature: Internal helper function for the Curvature List.
"""


def create_provider_file(status, provider, symbols=None, path=None):
    """"Create a list for all download types to be used by an external provider.

    :param status: Enum Status - Active/All/Expired Status
    :param provider: str - Provider name
    :param symbols: list - Symbols to download (Stem should be provided) - If not provided, will go through the universe
    :param path: str - If path is provided, it saves the output to a file with the specified path
    :return: None/DataFrame - Depending if path is provided
    """
    log = logging.getLogger(__name__)

    # Get all the tickers
    symbols = oci.json_db if symbols is None else symbols
    dfs = []
    for m in symbols:
        # Get tickers for this market
        dfs.append(generate_tickers_df(m, status))
    # Create the provider dataframe
    tickers = pd.concat(dfs)
    tickers['Provider'] = tickers.apply(lambda x: oci.convert_ticker(x['Ticker'], provider), axis=1)
    # Return the list or export it
    if path is None:
        return tickers[['Ticker', 'Provider']]
    else:
        log.debug('Save file to: {}'.format(path))

        tickers[['Ticker', 'Provider']].to_csv(path, sep=';', index=False, header=False)
        


def generate_tickers_df(stem, status=occ.Status.Active):
    """Generate a DataFrame of symbols for a given stem for data download

    :param stem: str - Customized Stem
    :param status: Enum Status - Status needed for download
    :return: DataFrame with Ticker Column
    """
    log = logging.getLogger(__name__)

    dfs = []
    # Get number of active contracts and number of contracts in between
    # TODO: Populate database.json with values for all contracts!
    try:
        dl = oci.get(stem, 'Download')
        nac, ncb = dl['nac'], dl['ncb']
    except oci.InstrumentError:
        log.warning('{} - Set Download Parameters!'.format(stem))
        nac, ncb = 4, 1  # Default behaviour when no parameters
    params = {'as_dataframe': True, 'data_download': True}
    ot = occ.FutureChain(stem, oci.FutureType.Outright).initialize_contracts(status, we_trade=False, nac=nac, **params)
    st = occ.FutureChain(stem, oci.FutureType.Spread).initialize_contracts(status, we_trade=(False if stem != 'ED' else True), nac=nac - 1, ncb=ncb, **params)
    bt = occ.FutureChain(stem, oci.FutureType.Butterfly).initialize_contracts(status, we_trade=True, nac=nac - 2, ncb=ncb, **params) if stem == 'ED' else None
    dfs.append(ot)
    dfs.append(st)
    if bt is not None:
        dfs.append(bt)
    sdf = pd.concat(dfs)

    return sdf.reset_index(drop=True)


def generate_curvature_list():
    """Generate a list of symbols for data download for the curvature strategy. This is to be used only to generate
    the symbols for the Excel Quotes sheet.

    :return: list - Active Tickers for ED and FF
    """
    log = logging.getLogger(__name__)

    log.debug('Generate list of tickers for Curvature')
    date = dt.datetime.today().strftime('%Y-%m-%d')
    tickers = []
    for m in ['ED', 'FF']:
        mcm = oci.ctrmth(m)
        fm = mcm[mcm['LTD'] >= date].iloc[0]['CtrMth']
        tickers.extend(generate_tickers_for_curvature(oci.ym_maturity(fm), m, 1 if m == 'FF' else 3))
    # Transform to short maturities (specific to Curvature)
    tickers = ['{}{}'.format(t[0:-2], t[-1]) for t in tickers]
    return tickers


def generate_tickers_for_curvature(first_maturity, symbol='ED', months_to_next_mat=3):
    """Generate a list of all the active tickers that we might need to trade

    :param first_maturity: Maturity where to start generating tickers
    :param symbol: Symbol to generate ticker for
    :param months_to_next_mat: Number of months between maturities
    :return: List of active tickers
    """
    log = logging.getLogger(__name__)

    short_maturity = False
    if len(first_maturity) == 2:
        short_maturity = True
    if 'ED' in symbol:
        d_sym = {
            1: ['ED', 29], 2: ['EDS3', 28], 3: ['EDS6', 27], 4: ['EDS9', 26],
            5: ['EDS12', 25], 6: ['EDB3', 27], 7: ['EDB6', 25], 8: ['EDB12', 21]
        }
    elif 'FF' in symbol:
        d_sym = {
            1: ['FF', 18], 2: ['FFS1', 17], 3: ['FFS2', 16],
            4: ['FFS3', 15], 5: ['FFS4', 14], 6: ['FFS5', 13], 7: ['FFS6', 12]
        }
    else:
        raise Exception('Symbol not defined: {}'.format(symbol))
    tickers = []
    for k, v in d_sym.items():
        gen_mat = oci.maturity_generator(first_maturity, months_to_next_mat, short_maturity)
        tickers += ['{}{}'.format(v[0], next(gen_mat)) for _ in range(v[1])]

    return tickers
