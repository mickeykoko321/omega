import datetime as dt
import enum
import logging


import omega.core.chain as occ
import omega.core.instrument as oci
import omega.raid.utils as oru
import omega_ui.backtest as ob

"""Module Backtest
Contains code to run a backtest for a list of markets.
"""


class BacktradeError(Exception):
    pass


class Mode(enum.Enum):
    Backtest = 1
    Live = 2

    def __str__(self):
        return self.name


def initialize_cerebro_for_single_bt(stem, cash, mode):
    """Initialize Cerebro for a backtest. Needs cash, commissions, data and analyser.

    :param stem: str - Customized ticker
    :param cash: float - Portfolio start value
    :param mode: Enum Mode - Which mode to run: Backtest or Live?
    :return: object Cerebro, object FutureChain - These are both needed to run a backtest
    """
    log = logging.getLogger(__name__)

    # Setup Cerebro
    cerebro = ob.Backtest.setup_cerebro(cash)
    # Future Chain
    status = occ.Status.Expired if mode == Mode.Backtest else occ.Status.ActiveLive
    fc = occ.FutureChain(stem, oci.FutureType.Spread)
    fc.initialize_contracts(status, initialize_data=True)
    start, end = fc.get_start_end(extra_days=True)
    # Commissions - Note: When throwing margin rejects => due to missing data
    cerebro.broker.setcommission(commission=fc.commission * 2, margin=fc.margin, mult=fc.point)
    # Data
    end = dt.datetime.today().strftime('%Y-%m-%d') if mode == Mode.Live else end  # Needed to stop at today's bar
    cerebro = oru.add_reference_data(cerebro, start, end)
    cerebro = oru.add_chain_data(cerebro, [fc])

    return cerebro, fc


def initialize_cerebro(stems, cash, mode, future_type=oci.FutureType.Spread):
    """Initialize Cerebro for a backtest. This is the multi-market version.

    :param stems: str - Customized ticker
    :param cash: float - Portfolio start value
    :param mode: Enum Mode - Which mode to run: Backtest or Live?
    :param future_type: obj FutureType - Which type of Future do we run the backtest on
    :return: object Cerebro, object FutureChain - These are both needed to run a backtest
    """
    log = logging.getLogger(__name__)

    # Setup Cerebro
    cerebro = ob.Backtest.setup_cerebro(cash)
    # Future Chains
    status = occ.Status.Expired if mode == Mode.Backtest else occ.Status.ActiveLive
    chains = []
    min_start = str(dt.date.today())
    max_end = '1900-01-01'
    for stem in stems:
        fc = occ.FutureChain(stem, oci.FutureType.Spread)
        fc.initialize_contracts(status, days_back=90, initialize_data=True)
        try:
            # Get Start/End
            start, end = fc.get_start_end(extra_days=True)
            min_start = min(start, min_start)
            max_end = max(end, max_end)
            # Add chain to the list if start/end ok
            chains.append(fc)
        except occ.ChainError:
            log.error('{} discarded as there is a problem with the chain/data!'.format(stem))
    # Data
    end = dt.datetime.today().strftime('%Y-%m-%d') if mode == Mode.Live else max_end  # Needed to stop at today's bar
    cerebro = oru.add_reference_data(cerebro, min_start, end)
    cerebro = oru.add_chain_data(cerebro, chains, with_comms=True)

    return cerebro, chains


def run_single_bt(mode, stem, cash, strategy, **params):
    """Multi months backtest for a single market

    :param mode: Enum Mode - Which mode to run: Backtest or Live?
    :param stem: str - Market stem
    :param cash: float - Portfolio start value
    :param strategy: object - Strategy to be ran
    :param params: dictionary - Parameters to run the strategy
    """
    log = logging.getLogger(__name__)

    log.info('Backtest for mode: {}'.format(str(mode)))
    cerebro, fc = initialize_cerebro_for_single_bt(stem, cash, mode)
    # Strategy
    cerebro.addstrategy(strategy, chain=fc, **params)
    # Backtest
    results = cerebro.run()
    pnl = cerebro.broker.getvalue() - cash

    return pnl, results[0]


def run(mode, stems, cash, strategies, future_type=oci.FutureType.Spread):
    """Multi months backtest for multi markets

    :param mode: Enum Mode - Which mode to run: Backtest or Live?
    :param stems: list - Market stems
    :param cash: float - Portfolio start value
    :param strategies: list - List of strategies to be ran (passed along in a dictionary with parameters)
    :param future_type: obj FutureType - Which type of Future do we run the backtest on
    :return: float, object results - PnL, Results object to get the analyzers
    """
    log = logging.getLogger(__name__)

    log.info('Backtest for mode: {}'.format(str(mode)))
    cerebro, chains = initialize_cerebro(stems, cash, mode, future_type)
    # Strategy
    for s in strategies:
        cerebro.addstrategy(s['strategy'], chains=chains, **s['parameters'])
    # Backtest
    results = cerebro.run()
    pnl = cerebro.broker.getvalue() - cash

    return pnl, results[0]


def optimize(stems, cash, strategy, params, future_type=oci.FutureType.Spread):
    """Multi months optimization for multi markets

    :param stems: list - Market stems
    :param cash: float - Portfolio start value
    :param strategy: object - Strategy to be ran
    :param params: dictionary - Parameters to run the strategy
    :param future_type: obj FutureType - Which type of Future do we run the backtest on
    """
    log = logging.getLogger(__name__)

    log.info('Optimize parameter for: {}'.format(stems))
    cerebro, chains = initialize_cerebro(stems, cash, Mode.Backtest, future_type)
    # Strategy
    params = oru.amend_parameters_for_optimization(params)
    cerebro.optstrategy(strategy, chains=(chains,), **params)
    # Optimize
    stratruns = cerebro.run()
    # Results
    pnls = []
    for stratrun in stratruns:
        for strat in stratrun:
            trades = strat.analyzers.trades.get_analysis()
            dd_analysis = strat.analyzers.drawdown.get_analysis()
            sharpe = strat.analyzers.sharpe.get_analysis()
            pnls.append({'PnL': trades['pnl']['net']['total'], 'DD': dd_analysis['max']['drawdown'], 'Sharpe': sharpe['sharperatio']})

    return pnls, stratruns


def get_parameters(strategy, symbols):
    """Get parameters for a specific strategy and symbols. Will throw an error if there are no parameters for the
    strategy or the symbols.

    :param strategy: object - Strategy for which to get parameters
    :param symbols: list - Symbols for which to get the parameters
    :return: dict - Parameters
    """
    # Important: This works only for multi-markets!
    name = strategy.__name__
    parameters_db = oru.load_parameters(strategy.__module__)
    for strategies, params in parameters_db.items():
        if name not in strategies:
            continue
        # Check that all symbols have parameters (if the parameter is a dict)
        for k, v in params.items():
            if not isinstance(v, dict):
                continue
            for s in symbols:
                if s not in v:
                    raise BacktradeError('Parameter: {} doesn''t have a default value for: {}!'.format(k, s))
        # Check that all parameters have default values
        sparams = list(strategy.params._getkeys())
        for p in sparams:
            if 'chain' not in p and p not in params:
                raise BacktradeError('Parameter: {} doesn''t have any default values!'.format(p))
        # If make it here then we can return params - any other outcome will throw an exception
        return params

    raise BacktradeError('Strategy: {} doesn''t have any default parameters!'.format(name))


class FuturesBacktest(ob.Backtest):
    """Implements Backtest Class for Omega UI!"""
    def __init__(self, future_type=oci.FutureType.Spread):
        super().__init__()
        self.future_type = future_type

    def get_symbols(self):
        return oci.futures()

    def get_parameters(self, strategy, symbols):
        return get_parameters(strategy, symbols)

    def run(self, symbols, cash, strategy, params):
        strategies = [{'strategy': strategy, 'parameters': params}]
        return run(Mode.Backtest, symbols, cash, strategies, self.future_type)
    
    # TODO: Consider adding this method into OmegaUI as well
    def run_multi(self, symbols, cash, strategies):
        return run(Mode.Backtest, symbols, cash, strategies, self.future_type)
