import datetime as dt
import logging
import pandas as pd
import os

import omega.configuration as oc
import omega.core.instrument as oci

from arctic import Arctic
import urllib.parse
import omega.data.utils as odu


"""Module ICE COT
This is a module to retrieve COT data from the ICE exchange - data needs to be retrieved on a weekly basis.
"""


def list_stem_by_cot():
    """Function to get all the ICE markets for which to get the COT data and returns an inverted dictionary.

    :return: dict - Inverted COT dictionary (ICE COT -> Stem)
    """
    result = dict()
    for stem in oci.json_db:
        params = oci.json_db[stem]
        if params['Exchange'] == 'ICE':
            result.update({params['COT']: stem})
    return result


def process_date(date):
    """Transform a date to a different format.

    :param date: str - Date to be transformed (old format: mm/dd/yyyy)
    :return: str - Date transformed (new format: yyyy-mm-dd)
    """
    m, d, y = date.split('/')
    return '{}-{}-{}'.format(y, m.zfill(2), d.zfill(2))


def process_stem(df_in, cot_type, stem):
    """Process a raw DataFrame from the ICE, extract relevant data and save it

    :param df_in: DataFrame - DataFrame with COT data
    :param cot_type: str - COT Type
    :param stem: str -  Market stem (customized)
    """
    log = logging.getLogger(__name__)

    log.info('Process stem for {} - Type: {}'.format(stem, cot_type))
    # Create DataFrame
    df = pd.DataFrame()
    df['Date'] = df_in['As_of_Date_Form_MM/DD/YYYY'].map(lambda x: process_date(x))
    df['Open Interest'] = df_in['Open_Interest_All']
    df['Producer/Merchant/Processor/User Longs'] = df_in['Prod_Merc_Positions_Long_All']
    df['Producer/Merchant/Processor/User Shorts'] = df_in['Prod_Merc_Positions_Short_All']
    df['Swap Dealer Longs'] = df_in['Swap_Positions_Long_All']
    df['Swap Dealer Shorts'] = df_in['Swap__Positions_Short_All']
    df['Swap Dealer Spreads'] = df_in['Swap__Positions_Spread_All']
    df['Money Manager Longs'] = df_in['M_Money_Positions_Long_All']
    df['Money Manager Shorts'] = df_in['M_Money_Positions_Short_All']
    df['Money Manager Spreads'] = df_in['M_Money_Positions_Spread_All']
    df['Other Reportable Longs'] = df_in['Other_Rept_Positions_Long_All']
    df['Other Reportable Shorts'] = df_in['Other_Rept_Positions_Short_All']
    df['Other Reportable Spreads'] = df_in['Other_Rept_Positions_Spread_All']
    df['Total Reportable Longs'] = df_in['Tot_Rept_Positions_Long_All']
    df['Total Reportable Shorts'] = df_in['Tot_Rept_Positions_Short_All']
    df['Non Reportable Longs'] = df_in['NonRept_Positions_Long_All']
    df['Non Reportable Shorts'] = df_in['NonRept_Positions_Short_All']
    # Save DataFrame
    full_path_to_file = os.path.join(oc.cfg['default']['data'], 'COT', cot_type, '{}.csv'.format(stem))

    if os.path.exists(full_path_to_file):
        pd.read_csv(full_path_to_file).append(df).drop_duplicates().to_csv(full_path_to_file, index=False)

    else:
        df.to_csv(full_path_to_file, index=False)
        

def process_group(df, cot_names, cot_type, stems):
    """Process a group

    :param df: DataFrame - Filtered for a specific market
    :param cot_names: list - Unique ICE COT names extracted from the report
    :param cot_type: str - COT Type
    :param stems: dict - Dictionary of ICE COT ids with associated Stems
    """
    for cot_name in cot_names:
        if cot_name in stems:
            process_stem(df[df['CFTC_Commodity_Code'] == cot_name], cot_type, stems[cot_name])


def get_data_by_year(year):
    """Get ICE COT data by year

    :param year: int - Year to get data
    """
    log = logging.getLogger(__name__)

    log.info('Get ICE COT Data for year {}'.format(year))
    stems = list_stem_by_cot()
    # Get data
    url = 'https://www.theice.com/publicdocs/futures/COTHist{}.csv'.format(year)
    df = pd.read_csv(url)
    # Process data
    cot_names = df['CFTC_Commodity_Code'].unique()
    process_group(df[df['FutOnly_or_Combined'] == 'FutOnly'], cot_names, 'FuturesOnly', stems)
    process_group(df[df['FutOnly_or_Combined'] == 'Combined'], cot_names, 'FuturesAndOptions', stems)


def get_all_data():
    """Get all ICE COT data"""
    for year in range(2011, dt.datetime.now().year+1):
        get_data_by_year(year)


def get_last_data():
    """Get ICE COT latest data"""
    get_data_by_year(dt.datetime.now().year)

