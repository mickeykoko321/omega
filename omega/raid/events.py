import datetime as dt
import enum
import pytz

import omega.core.instrument as oci
import omega.raid.utils as oru


"""Module Events
Class definitions to refer easily to specific events for trading.
"""


class EventsError(Exception):
    pass


class Event(object):
    """Generic event"""
    def __init__(self, calendar):
        self.calendar = calendar

    def date(self, ticker, last_day, days):
        """To get the event date (with a number of days in relation to the date)

        :param ticker: str - Customized ticker
        :param last_day: date - Last Trading Day for the associated ticker
        :param days: int - Number of days in relation to the date
        :return: date - Event Date
        """
        pass


class GoldmanRoll(Event):
    """Goldman Roll event"""
    def date(self, ticker, last_day, days):
        """Important: days refers to the nth day of the Goldman Roll."""
        im = oci.previous_month(ticker[-3:])
        ym_cal = [int(d.strftime('%Y%m')) for d in self.calendar]
        idx = ym_cal.index(im)
        return self.calendar[idx + days + 3].date()  # (idx is 1st)


class LastDay(Event):
    """Last Day event"""
    def date(self, ticker, last_day, days):
        """Important: set days to -2 for the exit on the day before last (we never trade the last day)."""
        idx = self.calendar.get_loc(last_day)

        return self.calendar[idx + days].date()


class SpotLimit(Event):
    """Spot Limit event"""
    def date(self, ticker, last_day, days):
        try:
            sl_type = oci.get(ticker[0:2], 'Spot')
        except oci.InstrumentError:
            raise EventsError('Spot Limit not defined in database.json!')
        if sl_type == 'Close of trading on the first business day of the contract month':
            return self._close_first_business_day(ticker, days)
        elif sl_type == 'During the last x trading days of the contract':
            nb = oci.get(ticker[0:2], 'Rule')
            return self._last_x_business_days(last_day, -nb + days)
        elif sl_type == 'x Business Day following the expiration of the regular option contract traded on the expiring futures contract':
            nb = oci.get(ticker[0:2], 'Rule')
            return self._x_business_days_after_third_friday(last_day, nb + days)
        elif sl_type == 'Close of trading x business days prior to last trading day of the contract':
            nb = oci.get(ticker[0:2], 'Rule')
            return self._last_x_business_days(last_day, -nb + days)
        elif sl_type == 'Close of trading on the business day prior to the first notice day of the delivery month':
            nb = oci.get(ticker[0:2], 'Rule')
            return self._close_first_business_day(ticker, -nb + days)
        elif sl_type == 'Close of trading x business days prior to the first trading day of the delivery month':
            nb = oci.get(ticker[0:2], 'Rule')
            return self._close_first_business_day(ticker, -nb + days)
        elif sl_type == 'On and after First Notice Day':
            return self._on_fnd(last_day, days)
        else:
            raise EventsError('Spot Limit function not defined!')

    def _close_first_business_day(self, ticker, days):
        im = oci.int_maturity(ticker[-3:])
        ym_cal = [int(d.strftime('%Y%m')) for d in self.calendar]
        idx = ym_cal.index(im)
        return self.calendar[idx + days].date()

    def _on_fnd(self, last_day, days):
        idx = self.calendar.get_loc(last_day)
        return self.calendar[idx + days].date()

    def _last_x_business_days(self, last_day, days):
        idx = self.calendar.get_loc(last_day)
        return self.calendar[idx + days].date()

    def _x_business_days_after_third_friday(self, last_day, days):
        if isinstance(last_day, str):
            last_day = dt.datetime.strptime(last_day, '%Y-%m-%d')
        year = int(last_day.strftime('%Y'))
        month = int(last_day.strftime('%m'))
        third_friday = oru.third_friday(year, month)
        try:
            idx = self.calendar.get_loc(third_friday)
        except KeyError:
            # Third Friday is a holiday (most likely Good Friday) - Get the 1st day before that date
            idx = [idx for idx, date in enumerate(self.calendar) if date < pytz.UTC.localize(last_day)][-1]

        return self.calendar[idx + days].date()


class Events(enum.Enum):
    """Events Enum: Reference all exit events"""
    GoldmanRoll = (0, GoldmanRoll)
    LastDay = (1, LastDay)
    SpotLimit = (2, SpotLimit)


def get_date(event, calendar, ticker, last_day, days):
    """Get a date for a specific event (this is useful for testing purposes)

    :param event: enum Events - Which event to get the dates for
    :param calendar: object pmc - Calendar of business days
    :param ticker: str - Customized ticker
    :param last_day: date - Last trading day
    :param days: int - Number of days in reference to the last trading day
    :return: date - Date for the specific event
    """
    # If a string is passed as variable, convert it to an event
    if isinstance(event, str):
        event = Events[event]
    cle = event.value[1](calendar)
    return cle.date(ticker, last_day, days)


def get_dates(event, calendar, chain, days):
    """Get a list of all the dates for a specific event

    :param event: enum/str Events - Which event to get the dates for
    :param calendar: object pmc - Calendar of business days
    :param chain: object - Chain DataFrame
    :param days: int - Number of days in reference to the last trading day
    :return: list - Dates for the specific event for all the tickers in the chain
    """
    # If a string is passed as variable, convert it to an event
    if isinstance(event, str):
        event = Events[event]
    cle = event.value[1](calendar)
    return [cle.date(r['Ticker'], dt.datetime.strptime(r['LastDate'], '%Y-%m-%d'), days) for _, r in chain.iterrows()]
