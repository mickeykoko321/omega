import pytest

import omega.raid.backtrade as orb
import omega.raid.tests.test_strategy as ortt


def test_optimize():
    params = {'param1': range(10, 11), 'param2': {'FC': 4, 'LC': 5, 'LH': 6}}
    pnls, results = orb.optimize(['LC'], 1000000.0, ortt.TestTradeMulti, **params)

    print(pnls)
