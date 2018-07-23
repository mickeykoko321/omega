"""Test Lists module"""
import omega.core.chain as occ
import omega.data.download as odd
import omega.data.utils as odu


def test_get_ohlcv_data():
    df = odd.get_ohlcv_data('W_S2N18', 'daily', '1900-01-01', '2018-04-27')
    if df is not None:
        print(df.head())
        print(df.tail())


def test_fix_settlement():
    ticker = 'FCS1V12'
    df = odu.get_market_df(ticker)
    sdf = odd.fix_settlement(ticker, df, False)
    print(sdf)


def test_download_list():
    odd.download_list(occ.Status.ActivePlus, ['LC'])  # , override_last=True


def test_download_missing():
    odd.download_missing(['LH'])
