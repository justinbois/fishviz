import numpy as np
import pandas as pd

import bokeh.models
import bokeh.palettes
import bokeh.plotting



def dark(df, time, light):
    """
    
    Takes light series from a single fish and gives the start and end of nights.
    """
    zeit = df[time].reset_index(drop=True)
    lefts = zeit[np.where(np.diff(df[light].astype(int)) == -1)[0]].values
    rights = zeit[np.where(np.diff(df[light].astype(int)) == 1)[0]].values
    return lefts, rights


def time_series_plot(p, df, identifier, time, time_ind, signal, colors=None,
                     alpha=0.75, hover_color='#535353', title=None,
                     summary_trace='mean'):
    """
    Populate traces of fish activity.
    """

    if colors is None:
        colors = bokeh.palettes.brewer['Paired'][3][:2]

    # Make the lines for display
    ml = []
    for individual in df[identifier].unique():
        sub_df = df.loc[df[identifier]==individual, [identifier, time, signal]]
        source = bokeh.models.ColumnDataSource(sub_df)
        ml.append(p.line(x=time, y=signal, source=source, line_width=0.5,
                  alpha=alpha, color=colors[0], name='do_not_hover',
                  line_join='bevel'))

    # Plot summary trace
    if summary_trace is None:
        summary_line = None
    else:
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
    Set up night/day plot for fish.
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


def grid(df, identifier, category, time, time_ind, signal, alpha=0.75,
         hover_color='#535353', summary_trace='mean', height=200, width=650,
         x_axis_label='time', y_axis_label=None, light=None, colors=None,
         show_title=True):
    """
    Makes a grid of plots of fish.
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
        _ = time_series_plot(p, sub_df, identifier, time, time_ind, signal,
                             colors=colors[cat], alpha=alpha,
                             hover_color=hover_color, title=title,
                             summary_trace=summary_trace)

    return bokeh.layouts.gridplot([[ps[i]] for i in range(len(ps))])


def get_colors(cats):
    """
    Makes a color dictionary for the genotypes
    """
    if len(cats) > 6:
        raise RuntimeError('Maxium of 6 categoriess allowed.')
    c = bokeh.palettes.brewer['Paired'][2*len(cats)]
    return {g: (c[2*i], c[2*i+1]) for i, g in enumerate(cats)}
