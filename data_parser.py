import datetime

import numpy as np
import pandas as pd


def tidy_data(activity_name, genotype_name, out_name, lights_on, lights_off,
              day_in_the_life, resample_win=1, extra_cols=[],
              rename={'middur': 'activity'}):
    """Write a tidy data file"""
    df = load_data(activity_name, genotype_name, lights_on, lights_off,
                   day_in_the_life, extra_cols=extra_cols, rename=rename)
    df = resample(df, resample_win)
    df.to_csv(out_name, index=False)
    return None


def load_gtype(fname):
    """Read genotype file into tidy DataFrame"""
    # Read file
    df = pd.read_csv(fname, delimiter='\t', comment='#', header=[0, 1])

    # Reset the columns to be the second level of indexing
    df.columns = df.columns.get_level_values(1)

    # Only keep genotype up to last space because sometimes has n
    df.columns = [col[:col.rfind(' ')] if col.rfind(' ') > 0 else col
                  for col in df.columns]

    # Melt the DataFrame
    df = pd.melt(df, var_name='genotype', value_name='fish').dropna()

    # Reset the index
    df = df.reset_index(drop=True)

    # Make sure data type is integer
    df.loc[:,'fish'] = df.loc[:, 'fish'].astype(int)

    return df


def load_data(fname, genotype_fname, lights_on, lights_off, day_in_the_life,
              extra_cols=[], rename={'middur': 'activity'}):
    """Load in activity to DataFrame."""

    # Convert lightson and lightsoff to datetime.time objects
    if type(lights_on) != datetime.time:
        lights_on = pd.to_datetime(lights_on).time()
    if type(lights_off) != datetime.time:
        lights_off = pd.to_datetime(lights_off).time()

    # Get genotype information
    df_gt = load_gtype(genotype_fname)

    # Determine which columns to read in
    if extra_cols is None:
        extra_cols = []
    cols = ['location', 'stdate', 'sttime', 'middur']
    new_cols = list(set(extra_cols) - set(cols))
    usecols = cols + new_cols

    # Read file
    df = pd.read_csv(fname, usecols=usecols)

    # Convert location to well number (just drop 'c' in front)
    df = df.rename(columns={'location': 'fish'})
    df['fish'] = df['fish'].str.extract('(\d+)', expand=False).astype(int)

    # Only keep fish that we have genotypes for
    df = df.loc[df['fish'].isin(df_gt['fish']), :]

    # Store the genotypes
    fish_lookup = {fish: df_gt.loc[df_gt['fish']==fish, 'genotype'].values[0]
                          for fish in df_gt['fish']}
    df['genotype'] = df['fish'].apply(lambda x: fish_lookup[x])

    # Convert date and time to a time stamp
    df['time'] = pd.to_datetime(df['stdate'] + df['sttime'],
                                format='%d/%m/%Y%H:%M:%S')

    # Get earliest time point
    t_min = pd.DatetimeIndex(df['time']).min()

    # Get Zeitgeber time in units of hours
    df['zeit'] = (df['time'] - t_min).dt.total_seconds() / 3600

    # Determine light or dark
    clock = pd.DatetimeIndex(df['time']).time
    df['light'] = np.logical_and(clock >= lights_on, clock < lights_off)

    # Which day it is (remember, day goes lights on to lights on)
    df['day'] = pd.DatetimeIndex(
        df['time'] - datetime.datetime.combine(t_min.date(), lights_on)).day \
                + day_in_the_life - 1

    # Sort by fish and zeit
    df = df.sort_values(by=['fish', 'zeit']).reset_index(drop=True)

    # Set up zeit indices
    for fish in df['fish'].unique():
        df.loc[df['fish']==fish, 'zeit_ind'] = np.arange(
                                                    np.sum(df['fish']==fish))
    df['zeit_ind'] = df['zeit_ind'].astype(int)

    # Return everything if we don't want to delete anything
    if 'sttime' not in extra_cols:
        usecols.remove('sttime')
    if 'stdate' not in extra_cols:
        usecols.remove('stdate')
    usecols.remove('location')

    cols = usecols + ['time', 'fish', 'genotype', 'zeit', 'zeit_ind',
                      'light', 'day']
    df = df[cols]

    # Rename columns
    if rename is not None:
        df = df.rename(columns=rename)

    return df


def load_perl_processed_activity(activity_file, df_gt):
    """
    Load activity data into tidy DataFrame
    """
    df = pd.read_csv(activity_file, delimiter='\t', comment='#', header=[0, 1])

    # Make list of columns (use type conversion to allow list concatenation)
    df.columns = list(df.columns.get_level_values(1)[:2]) \
                                + list(df.columns.get_level_values(0)[2:])

    # Columns we want to drop
    cols_to_drop = df.columns[df.columns.str.contains('Unnamed')]
    df = df.drop(cols_to_drop, axis=1)

    # Start and end times are also dispensible
    df = df.drop(['start', 'end'], axis=1)

    # Find columns to drop (fish that do not have assigned genotypes)
    cols_to_drop = []
    for col in df.columns:
        if 'FISH' in col and int(col.lstrip('FISH')) not in df_gt['fish'].values:
                cols_to_drop.append(col)

    # Drop 'em!
    df = df.drop(cols_to_drop, axis=1)

    # Add a column for whether or not it is light
    df['light'] = pd.Series(df.CLOCK < 14.0, index=df.index)

    # Find where the lights switch from off to on.
    dark_to_light = np.where(np.diff(df['light'].astype(np.int)) == 1)[0]

    # Initialize array with day numbers
    day = np.zeros_like(df['light'], dtype=np.int)

    # Loop through transitions to set day numbers
    for i in range(len(dark_to_light) - 1):
        day[dark_to_light[i]+1:dark_to_light[i+1]+1] = i + 1
    day[dark_to_light[-1]+1:] = len(dark_to_light)

    # Insert the day numnber into DataFrame
    df['day'] = pd.Series(day, index=df.index)

    # Build ziet and put it in the DataFrame
    zeit = 24.0 * df['day'] + df['CLOCK']
    df['zeit'] = pd.Series(zeit, index=df.index)

    # Build list of genotypes
    genotypes = []

    # Check each column, put None for non-FISH column
    for col in df.columns:
        if 'FISH' in col:
            fish_id = int(col.lstrip('FISH'))
            genotypes.append(df_gt.genotype[df_gt.fish==fish_id].iloc[0])
        else:
            genotypes.append(None)

    df.columns = pd.MultiIndex.from_arrays((genotypes, df.columns),
                                        names=['genotype', 'variable'])

    # Value variables are the ones with FISH
    col_1 = df.columns.get_level_values(1)
    value_vars = list(df.columns[col_1.str.contains('FISH')])

    # ID vars are the non-FISH entries
    id_vars = list(df.columns[~col_1.str.contains('FISH')])

    # Perform the melt
    df = pd.melt(df, value_vars=value_vars, id_vars=id_vars,
                 value_name='activity', var_name=['genotype', 'fish'])

    # Rename any column that is a tuple
    for col in df.columns:
        if type(col) is tuple:
            df.rename(columns={col: col[1]}, inplace=True)

    # Make fish IDs integer
    df['fish'] = df['fish'].apply(lambda x: int(x.lstrip('FISH')))

    return df


def resample(df, ind_win):
    """
    Resample the DataFrame.
    """
    # Make a copy so as to leave original unperturbed
    df_in = df.copy()

    # Sort the DataFrame by fish and then zeit
    df_in = df_in.sort_values(by=['fish', 'zeit']).reset_index(drop=True)

    # If no resampling is necessary
    n_fish = len(df_in.fish.unique())
    if ind_win == 1:
        zeit_ind = list(range(np.sum(df_in.fish==df_in.fish.unique()[0]))) \
                            * n_fish
        df_in['zeit_ind'] = zeit_ind
        return df_in

    # Make GroupBy object
    df_gb = df_in.groupby('fish')['activity']

    # Compute rolling sum
    s = df_gb.rolling(window=ind_win).sum().reset_index(level=0, drop='fish')
    df_in['window'] = s

    # Index of right edge of 1st averaging win. (ensure win. ends at lights out)
    light = df_in.loc[df_in.fish==df_in.fish.unique()[0], 'light']
    start_ind = ind_win \
                + np.where(np.diff(light.values.astype(int)))[0][0] % ind_win

    # Inds to keep
    inds = np.array([])
    for fish in df_in.fish.unique():
        start = df_in.loc[df_in.fish==fish, :].index[0] + start_ind
        stop = df_in.loc[df_in.fish==fish, :].index[-1]
        inds = np.concatenate((inds, np.arange(start, stop, ind_win)))

    # Zeit indices
    zeit_ind = list(range(int(len(inds) // n_fish))) * n_fish

    # New DataFrame
    new_cols = ['fish', 'genotype', 'day', 'light', 'zeit', 'window']
    df_resampled = df_in.loc[inds, new_cols].reset_index(drop=True)
    df_resampled['zeit_ind'] = zeit_ind
    df_resampled = df_resampled.rename(columns={'window': 'activity'})

    return df_resampled
