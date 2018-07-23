import xlwings as xw

import omega.core.instrument as oci


@xw.func
@xw.arg('maturity', doc='Maturity (short format)')
@xw.arg('length', doc='Number of months to the next maturity')
def next_maturity(maturity, length):
    """Returns the next maturity for a specific maturity. To be used in Positions sheet

    :param maturity: String maturity (short format: U7)
    :param length: Number of months between the maturities
    :return: Next maturity (keeping the same format)
    """
    nm = oci.next_maturity(maturity, length, short_maturity=True)
    return nm


@xw.func()
@xw.arg('symbol', doc='Ticker (customized format)')
def diff_month(symbol):
    """Returns the number of months between the 2 contracts of the spread

    :param symbol: String symbol - Customized ticker
    :return: Int number of months
    """
    ms = oci.get_maturities(oci.check_ticker(symbol))
    return oci.diff_month(oci.int_maturity(ms[0]), oci.int_maturity(ms[1]))


@xw.func
@xw.arg('symbol', doc='Ticker (customized format)')
@xw.arg('quantity', doc='Trade quantity')
def lots(symbol, quantity):
    """Returns the number of lots traded for a symbol

    :param symbol: String symbol - Customized ticker
    :param quantity: Int Quantity traded
    :return: Int corresponding to the number of lots for the trade (useful for spreads, butterflies, etc...)
    """
    lo = 0
    if symbol is not None:
        lo = oci.lots(symbol) * quantity
    return lo


@xw.func
@xw.arg('account', doc='Account')
@xw.arg('symbol', doc='Ticker (customized format)')
@xw.arg('quantity', doc='Trade quantity')
@xw.arg('tdate', doc='Trade date')
def comms(account, symbol, quantity, tdate):
    """Calculate the comms for a trade

    :param account: String account - Account
    :param symbol: String symbol - Customized ticker
    :param quantity: Int Quantity traded
    :param tdate: Date of the transaction
    :return: Float value of the corresponding commission for the trade
    """
    return oci.comms(account, symbol, quantity, tdate)


@xw.func
@xw.arg('symbol', doc='Ticker (customized format)')
def point(symbol):
    """Calculate the point value

    :param symbol: String symbol - Customized ticker
    :return: Float Point Value for the future
    """
    return oci.get(symbol[0:2], 'Point')


@xw.func
@xw.arg('symbol', doc='Ticker (customized format)')
def check_ticker(symbol):
    """Check if the ticker is in the correct format and correct it

    :param symbol: String symbol - Customized ticker
    :return: Corrected customized ticker
    """
    return oci.check_ticker(symbol)


@xw.func
@xw.arg('symbol', doc='Ticker (customized format)')
@xw.arg('provider', doc='Data provider (CMED, T4, Reuters, etc...)')
def convert_ticker(symbol, provider):
    """Convert the provided customized ticker to the desired provider format
    
    :param symbol: String symbol - Customized ticker
    :param provider: Which provider to convert to
    :return: Converted ticker for the provider
    """
    return oci.convert_ticker(symbol, provider)


@xw.func
@xw.arg('symbol', doc='Ticker (customized format)')
def check_ticker(symbol):
    """Check the provider ticker to see if it matches the customized format

    :param symbol: String symbol - Customized ticker
    :return: String customized ticker
    """
    return oci.check_ticker(symbol)


@xw.func
@xw.arg('symbol', doc='Ticker (customized format)')
@xw.arg('maturity', doc='Maturity (short format)')
@xw.arg('position', doc='Position on this symbol')
def contract_position(symbol, maturity, position):
    """To be used in the positions sheet to find out the outright positions

    :param symbol: String symbol - Customized ticker
    :param maturity: String maturity (short format: U7) of the outright where we wan to get the position
    :param position: Int Position on the symbol
    :return: Int Number of lots on the specified outright (or empty string if no position)
    """
    # Check if the maturity is in the maturity list
    try:
        idx = oci.get_maturities(symbol, True).index(maturity)
    except ValueError:
        return ''
    # Maturity is in the list => Return the weight
    ft = oci.get_future_type(symbol)
    weights = oci.type_definition[ft]['weights']
    return weights[idx] * position


if __name__ == '__main__':
    xw.serve()
