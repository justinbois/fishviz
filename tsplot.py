import numpy as np
import pandas as pd

import bokeh.models
import bokeh.palettes
import bokeh.plotting



def dark(df, time, light):
    """
    Compute start and end time for dark bars on plots.

    Parameters
    ----------
    df : pandas DataFrame
        Tidy data frame containing a column with time points and
        a column with Boolean values, False being "dark" regions
        on plot.
    time : string or other acceptable pandas index
        Column containing time points.
    light : string or other acceptable pandas index
        Column containing Booleans for where the plot background
        is light.

    Returns
    -------
    lefts : ndarray
        Time points for left side of dark bars
    rights : ndarray
        Time points for right side of dark bars
    """
    zeit = df[time].reset_index(drop=True)
    lefts = zeit[np.where(np.diff(df[light].astype(int)) == -1)[0]].values
    rights = zeit[np.where(np.diff(df[light].astype(int)) == 1)[0]].values
    return lefts, rights


def time_series_plot(p, df, identifier, time, signal, time_ind=None,
                     colors=None, alpha=0.75, hover_color='#535353', title=None,
                     summary_trace='mean'):
    """
    Make a plot of multiple time series with a summary statistic.

    Parameters
    ----------
    p : bokeh.plotting.Figure instance
        Figure on which to make the plot, usually generated
        with the canvas() function.
    df : pandas DataFrame
        Tidy DataFrame minimally with columns:
        - identifier: ID of each time series
        - time: The time points; should be the same for each ID
        - signal: The y-axis of the time series
        - time_ind: (optional) Indices of time points for use in
                    computing summary statistics in case the time
                    points for all IDs are slightly off.
    identifier : string or any acceptable pandas index
        The name of the column in `df` containing the IDs
    time : string or any acceptable pandas index
        The name of the column in `df` containing the time points
    signal : string or any acceptable pandas index
        The name of the column in `df` containing the y-values
    time_ind : string or any acceptable pandas index
        The name of the column in `df` containing the time indices
        to be used in computing summary statistics. These values
        are used to do a groupby. Default is the column given by
        `time`.
    colors : list or tuple of length 2, default ['#a6cee3', '#1f78b4']
        colors[0]: hex value for color of all time series
        colors[1]: hex value for color of summary trace
    alpha : float, default 0.75
        alpha value for individual time traces
    hover_color : string, default '#535353'
        Hex value for color when hovering over a curve
    title : string or None, default None
        Title of plot.
    summary_trace : string, float, or None, default 'mean'
        Which summary statistic to use to make summary trace. If a
        string, can one of 'mean', 'median', 'max', or 'min'. If
        None, no summary trace is generated. If a float between
        0 and 1, denotes which quantile to show.

    Returns
    -------
    output : bokeh.plotting.Figure instance
        Bokeh plot populated with time series.
    """

    if colors is None:
        colors = bokeh.palettes.brewer['Paired'][3][:2]

    if time_ind is None:
        time_ind = time

    # Make the lines for display
    ml = []
    for individual in df[identifier].unique():
        sub_df = df.loc[df[identifier]==individual, [identifier, time, signal]]
        source = bokeh.models.ColumnDataSource(sub_df)
        ml.append(p.line(x=time, y=signal, source=source, line_width=0.5,
                  alpha=alpha, color=colors[0], name='do_not_hover',
                  line_join='bevel'))

    # Plot summary trace
    if summary_trace is not None:
        # Get the time axis
        t = df.loc[df[identifier]==df[identifier].unique()[0], time].values

        # Perform summary statistic calculation
        if summary_trace == 'mean':
            y = df.groupby(time_ind)[signal].mean().values
        elif summary_trace == 'median':
            y = df.groupby(time_ind)[signal].median().values
        elif summary_trace == 'max':
            y = df.groupby(time_ind)[signal].max().values
        elif summary_trace == 'min':
            y = df.groupby(time_ind)[signal].min().values
        elif type(summary_trace) == float:
            if summary_trace > 0 and summary_trace < 1:
                y = df.groupby(time_ind)[signal].quantile(summary_trace).values
            else:
                raise RuntimeError('Invalid summary_trace value.')
        else:
            raise RuntimeError('Invalid summary_trace value.')

        summary_line = p.line(t, y, line_width=3, color=colors[1],
                              line_join='bevel')

    # Make lines for hover
    for individual in df[identifier].unique():
        sub_df = df.loc[df[identifier]==individual, [identifier, time, signal]]
        source = bokeh.models.ColumnDataSource(sub_df)
        p.line(x=time, y=signal, source=source, line_width=2, alpha=0,
               name='hover', line_join='bevel', hover_color=hover_color)

    # Label title
    if title is not None:
        p.title.text = title

    return p


def canvas(df, identifier, height=350, width=650, x_axis_label='time',
           y_axis_label=None, light=None, time=None):
    """
    Make a Bokeh Figure instance for plotting time series.

    Parameters
    ----------
    df : pandas DataFrame
        Tidy DataFrame minimally with columns:
        - identifier: ID of each time series
    identifier : string or any acceptable pandas index
        The name of the column in `df` containing the IDs
    height : int, default 350
        Height of plot in pixels.
    width : int, default 650
        Width of plot in pixels.
    x_axis_label : string or None, default 'time'
        x-axis label.
    y_axis_label : string or None, default None
        y-axis label
    light : string or None or any acceptable pandas index, default None
        Column containing Booleans for where the plot background
        is light. If None, no shaded bars are present on the figure.
    time : string or None or any acceptable pandas index, default None
        The name of the column in `df` containing the time points.
        Ignored is `light` is None. Otherwise, `time` cannot be None.

    Returns
    -------
    output : bokeh.plotting.Figure instance
        Bokeh figure ready for plotting time series.
    """

    # Create figure
    p = bokeh.plotting.figure(width=width, height=height,
                              x_axis_label=x_axis_label,
                              y_axis_label=y_axis_label,
                              tools='pan,box_zoom,wheel_zoom,reset,resize,save')

    if light is not None:
        if time is None:
            raise RuntimeError('if `light` is not None, must supply `time`.')

        # Determine when nights start and end
        lefts, rights = dark(df[df[identifier]==df[identifier].unique().min()],
                             time, light)

        # Make shaded boxes
        dark_boxes = []
        for left, right in zip(lefts, rights):
            dark_boxes.append(
                    bokeh.models.BoxAnnotation(plot=p, left=left, right=right,
                                               fill_alpha=0.3, fill_color='gray'))
        p.renderers.extend(dark_boxes)

    # Add a HoverTool to highlight individuals
    p.add_tools(bokeh.models.HoverTool(
            tooltips=[(identifier, '@'+identifier)], names=['hover']))

    return p


def grid(df, identifier, category, time, signal, time_ind=None, alpha=0.75,
         hover_color='#535353', summary_trace='mean', height=200, width=650,
         x_axis_label='time', y_axis_label=None, light=None, colors=None,
         show_title=True):
    """
    Generate a set of plots of time series.

    Parameters
    ----------
    df : pandas DataFrame
        Tidy DataFrame minimally with columns:
        - identifier: ID of each time series
        - time: The time points; should be the same for each ID
        - signal: The y-axis of the time series
        - time_ind: (optional) Indices of time points for use in
                    computing summary statistics in case the time
                    points for all IDs are slightly off.
    identifier : string or any acceptable pandas index
        The name of the column in `df` containing the IDs
    category : string or any acceptable pandas index
        The name of the column in `df` that is used to group time
        series into respective subplots.
    time : string or any acceptable pandas index
        The name of the column in `df` containing the time points
    signal : string or any acceptable pandas index
        The name of the column in `df` containing the y-values
    time_ind : string or any acceptable pandas index
        The name of the column in `df` containing the time indices
        to be used in computing summary statistics. These values
        are used to do a groupby. Default is the column given by
        `time`.
    alpha : float, default 0.75
        alpha value for individual time traces
    hover_color : string, default '#535353'
        Hex value for color when hovering over a curve
    summary_trace : string, float, or None, default 'mean'
        Which summary statistic to use to make summary trace. If a
        string, can one of 'mean', 'median', 'max', or 'min'. If
        None, no summary trace is generated. If a float between
        0 and 1, denotes which quantile to show.
    height : int, default 350
        Height of plot in pixels.
    width : int, default 650
        Width of plot in pixels.
    x_axis_label : string or None, default 'time'
        x-axis label.
    y_axis_label : string or None, default None
        y-axis label
    light : string or None or any acceptable pandas index, default None
        Column containing Booleans for where the plot background
        is light. If None, no shaded bars are present on the figure.
    colors : dict, default None
        colors[cat] is a 2-list containg, for category `cat`:
            colors[cat][0]: hex value for color of all time series
            colors[cat][1]: hex value for color of summary trace
        If none, colors are generated using paired ColorBrewer colors,
        with a maximum of six categories.
    show_title : bool, default True
        If True, label subplots with with the category.

    Returns
    -------
    output : Bokleh grid plot
        Bokeh figure with subplots of all time series
    """
    # Get the categories
    cats = df[category].unique()

    # Make colors if not supplied
    if colors is None:
        colors = get_colors(cats)

    # Create figures
    ps = [canvas(df, identifier, height=height, width=width,
                 x_axis_label=x_axis_label, y_axis_label=y_axis_label,
                 light=light, time=time)
                        for i in range(len(cats))]

    # Link ranges (enable linked panning/zooming)
    for i in range(1, len(cats)):
        ps[i].x_range = ps[0].x_range
        ps[i].y_range = ps[0].y_range

    # Populate glyphs
    title = None
    for p, cat in zip(ps, cats):
        sub_df = df.loc[df[category]==cat, :]
        if show_title:
            title = cat
        _ = time_series_plot(p, sub_df, identifier, time, signal,
                             time_ind=time_ind, colors=colors[cat], alpha=alpha,
                             hover_color=hover_color, title=title,
                             summary_trace=summary_trace)

    return bokeh.layouts.gridplot([[ps[i]] for i in range(len(ps))])


def get_colors(cats):
    """
    Makes a color dictionary for plots.

    Parameters
    ----------
    cats : list or tuple, maximum length of 6
        Categories to be used as keys for the color dictionary

    Returns
    -------
    colors : dict, default None
        colors[cat] is a 2-list containg, for category `cat`:
            colors[cat][0]: hex value for color of all time series
            colors[cat][1]: hex value for color of summary trace
        Colors are generated using paired ColorBrewer colors,
        with a maximum of six categories.    
    """
    if len(cats) > 6:
        raise RuntimeError('Maxium of 6 categoriess allowed.')
    c = bokeh.palettes.brewer['Paired'][2*len(cats)]
    return {g: (c[2*i], c[2*i+1]) for i, g in enumerate(cats)}
