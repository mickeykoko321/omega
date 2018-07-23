import logging
import os

import omega.configuration as c
import omega.core.instrument as oci

import omega.data.utils as odu


def amend_ctrmth(stem, amendments):
    """Amend the Contract Month table - This is a hard amend, as is, the old file will be overwritten with the changes.
    Must provide tuples of letters and status.

    :param stem: str - Customized Stem
    :param amendments: list - List of tuples (example: [('J', True)]
    """
    log = logging.getLogger(__name__)

    df = oci.ctrmth(stem, we_trade=False)
    # Amendments
    for a in amendments:
        df.loc[df['Letter'] == a[0], 'WeTrd'] = (-1 if a[1] else 0)
    log.debug('CtrMth table updated for: {} - Changes: {}'.format(stem, amendments))
    # Save new Contract Month table
    ric = oci.get_stem(stem, 'Reuters')
    file = os.path.join(c.cfg['default']['data'], 'CtrMth', '{}.csv'.format(ric))
    fields = ['CtrMth', 'WeTrd', 'LTD', 'FND', 'PosFstDt', 'PosLstDt']

    df[fields].to_csv(file, sep=',', index=False, header=True)
    
