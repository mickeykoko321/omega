"""Test Strategy module"""
import logging
import pandas_market_calendars as pmc
import time

import backtrader as bt

import omega.configuration as oc
import omega.raid.backtrade as orb
import omega.raid.default_strategy as ords
import omega.raid.events as ore


class Test(bt.Strategy):
    """Test Strategy to check data is loaded correctly"""
    params = (('chain', None),)

    def __init__(self):
        self.log = logging.getLogger(__name__)

        # Internal Strategy Variables
        self.date = self.datas[0].datetime.date  # Reference
        self.order = None  # To keep track of pending orders
        self.names = self.getdatanames()
        del self.names[0]  # Remove Reference
        self.debug('Symbols: {}'.format(self.names))
        # Parameters
        self.chain = self.p.chain.filter_chain(self.names)

    def debug(self, message):
        self.log.debug('{} - {}'.format(self.date(0), message))

    def prenext(self):
        self.next()

    def next(self):
        if self.order:
            return
        # Initialize Data
        fdata = [(i, dta) for i, dta in enumerate(self.datas[1:]) if len(dta) and self.chain.last_date(i).date() >= self.date(0)]
        if not fdata:
            return
        # Debugging
        chain = ['(Index: {} - Date: {})'.format(fdata[i][0], fdata[i][1].datetime.date(0)) for i, dta in enumerate(fdata)]
        self.debug('Reference: {} - {}'.format(self.date(0), chain))


class TestMulti(bt.Strategy):
    """Test Multi Strategy to check data is loaded correctly"""
    params = (('chains', None),)

    def __init__(self):
        self.log = logging.getLogger(__name__)

        # Internal Strategy Variables
        self.date = self.datas[0].datetime.date  # Reference
        self.order = None  # To keep track of pending orders
        self.names = self.getdatanames()
        del self.names[0]  # Remove Reference
        self.debug('Symbols: {}'.format(self.names))
        # Future Chains
        self.chains = self.p.chains
        self.chain_names = []
        for idx, fc in enumerate(self.chains):
            names = [n for n in self.names if n[:2] == fc.stem]
            self.chains[idx] = fc.filter_chain(names)
            self.chain_names.append(names)

    def debug(self, message):
        self.log.debug('{} - {}'.format(self.date(0), message))

    def prenext(self):
        self.next()

    def next(self):
        if self.order:
            return
        for fc in self.chains:
            self.debug(fc.stem)
            datas = [self.datas[x] for x in range(1, len(self.datas)) if self.datas[x]._name[:2] == fc.stem]
            fdata = [(i, dta) for i, dta in enumerate(datas) if len(dta) and fc.last_date(i).date() >= self.date(0)]
            if not fdata:
                return
            # Debugging
            chain = ['(Index: {} - Name: {} - Date: {})'.format(fdata[i][0], fdata[i][1]._name, fdata[i][1].datetime.date(0)) for i, dta in enumerate(fdata)]
            self.debug('Reference: {} - {}'.format(self.date(0), chain))


class TestTrade(bt.Strategy):
    """Test Trade to test we can trade"""
    params = (('chain', None),)

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Internal Strategy Variables
        self.date = self.datas[0].datetime.date  # Reference
        self.order = None  # To keep track of pending orders
        self.names = self.getdatanames()
        del self.names[0]  # Remove Reference
        self.log(logging.INFO, 'Symbols: {}'.format(self.names))
        # Parameters
        self.chain = self.p.chain.filter_chain(self.names)
        # Calendar
        start, end = self.chain.get_start_end(extra_days=True)
        self.calendar = pmc.get_calendar('CME').valid_days(start, end)
        # Exits
        self.exits = ore.get_dates(ore.Events.LastDay, self.calendar, self.chain.chain, -2)

    def log(self, level, message):
        self.logger.log(level, '{} - {}'.format(self.date(0), message))

    def notify_order(self, order):
        name = order.data._name
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return
        # Check if an order has been completed
        if order.status in [order.Completed]:
            side = 'Buy' if order.isbuy() else 'Sell'
            message = '{} - Execution ({}) - Price: {:.2f}, Cost: {:.2f}, Comms: {:.2f}'
            self.log(logging.INFO, message.format(name, side, order.executed.price, order.executed.value, order.executed.comm))
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(logging.WARNING, '{} - Order Cancelled/Margin/Rejected'.format(name))

        self.order = None

    def notify_trade(self, trade):
        name = trade.data._name
        if not trade.isclosed:
            return
        self.log(logging.INFO, '{} - Trade PnL - Gross: {:.2f}, Net: {:.2f}'.format(name, trade.pnl, trade.pnlcomm))

    def prenext(self):
        self.next()

    def next(self):
        if self.order:
            return
        # Initialize Data
        rdata = self.datas[0]  # Reference - This might not be needed as we already have self.dates(0)!
        fdata = [(i, dta) for i, dta in enumerate(self.datas[1:]) if len(dta) and self.chain.last_date(i).date() >= self.date(0)]
        # Do not do anything if no data
        if not fdata:
            return
        # Do not do anything if holiday
        if self.date(0) not in self.calendar:
            self.log(logging.INFO, 'Holiday: {}'.format(self.date(0)))
            return
        # Debugging
        chain = ['(Index: {} - Name: {} - Date: {})'.format(fdata[i][0], fdata[i][1]._name, fdata[i][1].datetime.date(0)) for i, dta in enumerate(fdata)]
        self.log(logging.DEBUG, 'Reference: {} - {}'.format(self.date(0), chain))
        # Strategy
        for fd in fdata:
            # Variables
            i, dta = fd[0], fd[1]
            name, pos = self.names[i], self.getpositionbyname(self.names[i])
            # Entry
            if not pos and self.date(0) < self.exits[i]:
                self.log(logging.INFO, '{} - Entry on first bar!'.format(name))
                if self.date(0).day % 2 == 0:  # Sell on even days
                    self.log(logging.INFO, '{} - Sell Order (Front) @ {}'.format(name, dta.close[0]))
                    self.order = self.order_target_size(data=dta, target=-1)
                else:
                    self.log(logging.INFO, '{} - Buy Order (Front) @ {}'.format(name, dta.close[0]))
                    self.order = self.order_target_size(data=dta, target=1)

            # Final Exit
            if pos and self.date(0) == self.exits[i]:
                self.log(logging.INFO, '{} - Exit on last bar @ {}!'.format(name, dta.close[0]))
                self.order = self.close(data=dta, exectype=bt.Order.Close)


class TestTradeMulti(ords.DefaultStrategy):
    """Test Trade Multi to test we can trade multiple instruments and inheritance of the default strategy"""
    params = (('chains', None), ('param1', 10), ('param2', {'FC': 4, 'LC': 5, 'LH': 6}))

    def __init__(self):
        super().__init__(self.p.chains)
        self.log(logging.INFO, 'Param1: {} - Param2: {}'.format(self.p.param1, self.p.param2))

    def next(self):
        if self.order:
            return
        # Initialize Data
        for fc in self.chains:
            # Get Data for the chain
            fdata = self.get_fdata(fc)
            if fdata is None:
                continue
            # Strategy
            for fd in fdata:
                # Variables
                i, dta = fd[0], fd[1]
                name, pos = self.names[fc][i], self.getpositionbyname(self.names[fc][i])
                # Entry
                if not pos and self.date(0) < self.exits[fc][i]:
                    self.log(logging.INFO, '{} - Entry on first bar!'.format(name))
                    if self.date(0).day % 2 == 0:  # Sell on even days
                        self.log(logging.INFO, '{} - Sell Order (Front) @ {}'.format(name, dta.close[0]))
                        self.order = self.order_target_size(data=dta, target=-1)
                    else:
                        self.log(logging.INFO, '{} - Buy Order (Front) @ {}'.format(name, dta.close[0]))
                        self.order = self.order_target_size(data=dta, target=1)
                # Final Exit
                if pos and self.date(0) == self.exits[fc][i]:
                    self.log(logging.INFO, '{} - Exit on last bar @ {}!'.format(name, dta.close[0]))
                    self.order = self.close(data=dta, exectype=bt.Order.Close)


def test_test_trade_single():
    start = time.time()
    mode = orb.Mode.Backtest
    oc.initialization('backtest-single-logs.txt')
    pnl, _ = orb.run_single_bt(mode, 'LC', 100000.0, TestTrade)
    print('Execution time: {:.0f} seconds!'.format(time.time() - start))
    start = time.time()
    oc.initialization('backtest-multi-logs.txt')
    pnl_s, _ = orb.run(mode, ['LC'], 100000.0, TestTradeMulti)
    print('Execution time: {:.0f} seconds!'.format(time.time() - start))
    print('Total PnL for the normal runs: {}.'.format(pnl))
    print('Total PnL for the multi-run: {}.'.format(pnl_s))
    assert pnl == pnl_s


def test_test_trade_multi():
    oc.initialization('backtest-single-logs.txt')
    mode = orb.Mode.Backtest
    pnl1, _ = orb.run_single_bt(mode, 'FC', 100000.0, TestTrade)
    pnl2, _ = orb.run_single_bt(mode, 'LH', 100000.0, TestTrade)
    oc.initialization('backtest-multi-logs.txt')
    pnl_t = orb.run(mode, ['FC', 'LH'], 100000.0, TestTradeMulti)
    print('Total PnL for the normal runs: {}.'.format(pnl1 + pnl2))
    print('Total PnL for the multi-run: {}.'.format(pnl_t))
    assert pnl1 + pnl2 == pnl_t


def test_backtest():
    start = time.time()
    mode = orb.Mode.Backtest
    oc.initialization('test-backtest-logs.txt')
    params = orb.FuturesBacktest().get_parameters(TestTradeMulti, ['FC'])
    pnl, _ = orb.run(mode, ['FC'], 1000000.0, TestTradeMulti, **params)
    print('Execution time: {:.0f} seconds!'.format(time.time() - start))
