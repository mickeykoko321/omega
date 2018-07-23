import datetime as dt
import logging
import os

import omega.configuration as c
import omega.xl.qrow as qr

logger = logging.getLogger(__name__)

try:
    import xlwings as xlw
except ImportError:
    logger.error('xlwings module can''t be imported!')


"""Excel module

This module is used for interaction between Python code and the Excel workbook (the functions are common to all the
traded strategies).
"""


def screen_updating(func):
    """Decorator for some functions in this notebook, disable screen updating before calling the function and re-enable
    it afterwards

    :param func: Function to be decorated
    """
    def wrapper_func(*args, **kwargs):
        log = logging.getLogger(__name__)

        log.debug('Disable screen updating in excel')
        xlw.apps[0].screen_updating = False
        ret_val = func(*args, **kwargs)
        log.debug('Enable screen updating in excel')
        xlw.apps[0].screen_updating = True
        return ret_val
    return wrapper_func


@screen_updating
def populate_workbook(workbook, tickers, provider):
    """Populate the Quote sheet with formulas depending on the header. This should be used each time we have a change
    in the traded universe (or if we add manual rows).

    :param workbook: Object Workbook
    :param tickers: List of tickers
    :param provider: Which data provider
    """
    log = logging.getLogger(__name__)

    log.debug('Populate {} book - provider: {}'.format(workbook, provider))
    # Processing
    sheet = workbook.sheets['Quotes']
    sheet.range('C1').value = provider  # Amend header to reflect the change in provider
    headers = sheet.range('A1').expand('right').value
    idx_gen = headers.index('Generated')
    index = 1
    rows = []
    # Populate Manuals
    manuals = sheet.range('A2').expand().value
    if manuals is not None:
        for row in manuals:
            if 'Manual' in row[idx_gen]:
                index += 1
                rows.append(qr.create_row(index, row[0], headers, provider, row[idx_gen]))
    # Go through all the tickers in the serie
    for s in tickers:
        # Create the row
        index += 1
        rows.append(qr.create_row(index, s, headers, provider))
    # Erase all the sheet
    sheet.range('A2:Z1000').clear_contents()
    sheet.range((2, 1)).value = rows


@screen_updating
def update_sheet(workbook, sheet, location, df):
    """Update excel sheet given a book and sheet names, a location and a dataframe to update with.

    :param workbook: Object workbook
    :param sheet: string sheet name
    :param location: string range on the sheet
    :param df: Dataframe to be paste on the sheet
    """
    log = logging.getLogger(__name__)

    log.debug('Update sheet on book {} - sheet {} - location {}'.format(workbook, sheet, location))
    # Copy to excel sheet (clear content first)
    sheet = workbook.sheets[sheet]
    sheet.range(location).clear_contents()
    sheet.range(location.split(':')[0]).options(index=False, header=False).value = df


def init(book):
    """Initialize a book (opens it if not open).

    :param book: str - Book's name
    :return: object Workbook - Return the workbook
    """
    log = logging.getLogger(__name__)

    try:
        wb = xlw.apps[0].books[c.cfg['excel'][book]]
    except IndexError:
        log.info('{} not open! Opening it'.format(book))
        wb = xlw.Book(os.path.join(c.cfg['default'][book], c.cfg['excel'][book]))
    return wb


def check_status(workbook, cell):
    """Check if a macro has been ran already

    :param workbook: Object Workbook
    :param cell: Cell location (to be defined in the relevant caller function)
    :return: Boolean value indicating if the macro has been ran
    """
    log = logging.getLogger(__name__)

    log.debug('Check status')
    return workbook.sheets['Trades'].range(cell).value


def update_status(workbook, cell):
    """Update the status to indicate that a macro has been ran

    :param workbook: Object Workbook
    :param cell: Cell location (to be defined in the relevant caller function)
    """
    log = logging.getLogger(__name__)

    log.debug('Update status')
    workbook.sheets['Trades'].range(cell).value = True


def is_active(workbook, sheet):
    """Returns whether or not a sheet is active

    :param workbook: Object Workbook
    :param sheet: Sheet name to be checked
    :return: Boolean
    """
    log = logging.getLogger(__name__)

    log.debug('Active sheet: {}'.format(workbook.sheets.active.name))
    return workbook.sheets.active.name == sheet


def cycle(workbook):
    """Cycle function to be used in scheduling.

    :param workbook: Object Workbook
    """
    log = logging.getLogger(__name__)

    log.info('Cycle time: {}!'.format(dt.datetime.now()))
    if not is_active(workbook, 'Transactions'):
        log.debug('Transactions sheet not active, process cycle')


def save_and_quit(workbook):
    """Save and Quit the specified workbook (all other notebooks won't be saved!).

    :param workbook: Object Workbook
    """
    log = logging.getLogger(__name__)

    log.info('Save and quit Excel')
    workbook.save()
    xlw.apps[0].quit()


if __name__ == '__main__':
    pass



