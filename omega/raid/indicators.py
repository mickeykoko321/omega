import logging

import omega.data.cot as odc

import backtrader as bt


class COT(bt.Indicator):
    """Class COT Indicator - Make HPS and HPH accessible inside an indicator for ease of use."""
    lines = ('hps', 'hph', 'hps_slope',)
    params = (('stem', None),)

    def __init__(self, cot_type='F'):
        self.log = logging.getLogger(__name__)
        df = odc.cot_data(self.p.stem, cot_type)
        df = df[['HPH', 'HPS', 'HPSSlope']]
        # Need to add extra rows for live trading (as the data is weekly)
        next_date = odc.next_release_date(df.index[-1])
        df.loc[next_date] = [0, 0, 0]
        df = df.resample('D').ffill()
        self.df = df

    def next(self):
        # Get Data Reference Value
        date = str(self.datas[0].datetime.date(0))
        # Get Value in the DataFrame
        try:
            row = self.df[self.df.index == date].iloc[0]
        except IndexError:
            raise Exception('Reference date: {} is not in the COT DataFrame for {}, check COT Data!'.format(date, self.p.stem))
        # Update Indicator lines
        self.lines.hps[0] = row.HPS
        self.lines.hps_slope[0] = row.HPSSlope
        self.lines.hph[0] = row.HPH
