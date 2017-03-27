import argparse

import numpy as np
import pandas as pd

import bokeh.io

import data_parser
import tsplot


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', '-w', action='store', dest='ind_win',
                        default=10,
                help='Number of time points to use in averages (default 10)')
    parser.add_argument('--lightson', '-l', action='store', dest='lights_on',
                        default='9:00:00',
                help='time that lights come on, e.g., 9:00:00 (default)')
    parser.add_argument('--lightsoff', '-d', action='store', dest='lights_off',
                        default='23:00:00',
                help='time that lights go off, e.g., 23:00:00 (default)')
    parser.add_argument('--startday', '-D', action='store',
                        dest='day_in_the_life', default=5,
            help="Day in zebrafish's life that experiment began (default 5)" )
    parser.add_argument('--gtype', '-g', action='store', dest='gtype_file',
        help="name of file containing genotypes (req'd unles --tidy selected)")
    parser.add_argument('--activity', '-a', action='store',
                        dest='activity_file', required=True,
                        help='name of file containing activity data')
    parser.add_argument('--out', '-o', action='store',
                        dest='html_file', required=True,
                        help='name of file to store output')
    parser.add_argument('--tidy', '-t', action='store_true', dest='tidy',
                        default=False,
                        help='If data set is already tidied.')
    parser.add_argument('--perl_processed', '-p', action='store_true',
                        dest='perl_processed', default=False,
            help='If data set already pre-processed by Prober lab Perl script.')
    args = parser.parse_args()


    # Specify output
    bokeh.io.output_file(args.html_file, title='fish sleep explorer')

    # Parse data Frames
    if args.tidy:
        df = pd.read_csv(args.activity_file)
    elif args.perl_processed:
        df_gt = data_parser.load_gtype(args.gtype_file)
        df = data_parser.load_perl_processed_activity(args.activity_file, df_gt)
    else:
        lights_on = pd.to_datetime(args.lights_on).time()
        lights_off = pd.to_datetime(args.lights_off).time()
        df = data_parser.load_data(
                 args.activity_file, args.gtype_file, lights_on,
                 lights_off, int(args.day_in_the_life))

    # Resample the data
    df_resampled = data_parser.resample(df, int(args.ind_win))

    # Get approximate time interval of averages
    inds = df_resampled.fish==df_resampled.fish.unique()[0]
    zeit = np.sort(df_resampled.loc[inds, 'zeit'].values)
    dt = np.mean(np.diff(zeit)) * 60

    # Make y-axis label
    y_axis_label = 'sec. of act. in {0:.1f} min.'.format(dt)

    # Make plots
    p = tsplot.grid(df_resampled, 'fish', 'genotype', 'zeit', 'zeit_ind',
                    'activity', light='light', x_axis_label='time (hr)',
                    y_axis_label=y_axis_label)

    # Save HTML file
    bokeh.io.save(p)
