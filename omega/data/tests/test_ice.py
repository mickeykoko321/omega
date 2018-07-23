import os
import pandas as pd
import pytest

import omega.configuration as oc
import omega.data.cot as odc
import omega.data.icecot as odi


data_dirs = [oc.cfg['default']['data'] + '/COT/FuturesOnly', oc.cfg['default']['data'] + '/COT/FuturesAndOptions']


def compare_list_comp(x, y):
    return [i for i, j in zip(x, y) if i == j]


@pytest.mark.parametrize('stem', ['GO', 'CO', 'SU', 'RC'])
def test_get_cot(stem):
    df = odc.get_cot(stem, 'F')
    assert isinstance(df, pd.DataFrame)
    df_sample = odc.get_cot('LC', 'F')
    assert(len(df.columns) == len(compare_list_comp(df.columns, df_sample.columns)))


def test_duplicates():
    odi.get_last_data()
    for directory in data_dirs:
        for file in os.listdir(directory):
            df = pd.read_csv(directory + '/' + file)
            assert df.duplicated().sum() == 0


@pytest.mark.parametrize('stem', ['GO', 'CO', 'SU', 'RC'])
def test_legacy_exception(stem):
    with pytest.raises(Exception) as e:
        _ = odc.get_cot(stem, 'F_L')
    assert(str(e.value) == 'Legacy data for COT {} is not supported'.format(stem))
