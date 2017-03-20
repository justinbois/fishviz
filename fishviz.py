import argparse

import bokeh.io
import bokeh.models
import bokeh.palettes
import bokeh.plotting


def nights(df):
    """
    Takes light series from a single fish and gives the start and end of nights.
    """
    zeit = df.zeit.reset_index(drop=True)
    lefts = zeit[np.where(np.diff(df.light.astype(int)) == -1)[0]].values
    rights = zeit[np.where(np.diff(df.light.astype(int)) == 1)[0]].values
    return lefts, rights


def fish_plot(p, df, genotype, colors):
    """
    Populate traces of fish activity.
    """

    # Pull out genotype of interest
    df_p = df.loc[df.genotype==genotype, ['fish', 'zeit', 'zeit_ind', 'activity']]

    # Get the time axis
    zeit = df_p.loc[df_p.fish==df_p.fish.unique()[0], 'zeit'].values

    # Make the lines
    ml = []
    for fish in df_p.fish.unique():
        source = bokeh.models.ColumnDataSource(df_p.loc[df_p.fish==fish, :])
        ml.append(p.line(x='zeit', y='activity', source=source, line_width=0.5,
                  alpha=0.75, color=colors[genotype][0], line_join='bevel',
                  hover_color='#5c04f4'))

    # Plot average trace
    mean_line = p.line(zeit, df_p.groupby('zeit_ind').mean()['activity'].values,
                       line_width=3, color=colors[genotype][1],
                       line_join='bevel')

    # Label title
    p.title.text = genotype

    return p, ml, mean_line


def fish_canvas(df, height=350, width=650,
                y_axis_label='sec. of activity in time win.'):
    """
    Set up night/day plot for fish.
    """
    # Create figure
    p = bokeh.plotting.figure(width=width, height=height,
                              x_axis_label='time (hours)',
                              y_axis_label=y_axis_label,
                              tools='pan,box_zoom,wheel_zoom,reset,resize,save')

    # Determine when nights start and end
    lefts, rights = nights(df[df.fish==1])

    # Make shaded boxes for nights
    night_boxes = []
    for left, right in zip(lefts, rights):
        night_boxes.append(
                bokeh.models.BoxAnnotation(plot=p, left=left, right=right,
                                           fill_alpha=0.3, fill_color='gray'))
    p.renderers.extend(night_boxes)

    # Add a HoverTool to highlight individual fish
    p.add_tools(bokeh.models.HoverTool(tooltips=[('fish', '@fish')]))

    return p


def fish_grid(df, y_axis_label='sec. of activity in time win.'):
    """
    Makes a grid of plots of fish.
    """
    gtypes = df.genotype.unique()

    # Determine when nights start and end
    lefts, rights = nights(df[df.fish==df.fish.unique().min()])

    # Create figures
    ps = [fish_canvas(df, height=200, y_axis_label=y_axis_label)
                for i in range(len(gtypes))]

    # Link ranges (enable linked panning/zooming)
    for i in range(1, len(gtypes)):
        ps[i].x_range = ps[0].x_range
        ps[i].y_range = ps[0].y_range

    # Populate glyphs
    for p, genotype in zip(ps, gtypes):
        _ = fish_plot(p, df, genotype, colors)

    return bokeh.layouts.gridplot([[ps[i]] for i in range(len(ps))])


def get_colors(gtypes):
    """
    Makes a color dictionary for the genotypes
    """
    if len(gtypes) > 6:
        raise RuntimeError('Maxium of 6 genotypes allowed.')
    c = bokeh.palettes.brewer['Paired'][2*len(gtypes)]
    return {g: (c[2*i], c[2*i+1]) for i, g in enumerate(gtypes)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', '-w', action='store', dest='ind_win',
                        default=10,
                help='Number of time points to use in averages (default 10)')
    parser.add_argument('--lightson', '-l', action='store', dest='lights_on',
                        default='9:00:00',
                help='time that lights come on, e.g., 9:00:00')
    parser.add_argument('--lightsoff', '-d', action='store', dest='lights_off',
                        default='23:00:00',
                help='time that lights go off, e.g., 23:00:00')
    parser.add_argument('--startday', '-D', action='store',
                        dest='day_in_the_life', default=5,
                help="Day in zebrafish's life that experiment began" )
    parser.add_argument('--gtype', '-g', action='store', dest='gtype_file',
                        help='name of file containing genotypes')
    parser.add_argument('--activity', '-a', action='store',
                        dest='activity_file',
                        help='name of file containing activity data')
    parser.add_argument('--out', '-o', action='store',
                        dest='html_file',
                        help='name of file to store output')
    parser.add_argument('--tidy', '-t', action='store_true', dest='tidy',
                        default=False)
    parser.add_argument('--perl_processed', '-p', action='store_true',
                        dest='perl_processed', default=False)
    args = parser.parse_args()

    # Specify output
    bokeh.io.output_file(args.html_file, title='fish sleep explorer')

    # Parse data Frames
    if args.tidy:
        df = load_tidy_activity(args.activity_file)
    elif args.perl_processed:
        df_gt = load_gtype(args.gtype_file)
        df = load_perl_processed_activity(args.activity_file, df_gt)
    else:
        lights_on = pd.to_datetime(args.lights_on).time()
        lights_off = pd.to_datetime(args.lights_off).time()
        df = load_data(args.activity_file, args.gtype_file, lights_on,
                       lights_off, int(args.day_in_the_life))

    # Resample the data
    df_resampled = resample(df, int(args.ind_win))

    # Get approximate time interval of averages
    inds = df_resampled.fish==df_resampled.fish.unique()[0]
    zeit = np.sort(df_resampled.loc[inds, 'zeit'].values)
    dt = np.mean(np.diff(zeit)) * 60

    # Make y-axis label
    y_axis_label = 'sec. of act. in {0:.1f} min.'.format(dt)

    # Choose color scheme
    colors = get_colors(df_resampled.genotype.unique())

    # Make plots
    p = fish_grid(df_resampled, y_axis_label=y_axis_label)

    # Save HTML file
    bokeh.io.save(p)
