import calendar
import datetime as dt
import dateutil.relativedelta as rd
import dateutil.rrule as rrule
import pandas as pd

import omega.core.instrument as i
import omega.data.utils as odu
import omega.configuration as oc

# TODO: Calculate the curve for the next few months for LIBOR-FF futures.
# Example: EDK7-FF, EDM7-FF, EDN7-FF, EDU7-FF, EDZ7-FF, EDH8-FF
# TODO: Calculate forecast on a quarter earlier and trade a quarter later:
# Example: FC 01 : 03 - 04 05 06, Trade: 06 - 07 08 09

# Rules
rules_maturities = {
    '01': {'ED': '06', 'FF': ['07', '08', '09']},
    '02': {'ED': '06', 'FF': ['07', '08', '09']},
    '03': {'ED': '09', 'FF': ['10', '11', '12']},
    '04': {'ED': '09', 'FF': ['10', '11', '12']},
    '05': {'ED': '09', 'FF': ['10', '11', '12']},
    '06': {'ED': '12', 'FF': ['01', '02', '03']},
    '07': {'ED': '12', 'FF': ['01', '02', '03']},
    '08': {'ED': '12', 'FF': ['01', '02', '03']},
    '09': {'ED': '03', 'FF': ['04', '05', '06']},
    '10': {'ED': '03', 'FF': ['04', '05', '06']},
    '11': {'ED': '03', 'FF': ['04', '05', '06']},
    '12': {'ED': '06', 'FF': ['07', '08', '09']}
}

debug = True


def calculate_liborffm():
    # Get data
    libor = odu.get_index('LIBOR', '1986-01-01')
    ff = odu.get_index('FF', '1986-01-01')
    # Monthy resample
    liborm = libor.resample('M').mean()
    ffm = ff.resample('M').mean()
    # Difference
    liborff = liborm['Last'] - ffm['Last']

    return liborff


def months_generator(start, interval=1):
    """Create a generator of months end (set interval to 3 for quarters)

    :param start: Start Date
    :param interval: Numbers of months between each observations
    :return:
    """

    # Generate a list of quarters
    months = list(rrule.rrule(rrule.MONTHLY, interval=interval, dtstart=start, until=dt.datetime.today()))
    return (dt.datetime(q.year, q.month, calendar.monthrange(q.year, q.month)[1]) for q in months)


def add_diffs(df, start, field='cl'):
    df.loc[:, 'diff'] = df[field] - df[field].shift(1)
    return df[df['Dt'] > start]


def get_last_value(df, date, ctrmth):
    try:
        return float(df[df.index < date].tail(1)['Close'])
    except Exception:
        print('DF null, return 0 for: {} {}'.format(ctrmth, date))
        return 0


def get_forecasts_and_data():
    start = dt.datetime(2016, 1, 1)

    liborff = calculate_liborffm()
    fcs = []
    dfs = []
    for m in months_generator(start):
        date = m.strftime('%Y-%m-%d')
        m_rule = m.strftime('%m')
        if debug:
            print('Process Month with ending: {}!'.format(date))
        # ED
        ed_rule = rules_maturities[m_rule]['ED']
        ed_ctrmth = int('{}{}'.format(int(date[0:4]) + (1 if m_rule in ['09', '10', '11', '12'] else 0), ed_rule))
        if debug:
            print('ED {} {}'.format(date, ed_ctrmth))
        # FF
        ff_rule = rules_maturities[m_rule]['FF']
        plus_one = ['06', '07', '08', '09', '10', '11', '12']
        ff_ctrmth = [int('{}{}'.format(int(date[0:4]) + (1 if m_rule in plus_one else 0), r)) for r in ff_rule]
        if debug:
            print('FF {} {}'.format(date, ff_ctrmth))
        # Get dataframes
        start_m = (m - rd.relativedelta(months=1)).strftime('%Y-%m-%d')
        next_m = (m + rd.relativedelta(months=1)).strftime('%Y-%m-%d')
        ed_df = odu.get_market_df('{}{}'.format('ED', i.ym_maturity(ed_ctrmth)), start_m, next_m)
        ff_df = [odu.get_market_df('{}{}'.format('FF', i.ym_maturity(cm)), start_m, next_m) for cm in ff_ctrmth]
        if False:
            print(ed_df.tail())
            [print(df.tail()) for df in ff_df]
        # Calculate Forecast
        ed_value = get_last_value(ed_df, date, ed_ctrmth)
        if ed_value == 0:
            print('Null value for ED!')
        ff_values = [get_last_value(ff_df[x], date, ff_ctrmth[x]) for x in range(0, 3)]
        if sum(ff_values) == 0:
            print('All values are null for date: {} - see: {}!'.format(date, ff_values))
            continue
        # Calculate forecast and add to the list
        ff_values = [v for v in ff_values if v > 0]
        fc = (100 - ed_value) - (100 - sum(ff_values) / len(ff_values))
        fcs.append([date, fc])
        if debug:
            print('Values: {} {} - Forecast: {:.2f} - LIBORFF: {:.2f}'.format(ed_value, ff_values, fc, liborff[date] * 100))
        # Construct DataFrame and add to the list
        sfc = pd.Series(data=[(fc - liborff[date] * 100) for _ in range(len(ed_df.index))], index=ed_df.index)
        df = pd.concat([ed_df['Close'], ff_df[0]['Close'], ff_df[1]['Close'], ff_df[2]['Close'], sfc], axis=1)
        df.columns = ['ED', 'FF1', 'FF2', 'FF3', 'FC']
        df = df[df.index > date]
        if debug:
            print(df.head())
        dfs.append(df.dropna())

    # DataFrame
    return pd.concat(dfs)


if __name__ == '__main__':
    df = get_forecasts_and_data()

    df.to_csv('data.txt', index=True)
