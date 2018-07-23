import logging
import sys

import omega.core.instrument as i

"""QRow module
This module is used to provide an easy way to switch between providers to populate the Quotes sheet for all the traded
strategies.
"""

# Dictionary for fields in the quotes sheet
quotes_fields = {
    'T4': {
        'Num': 'Numerator',
        'Den': 'Denominator',
        'BidS': 'Bid_Volume',
        'Bid': 'Bid_Price',
        'Ask': 'Offer_Price',
        'AskS': 'Offer_Volume',
        'Open': 'Open_Price',
        'High': 'High_Price',
        'Low': 'Low_Price',
        'Last': 'Last_Trade_Price',
        'Settlement': 'Settlement_Price'
    },
    'CMED': {
        'BidS': 'BidQuantity',
        'Bid': 'BidPrice',
        'Ask': 'OfferPrice',
        'AskS': 'OfferQuantity',
        'Open': 'OpenTradePrice',
        'High': 'HighestTradePrice',
        'Low': 'LowestTradePrice',
        'Last': 'LastTradePrice',
        'Volume': 'Volume',
        'Settlement': 'SettlementPrice'
    },
    'Reuters': {
        'BidS': 'BIDSIZE',
        'Bid': 'BID',
        'Ask': 'ASK',
        'AskS': 'ASKSIZE',
        'Open': 'OPEN_PRC',
        'High': 'CF_HIGH',
        'Low': 'CF_LOW',
        'Last': 'CF_CLOSE',
        'Volume': 'CF_VOLUME',
        'Settlement': 'SETTLE'
    }
}


class QuoteRow:
    """Abstract class to be used in the excel populate function to provide an easy way to switch between providers.
    """
    index = 0
    ticker = ''
    i_type = ''
    row = None

    def __init__(self, index, ticker):
        """Constructor

        :param index: Int index of the row (location on the sheet)
        :param ticker: Customized ticker
        """
        self.index = index
        self.ticker = ticker
        self.i_type = i.get_type(ticker)
        self.row = []

    def get_row(self):
        """Get the created row to paste it in Excel

        :return: List to be pasted onto Excel
        """
        return self.row

    def add_ticker(self):
        self.row.append(self.ticker)

    def add_converted_ticker(self, provider):
        self.row.append(i.convert_ticker(self.ticker, provider))

    def add_value(self, value):
        self.row.append(value)

    def add_wp(self):
        pass

    def add_tick(self):
        pass

    def add_field_formula(self, field):
        pass


class T4Row(QuoteRow):
    """CTS T4 implementation of QuoteRow
    """
    def add_wp(self):
        self.row.append('=(H{0}*J{0}+I{0}*K{0})/(H{0}+K{0})'.format(self.index))

    def add_tick(self):
        self.row.append('=F{0}/G{0}'.format(self.index))

    def add_field_formula(self, field):
        try:
            new_field = quotes_fields['T4'][field]
        except KeyError:
            new_field = field
        self.row.append('=T4Screen|\'{}\'!{}'.format(i.convert_ticker(self.ticker, 'T4'), new_field))


class CMEDRow(QuoteRow):
    """CME Direct implementation of QuoteRow
    """
    def add_wp(self):
        self.row.append('=IF((G{0}-F{0})>O{0},(F{0}+G{0})/2,(E{0}*G{0}+F{0}*H{0})/(E{0}+H{0}))'.format(self.index))

    def add_tick(self):
        if 'O' in self.i_type:
            self.row.append('=CMED.CD(C{}, "TickSize")*100'.format(self.index))
        else:
            self.row.append('=CMED.CD(C{}, "TickSize")'.format(self.index))

    def add_field_formula(self, field):
        try:
            new_field = quotes_fields['CMED'][field]
        except KeyError:
            new_field = field
        if ('O' in self.i_type) and \
                (field == 'Bid' or field == 'Ask' or 'Open' in field or
                'High' in field or 'Low' in field or 'Last' in field or 'Settlement' in field):
            self.row.append('=IFERROR(CMED.MD(C{}, "{}")*100, "")'.format(self.index, new_field))
        else:
            self.row.append('=IFERROR(CMED.MD(C{}, "{}"), "")'.format(self.index, new_field))


class ReutersRow(QuoteRow):
    """Reuters implementation of QuoteRow
    """
    def add_wp(self):
        if 'ED' in self.ticker or 'FF' in self.ticker:
            self.row.append('=IF(MROUND((G{0}-F{0}), O{0})>O{0},(F{0}+G{0})/2,(E{0}*G{0}+F{0}*H{0})/(E{0}+H{0}))'.format(self.index))
        else:
            self.row.append('=IFERROR((E{0}*G{0}+F{0}*H{0})/(E{0}+H{0}),N{0})'.format(self.index))

    def add_tick(self):
        # TODO: ED has half tick (implement if needed)
        self.row.append(i.get(self.ticker[0:2], 'Tick'))

    def add_field_formula(self, field):
        try:
            new_field = quotes_fields['Reuters'][field]
        except KeyError:
            new_field = field
        if ('ED' in self.ticker or 'FF' in self.ticker) and \
                (field == 'Bid' or field == 'Ask' or 'Open' in field or
                'High' in field or 'Low' in field or 'Last' in field or 'Settlement' in field):
            self.row.append('=RData(C{}, "{}")*100'.format(self.index, new_field))
        else:
            self.row.append('=RData(C{}, "{}")'.format(self.index, new_field))


def create_row(index, ticker, headers, provider='T4', row_type='Generated'):
    """Create the symbol's row to paste directly into Excel (with relevant formulas) for a specific provider.

    :param index: Int index of the row (location on the sheet)
    :param ticker: Customized ticker
    :param headers: All the fields needed for the quotes
    :param provider: Datafeed provider
    :param row_type: Str Manual or Generated
    :return: List row to be pasted in Excel
    """
    log = logging.getLogger(__name__)

    log.debug('Create Row')
    # Instantiate
    row_class = getattr(sys.modules[__name__], '{}Row'.format(provider))
    row = row_class(index, ticker)
    # Go through all the fields
    for f in headers:
        if 'Ticker' in f:
            row.add_ticker()
        elif 'Bloomberg' in f or 'T4' in f or 'CMED' in f or 'Reuters' in f:
            row.add_converted_ticker(f)
        elif 'Generated' in f:
            row.add_value(row_type)
        elif 'WP' in f:
            row.add_wp()
        elif 'Tick' in f:
            row.add_tick()
        else:
            row.add_field_formula(f)

    return row.get_row()


if __name__ == '__main__':
    ro = CMEDRow(5, 'EDS12Z9')
    ro.add_converted_ticker('Bloomberg')
    ro.add_field_formula('Bid')
    getattr(getattr(sys.modules[__name__], '{}Row'.format('CMED')), 'add_wp')(ro)
    print(ro.get_row())
