import setuptools as st

st.setup(
    name='omega',
    version='0.0.2',
    packages=['omega', 'omega.cabbage', 'omega.core', 'omega.data', 'omega.logger', 'omega.raid', 'omega.xl'],
    url='',
    license='',
    author='Laurent',
    author_email='',
    description='',
    requires=[
        'backtrader', 'eikon', 'empyrical', 'pandas',
        'python-highcharts', 'quandl', 'pandas_market_calendars', 'plotly'
    ]
)
