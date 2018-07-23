import datetime as dt
import importlib as ilib
import logging
import optparse
import os
import pandas.tseries.offsets as off
import sys

import omega.configuration as oc
import omega.logger.filter_logs as olf
import omega.mail as om
import omega.core.chain as occ
import omega.data.download as odd
import omega.data.icecot as odi
import omega.raid.backtrade as orb
import omega.xl.excel as oxe
import omega.xl.utils as oxu


log = logging.getLogger(__name__)

# Alpha Module Import: If can't be imported then no live strategy can be ran
try:
    import alpha.harvester as ah
    import alpha.roll_return as arr
except ImportError as e:
    log.error('Alpha Modules can''t be imported!')

# Dynamic module import for easy easy referencing
try:
    books = {'curvature': ilib.import_module('omega.xl.curvature'), 'spreading': ilib.import_module('omega.xl.spreading')}
except ImportError:
    log.error('Problem while importing strategies module (Curvature/Spreading)!')


def init(mode=None):
    """Initialization function (for logger and parsing options)
    
    :param mode: Mode to run: snap, populate, positions, import or daily.
    :return: mode and options
    """
    opts = []
    if mode is None:
        # Option Parser
        parser = optparse.OptionParser(usage="""\nChoose a mode to run: snap, populate, positions, ...""")
        parser.add_option('-b', '--book', dest='book', default='curvature', help='Which book to target.')
        parser.add_option('-c', '--cash', dest='cash', default='None', help='Starting portfolio value.')
        parser.add_option('-d', '--date', dest='date', default=None, help='Date for day import.')
        parser.add_option('-m', '--markets', dest='markets', default=None, help='Markets on which to run the strategy.')
        parser.add_option('-s', '--strategies', dest='strategies', default=None, help='Strategies to run Live.')
        opts, args = parser.parse_args()
        try:
            mode = args[0]
        except IndexError:
            parser.print_help()
            sys.exit(1)
    # Change logging file
    oc.initialization('{}-logs.txt'.format(mode))

    return mode, opts


def macros(mode, book, **kwargs):
    """Run Functions to interact with Excel

    :param mode: str - Mode to run
    :param book: str - Which book to run the macro on.
    """
    logger = logging.getLogger(__name__)

    if 'snap' in mode:
        if book != 'curvature':
            logger.error('Macro only supported for curvature book!')
            sys.exit(1)
        logger.info('Snap Quotes')
        books[book].snap_quotes()
    elif 'populate' in mode:
        logger.info('Populate Quotes')
        universe = kwargs['universe'] if 'universe' in kwargs else None
        books[book].populate(universe=universe)
    elif 'positions' in mode:
        if book != 'curvature':
            logger.error('Macro only supported for curvature book!')
            sys.exit(1)
        logger.info('Update Positions for ED & FF')
        books[book].positions('ED')
        books[book].positions('FF')
    elif 'risk' in mode:
        logger.info('Update Risk')
        books[book].update_risk()


def dailydownload():
    """Daily Data Download"""
    logger = logging.getLogger(__name__)

    logger.info('Daily download mode!')
    # Daily Data
    odd.download_list(occ.Status.Active)
    om.send_email('Daily Download Job Completed!', '', 'laurent.michelizza@gmail.com', text_only=True)


def daily(universe=None):
    """Spreading Daily Run (send email once done)"""
    logger = logging.getLogger(__name__)

    day = (dt.datetime.today() + off.BDay(1)).strftime('%Y-%m-%d')
    logger.info('Daily mode (spreading) for: {}!'.format(day))
    # Get spreading book
    oxe.init(books['spreading'].book)
    # Display traded list
    ldt = books['spreading'].daily_trade(universe, day)
    # Display additions/deletions
    adds, dels = oxu.daily_differences(universe, day)
    adds = 'Additions: {}'.format(adds)
    logger.info(adds)
    dels = 'Deletions: {}'.format(dels)
    logger.info(dels)
    # Any spreads within 10 days of LTD?
    ltd10 = ldt[ldt['DaysTo'] <= 10]['Ticker'].tolist()
    # Calculate indicators (roll yield, stddevs, etc...)
    books['spreading'].update_risk(universe, day)
    # Send email
    subject = '{} - Spreading Daily Run'.format(dt.datetime.today().strftime('%Y-%m-%d'))
    message = 'Run for: {}\n\n'.format(day)
    message += 'Daily trades:\n{}\n\n{}\n{}\n\n'.format(ldt, adds, dels)
    if len(ltd10) > 0:
        message += 'WARNING: Within 10 days of FND/LTD: {}'.format(ltd10)
    om.send_email(subject, message, 'laurent.michelizza@gmail.com', text_only=True)


def live(symbols, cash, strategies):
    """Run a live strategy (based on daily bars) which will generate a set of orders to be executed next day at the open

    :param symbols: list - Symbols on which to run the strategy
    :param cash: float - Portfolio start value
    :param strategies: list - Strategies to be ran
    """
    logger = logging.getLogger(__name__)

    # Need to adjust the day if we run a Saturday or Sunday (last set of orders will be generated on Friday)
    today = dt.datetime.today()
    if today.weekday() > 4:
        today -= dt.timedelta(days=today.weekday()-4)
    date = today.strftime('%Y-%m-%d')
    filename = '{}-live.txt'.format(date)
    logger.info('Run Live Trading mode for day: {}!'.format(date))
    oc.initialization(filename)
    # Run Live Mode
    strats = [{'strategy': s, 'parameters': orb.get_parameters(s, symbols)} for s in strategies]
    orb.run(orb.Mode.Live, symbols, cash, strats)
    # Extract Orders
    orders = olf.by_strings(os.path.join(oc.cfg['logging']['root'], filename), ['INFO - {}'.format(date), 'Order'])
    orders = [o.split('INFO - ')[1] for o in orders]
    # Send email
    subject = '{} - Live Run for: {}'.format(date, [s.__name__ for s in strategies])
    message = 'Run for: {}\n\n'.format(date)
    message += 'Orders:\n{}\n'.format(''.join(orders))
    om.send_email(subject, message, 'laurent.michelizza@gmail.com', text_only=True)


def main():
    """Main entry point of the program."""
    # Initialization
    mode, opts = init()
    # Logger
    logger = logging.getLogger(__name__)

    try:
        if 'snap' in mode or 'populate' in mode or 'positions' in mode or 'risk' in mode:
            logger.info('Run macro: {}'.format(mode))
            macros(mode, opts.book)
        elif 'eod' in mode:
            logger.info('End of day processing.')
            wbc = oxe.init(books['curvature'].book)
            if not oxe.check_status(wbc, 'AA2'):
                # Update Risk on Excel
                books['curvature'].update_risk()
                # Update Status
                oxe.update_status(wbc, 'AA2')
                # Save and quit
                oxe.save_and_quit(wbc)
            else:
                logger.warning('EoD has already ran for today, do not do anything!')
        elif 'dailydownload' in mode:
            # Run daily download mode
            getattr(sys.modules[__name__], mode)()
        elif 'daily' in mode:
            # Run daily mode
            symbols = None if opts.markets is None else opts.markets.split(',')
            getattr(sys.modules[__name__], mode)(symbols)
        elif 'icecot' in mode:
            # Get ICE COT latest data
            odi.get_last_data()
        elif 'live' in mode:
            symbols = opts.markets.split(',')
            strategies = opts.strategies.split(',')
            # TODO: Better way to load a strategy?
            getattr(sys.modules[__name__], mode)(symbols, float(opts.cash), [getattr(ah, s) for s in strategies])
        else:
            logger.error('Mode is not defined, exiting!')
            sys.exit(1)
    except Exception as ex:
        logger.error(ex, exc_info=True)


if __name__ == '__main__':
    main()
