import logging
import pandas_market_calendars as pmc

import backtrader as bt

import omega.core.chain as occ
import omega.raid.events as ore


class DefaultStrategy(bt.Strategy):
    """
    Default strategy is base for all new strategies.
    In inherited class only next() method has to be defined (see example in TestTradeMulti).
    """

    def __init__(self, chains):
        self.logger = logging.getLogger(__name__)

        # Internal Strategy Variables
        self.date = self.datas[0].datetime.date  # Reference
        self.order = None  # To keep track of pending orders
        # Future Chains
        self.chains = chains
        self.names = {}
        for idx, fc in enumerate(self.chains):
            names = [n for n in self.getdatanames() if n[:2] == fc.stem]
            self.chains[idx] = fc.filter_chain(names)
            self.names[fc] = names
        self.log(logging.INFO, 'Symbols per chain: {}'.format(self.names))
        # Internals
        self.calendars = {}
        self.exits = {}
        for fc in self.chains:
            # Calendar
            start, end = fc.get_start_end(extra_days=True)
            # TODO: Get proper exchange! NYSE covers all american holidays!
            self.calendars[fc] = pmc.get_calendar('NYSE').valid_days(start, end)
            # Exits
            self.exits[fc] = ore.get_dates(ore.Events.LastDay, self.calendars[fc], fc.chain, -2)

    def get_fdata(self, chain, debug=False):
        datas = [self.datas[x] for x in range(1, len(self.datas)) if self.datas[x]._name[:2] == chain.stem]
        fdata = [(i, dta) for i, dta in enumerate(datas) if len(dta) and chain.last_date(i).date() >= self.date(0)]
        if not fdata:
            return None
        # Do not do anything if holiday
        if self.date(0) not in self.calendars[chain]:
            self.log(logging.INFO, 'Holiday: {}'.format(self.date(0)))
            return None
        # Debugging
        chain = ['(Index: {} - Name: {} - Date: {})'.format(fdata[i][0], fdata[i][1]._name, fdata[i][1].datetime.date(0)) for i, dta in enumerate(fdata)]
        if debug:
            self.log(logging.DEBUG, 'Reference: {} - {}'.format(self.date(0), chain))

        return fdata

    def log(self, level, message):
        self.logger.log(level, '{} - {}'.format(self.date(0), message))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return
        # Check if an order has been completed
        if order.status in [order.Completed]:
            side = 'Buy' if order.isbuy() else 'Sell'
            message = '{} - Execution ({}) - Price: {}, Cost: {:.2f}, Comms: {:.2f}'
            self.log(logging.INFO, message.format(order.data._name, side, order.executed.price, order.executed.value, order.executed.comm))
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(logging.WARNING, '{} - Order Cancelled/Margin/Rejected'.format(order.data._name))

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(logging.INFO, '{} - Trade PnL - Gross: {:.2f}, Net: {:.2f}'.format(trade.data._name, trade.pnl, trade.pnlcomm))

    def prenext(self):
        self.next()

    def stop(self):
        # Output positions only if status ActiveLive!
        if self.chains[0].status == occ.Status.ActiveLive:
            for fc in self.chains:
                # Get Data for the chain
                fdata = self.get_fdata(fc)
                if fdata is None:
                    continue
                # Go through data
                for fd in fdata:
                    # Variables
                    i = fd[0]
                    name, pos = self.names[fc][i], self.getpositionbyname(self.names[fc][i])
                    self.log(logging.INFO, '{} - Position: {} - Price: {}'.format(name, pos.size, pos.price))
