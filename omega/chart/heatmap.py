import logging
import math
import pandas as pd
import plotly.exceptions as ple
import plotly.figure_factory as pff
import plotly.offline as plo

import omega.core.instrument as oci


def per_contract(future_chain, field='Volume'):
    """Plot heatmap of the average Volume or Open Interest of the last 90 days. Display it by year for each contract.
    This should be useful to find out which contract are traded/not traded and where

    :param future_chain: object - Future Chain initialized with data
    :param field: str - Volume or OI
    :return: object - Plot Plotly chart
    """
    log = logging.getLogger(__name__)

    if field != 'Volume' and field != 'OI':
        raise Exception('Field provided must be str Volume or OI!')

    stem = future_chain.stem
    df = future_chain.chain
    data = future_chain.data
    # Average Volume
    df['Month'] = df.apply(lambda x: x['Ticker'][2:3], axis=1)
    df['Year'] = df.apply(lambda x: 2000 + int(x['Ticker'][-2:]), axis=1)
    # Add average volume of last 90 days
    df['AvgVol'] = 0
    for idx, row in df.iterrows():
        mdf = data[row['Ticker']]
        df.loc[idx, 'AvgVol'] = int(mdf[-90:][field].mean())
    # Transformation to HeatMap DF
    years = []
    for year in df['Year'].unique():
        ydf = df[df['Year'] == year][['Month', 'AvgVol']]
        ydf.set_index('Month', drop=True, inplace=True)
        ydf.index.names = [None]
        ydf.columns = [year]
        years.append(ydf)
    hdf = pd.concat(years, axis=1)
    # Index
    cdf = oci.ctrmth(stem, we_trade=False)
    cdf['Letter'] = cdf.apply(lambda x: oci.ym_maturity(x['CtrMth'])[0], axis=1)
    lw = cdf.groupby('Letter').mean()
    lw['Index'] = lw.apply(lambda x: '{} (T: {})'.format(x.name, x['WeTrd']), axis=1)
    rlw = lw.reindex(index=lw.index[::-1])
    # Plot
    rhdf = hdf.reindex(index=hdf.index[::-1])
    values = rhdf.values
    values = [[int(vi) if not math.isnan(vi) else float('NaN') for vi in v] for v in values]
    try:
        fig = pff.create_annotated_heatmap(values, x=list(rhdf.columns), y=list(rlw['Index']),
                                           colorscale='Jet', font_colors=['white'], hoverinfo='z')
        for i in range(len(fig.layout.annotations)):  # Make text size smaller
            fig.layout.annotations[i].font.size = 10
        fig.layout.title = '{} - {}'.format(stem, field)

        plo.iplot(fig)
    except ple.PlotlyError:
        log.error('Most likely a problem with axis length: x: {} - y: {} - z: {}'.format(list(rhdf.columns), list(rlw['Index']), len(values)))
