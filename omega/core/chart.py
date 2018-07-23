import datetime
import highcharts as hc
import logging
import pandas as pd
import time

import omega.data.cot as odc
import omega.data.utils as odu


options1 = {
    'chart': {
        'marginRight': 50
    },
    'rangeSelector': {
        'selected': 2
    },
    'title': {
        'text': ''
    },
    'yAxis': {
        'labels': {
            'align': 'right',
            'x': 35
        },
        'height': '80%',
        'lineWidth': 2,
        'offset': 15
    }
}

options2 = {
    'chart': {
        'marginRight': 50
    },
    'rangeSelector': {
        'selected': 2
    },
    'title': {
        'text': ''
    },
    'yAxis': [{
        'labels': {
            'align': 'right',
            'x': 35
        },
        'height': '80%',
        'lineWidth': 2,
        'offset': 15
    }, {
        'labels': {
            'align': 'right',
            'x': 35
        },
        'top': '80%',
        'height': '20%',
        'offset': 15,
        'lineWidth': 2
    }],
}

options3 = {
    'chart': {
        'marginRight': 50
    },
    'rangeSelector': {
        'selected': 2
    },
    'title': {
        'text': ''
    },
    'navigator': {
        'enabled': False
    },
    'yAxis': [{
        'labels': {
            'align': 'right',
            'x': 35
        },
        'height': '60%',
        'lineWidth': 2,
        'offset': 15
    }, {
        'labels': {
            'align': 'right',
            'x': 35
        },
        'top': '60%',
        'height': '20%',
        'offset': 15,
        'lineWidth': 2
    }, {
        'labels': {
            'align': 'right',
            'x': 35
        },
        'top': '80%',
        'height': '20%',
        'offset': 15,
        'lineWidth': 2,
    }],
}


def df_highchart(trade, start=None):
    """
    
    :param trade:
    :param start:
    :return: 
    """
    log = logging.getLogger(__name__)

    df = odu.read_csv(*trade['Symbols'], weights=trade['Weights'], start_date=start, date_as_index=False, multiplier=100)
    return highchart(df, trade['Name'])


def spread(ticker, start_date=None):
    """

    :param ticker:
    :param start_date:
    :return:
    """
    log = logging.getLogger(__name__)

    df = odu.read_csv(ticker, weights=[1], start_date=start_date, date_as_index=False)
    return highchart(df, ticker, series=['OHLC', 'Volume', 'HP'])


def highchart(df, name, series=None):
    """

    :param df:
    :param name:
    :param series:
    :return:
    """
    log = logging.getLogger(__name__)

    cot = pd.DataFrame()
    if series is None:
        series = ['OHLC']
    elif 'RMN' in series or 'HP' in series:
        cot = odc.cot_data(name[0:2])  # Get COT data
        cot = cot[cot.index <= df.iloc[-1]['Date']]  # To avoid having empty spaces for expired contracts

    nb_charts = 0
    df['Date'] = pd.to_datetime(df['Date']).apply(datetime.datetime.timetuple).apply(time.mktime).apply(int) * 1000
    data_ohlc = df[['Date', 'Open', 'High', 'Low', 'Close']].values.tolist()
    chart = hc.Highstock(width=980, height=600)
    grouping_units = [['day', [1]], ['month', [1, 2, 3, 4, 6]]]
    chart.add_data_set(data_ohlc, 'candlestick', name, dataGrouping={'units': grouping_units})
    options = options1
    if 'Volume' in series:
        data_vol = df[['Date', 'Volume']].values.tolist()
        nb_charts += 1
        chart.add_data_set(data_vol, 'column', 'Volume', yAxis=nb_charts, dataGrouping={'units': grouping_units})
        options = options2
    if 'RMN' in series:
        rmn = cot['RMN'].resample('B').last().ffill()
        hps = pd.DataFrame({'Date': rmn.index, 'RMN': rmn.values})
        # Transform data for chart
        rmn['Date'] = pd.to_datetime(hps['Date']).apply(datetime.datetime.timetuple).apply(time.mktime).apply(int) * 1000
        data_cots = hps[['Date', 'RMN']].values.tolist()
        nb_charts += 1
        chart.add_data_set(data_cots, 'line', 'RMN', yAxis=nb_charts, dataGrouping={'units': grouping_units})
        options = options2
    if 'HP' in series:
        # Speculators
        hps = cot['HPS'].resample('B').last().ffill()
        hps = pd.DataFrame({'Date': hps.index, 'HPS': hps.values})
        # Hedgers
        hph = cot['HPH'].resample('B').last().ffill()
        hph = pd.DataFrame({'Date': hph.index, 'HPH': hph.values})
        # Transform data for chart
        hps['Date'] = pd.to_datetime(hps['Date']).apply(datetime.datetime.timetuple).apply(time.mktime).apply(int) * 1000
        data_hps = hps[['Date', 'HPS']].values.tolist()
        hph['Date'] = pd.to_datetime(hph['Date']).apply(datetime.datetime.timetuple).apply(time.mktime).apply(int) * 1000
        data_hph = hph[['Date', 'HPH']].values.tolist()
        nb_charts += 1
        chart.add_data_set(data_hps, 'line', 'HPS', yAxis=nb_charts, dataGrouping={'units': grouping_units})
        chart.add_data_set(data_hph, 'line', 'HPH', yAxis=nb_charts, dataGrouping={'units': grouping_units})
        options = options2
    options = options3 if nb_charts == 2 else options
    options['title']['text'] = name
    chart.set_dict_options(options)
    return chart
