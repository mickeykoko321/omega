"""Test Contract module"""

import omega.core.contract as occ


def test_amend_ctrmth():
    occ.amend_ctrmth('CT', [('V', False)])
