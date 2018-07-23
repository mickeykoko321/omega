"""Test Filter Logs module"""
import os

import omega.configuration as oc
import omega.logger.filter_logs as olf


def test_by_strings():
    filename = '2018-05-29-live.txt'
    orders = olf.by_strings(os.path.join(oc.cfg['logging']['root'], filename), ['INFO', '2018-05-09', 'Order'])
    print(orders)
