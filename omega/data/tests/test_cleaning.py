"""Test Cleaning module"""
import omega.core.instrument as oci
import omega.data.cleaning as odc


def test_inspect_files():
    inspect = odc.inspect_files(['LH'], oci.FutureType.Outright)
    assert isinstance(inspect, dict)
    print(inspect)


def test_check_has_data():
    check = odc.check_has_data(['LH'])
    assert isinstance(check, list)
    print(check)


def test_try_fix_missing():
    print(odc.try_fix_missing('LHS10M09'))
