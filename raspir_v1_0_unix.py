#!/usr/bin/env python
# coding: utf-8

# raspir
# Author: Marie-Madlen Pust
# pust.marie-madlen@mh-hannover.de
# Last updated:


# Import python modules
import os
import pandas as pd
import numpy as np
import itertools
from itertools import count, takewhile
import matplotlib
import matplotlib.pyplot as plt
from scipy import fftpack, stats
from scipy.stats import linregress
import random

matplotlib.use('Agg')


# Set parameters
set_error = 0.01
set_alpha = 0.05


# Define range of the reference's read distance
def frange(start, stop, step):
    return takewhile(lambda x: x < stop, count(start, step))


def read_count(x):
    items_diff = [abs(j - i) for i, j in zip(x['Position'], x['Position'][1:])]
    a = [0]
    items_diff = a + items_diff
    x['items_diff'] = items_diff
    x['gap'] = np.where(x['items_diff'] == 1, 0, 1)
    x['readCount'] = np.cumsum(x['gap'])
    x = x.drop_duplicates(subset='readCount', keep='first')
    x = x.drop(['items_diff', 'gap'], 1)
    
    # remove all Organisms with less than 4 reads
    x['indexNames'] = x['readCount'].sum()
    store_index = x[x['indexNames'] < int(4)].index
    x.drop(store_index, inplace=True)
    return x


# Normalise position (circular genome)
def normalise_genome_position(x):
    x['PositionNorm0'] = np.where(x['Position'] > (x['GenomeLength'] / 2),
                                  (x['GenomeLength'] - x['Position']), x['Position'])
    x['PositionNorm'] = x['PositionNorm0']**(1/2)
    
    # Reference position
    n_reads = x['readCount'].max()
    start_position_ref = int(1)
    end_position_ref = x['GenomeLength'].iloc[0]
    end_position_ref = end_position_ref + n_reads
    increase_by = (end_position_ref / n_reads)
    x['ref_Position'] = list(frange(start_position_ref, end_position_ref, increase_by))
    x['ref_Position'] = x['ref_Position'].astype(int)
    x['PositionNorm_ref0'] = np.where(
        x['ref_Position'] > (x['GenomeLength'] / 2), (x['GenomeLength'] - x['ref_Position']), x['ref_Position'])
    x['PositionNorm_ref'] = x['PositionNorm_ref0'].astype(int)
    return x


# Time domain signal
def make_time_domain(x):
    # check if read count of organism matches with minimum requirement
    mean_depth = int(x['Depth'].mean())
    n_reads = int(x['readCount'].max())
    species_name = x['Organism'].iloc[0]
    x['PositionNorm'] = x['PositionNorm'] * x['Depth']
    x['PositionNorm_ref'] = x['PositionNorm_ref'] * mean_depth

    reference_combinations_distances_sort = []
    real_combinations_distances_sort = []

    # calculate the biological distance
    real_read_positions = sorted(x['PositionNorm'])
    reference_read_positions = sorted(x['PositionNorm_ref'])

    if n_reads > int(1000):
        random.seed(222)
        real_select_random = random.sample(real_read_positions, 400)
        real_read_combinations_sub = list(itertools.combinations(real_select_random, 2))
        real_combinations_distances_sub = [abs(i - j) for i, j in real_read_combinations_sub]
        real_combinations_distances_sort_sub = sorted(real_combinations_distances_sub)
        real_combinations_distances_sort.append(real_combinations_distances_sort_sub)

        # calculate the reference distance
        reference_select_random = random.sample(reference_read_positions, 400)
        reference_read_combinations_sub = list(itertools.combinations(reference_select_random, 2))
        reference_combinations_distances_sub = [abs(i - j) for i, j in reference_read_combinations_sub]
        reference_combinations_distances_sort_sub = sorted(reference_combinations_distances_sub)
        reference_combinations_distances_sort.append(reference_combinations_distances_sort_sub)
    else:
        real_read_combinations = list(itertools.combinations(real_read_positions, 2))
        real_combinations_distances = [abs(i - j) for i, j in real_read_combinations]
        real_combinations_distances_sort1 = sorted(real_combinations_distances)
        real_combinations_distances_sort.append(real_combinations_distances_sort1)

        # calculate the reference distance
        reference_read_combinations = list(itertools.combinations(reference_read_positions, 2))
        reference_combinations_distances = [abs(i - j) for i, j in reference_read_combinations]
        reference_combinations_distances_sort1 = sorted(reference_combinations_distances)
        reference_combinations_distances_sort.append(reference_combinations_distances_sort1)

    # create output data frame
    df = pd.DataFrame(list(zip(reference_combinations_distances_sort, real_combinations_distances_sort)),
                      columns=['Reference', 'Real'])
    df['Organism'] = species_name
    df2 = df.apply(lambda i: i.explode() if i.name in ['Reference', 'Real'] else i)
    return df2


# frequency domain signal (fds)
def fourier_trans(x):
    species_name = x['Organism'].iloc[0]
    sep = '_'
    stripped_name = species_name.split(sep)
    stripped_name2 = stripped_name[3] + ' ' + stripped_name[4]

    x['fft_ref1'] = np.fft.fft(x['Reference'])
    x['fft_bio1'] = np.fft.fft(x['Real'])

    x['fft_ref'] = [complex(np.around(items2.real), np.around(items2.imag)) for items2 in x['fft_ref1']]
    x['fft_bio'] = [complex(np.around(items2.real), np.around(items2.imag)) for items2 in x['fft_bio1']]
    
    x['fft_abs_ref'] = np.abs(x['fft_ref'])
    x['fft_abs_bio'] = np.abs(x['fft_bio'])
    x['fft_abs_ref_sqrt'] = np.around(x['fft_abs_ref'] / 1000000, 2)
    x['fft_abs_bio_sqrt'] = np.around(x['fft_abs_bio'] / 1000000, 2)

    # Pearson correlation
    if (sum(x['fft_abs_ref_sqrt']) > 0) & (sum(x['fft_abs_bio_sqrt']) > 0):
        pearson_corr = linregress(x['fft_abs_ref_sqrt'], x['fft_abs_bio_sqrt'])
        pearson_standard_error0 = pearson_corr[4]
        pearson_corr_r0, pearson_corr_p0 = stats.pearsonr(x['fft_abs_ref_sqrt'], x['fft_abs_bio_sqrt'])
        pearson_corr_r = round(pearson_corr_r0, 4)
        pearson_corr_p = round(pearson_corr_p0, 10)
        euclidean_dist_0 = np.linalg.norm(x['fft_abs_ref_sqrt']-x['fft_abs_bio_sqrt'])
        euclidean_dist = round(euclidean_dist_0, 1)
        pearson_standard_error = round(pearson_standard_error0, 5)
        return stripped_name2, pearson_corr_r, pearson_corr_p, pearson_standard_error, euclidean_dist


def make_freq_images(x):
    species_name = x['Organism'].iloc[0]
    path_real = x['PathName'].iloc[0]

    x['fft_ref1'] = np.fft.fft(x['Reference'])
    x['fft_bio1'] = np.fft.fft(x['Real'])

    x['fft_ref'] = [complex(np.around(items2.real), np.around(items2.imag)) for items2 in x['fft_ref1']]
    x['fft_bio'] = [complex(np.around(items2.real), np.around(items2.imag)) for items2 in x['fft_bio1']]

    x['fft_abs_ref'] = np.abs(x['fft_ref'])
    x['fft_abs_bio'] = np.abs(x['fft_bio'])
    x['fft_abs_ref_sqrt'] = np.around(x['fft_abs_ref'] / 1000000, 2)
    x['fft_abs_bio_sqrt'] = np.around(x['fft_abs_bio'] / 1000000, 2)

    # plot frequency signal
    yvals1 = x['Real']
    yvals2 = x['Reference']
    x_bio = x['fft_abs_bio_sqrt']
    x_reference = x['fft_abs_ref_sqrt']

    freqs_ref = fftpack.fftfreq(len(yvals2))
    freqs_bio = fftpack.fftfreq(len(yvals1))

    sep = '_'
    stripped_name = species_name.split(sep)
    stripped_name2 = stripped_name[3] + ' ' + stripped_name[4]

    fig, ax1 = plt.subplots(1, 1, figsize=(2.5, 2))
    fig.suptitle(stripped_name2, style='italic', fontsize=4)
    ax1.plot(freqs_ref, x_reference, "black", linewidth=0.6, linestyle="-", label="Reference")
    ax1.plot(freqs_bio, x_bio, 'green', linewidth=0.6, linestyle="-", label="Sample")
    ax1.legend(framealpha=1, loc='upper right', fontsize=4)
    ax1.fill_between(freqs_ref, x_reference, x_bio, facecolor='#FF0000', alpha=0.5, interpolate=True)
    fig.text(0.5, 0.025, "Frequency per cycle", ha='center', va='center', fontsize=4)
    fig.text(0.010, 0.5, "Spectrum", ha='center', va='center', rotation='vertical', fontsize=4)
    plt.xlim(-0.2, 0.2)
    plt.xticks(fontsize=3)
    plt.yticks(fontsize=3)
    plt.savefig(path_real + '/' + species_name + '_freq.png', dpi=600)
    plt.close()


def final_table(x):
    a0 = pd.DataFrame(x, columns=['Pearson'])
    a = a0.dropna(axis=0, how='all')
    a = a[['Species', 'r_value', 'p_value', 'stError', 'euclideanR0']] = pd.DataFrame(a['Pearson'].tolist())
    a.columns = ['a', 'b', 'c', 'd', 'e',
                 'Species', 'r_value', 'p_value', 'stError', 'euclideanR0']
    a.reset_index(drop=True, inplace=True)
    a = a.drop(a.columns[[0, 1]], axis=1)
    a = a[['Species', 'r_value', 'p_value', 'stError', 'euclideanR0']]
    a['euclidean'] = np.around((1 / a['euclideanR0']) * 1000, 3)
    a['distribution'] = np.where(
        (a['p_value'] < set_alpha) & (a['r_value'] > 0.5) & (a['stError'] < set_error) & (a['euclidean'] < 0.6),
        'uniform', 'nonuniform')
    b1 = a[['Species', 'r_value', 'p_value', 'stError', 'euclidean', 'distribution']]
    b2 = b1[b1.distribution == 'uniform']
    return b2


def main():
    path_name = os.getcwd()
    file_names = os.listdir(path_name)

    for all_names in file_names:
        files_to_process = []
        if all_names.endswith(".raspir.csv"):
            files_to_process.append(all_names)

            for items in files_to_process:
                file_name = str(items)
                print(file_name)

                # make directory
                new_directory_name_real = file_name[:-4]
                current_directory = os.getcwd()
                path_real = os.path.join(current_directory, new_directory_name_real)
                os.mkdir(path_real)
                store_path = path_real
                print("Directory '% s' was created" % new_directory_name_real)

                with open(items, newline='') as dataset:
                    df = pd.read_csv(dataset, delimiter=',')
                    pattern_del = "1_1_1_"
                    filter_approach = df['Organism'].str.contains(pattern_del, na=False)
                    df = df[~filter_approach]
                    print("1 Human reads have been removed.")

                    df = df.dropna(subset=['GenomeLength'])
                    df_filter1 = df.groupby('Organism').apply(read_count)
                    print("2 Continues with the first position of each read.")
                    
                    if df_filter1.empty is True:
                        df_filter1.to_csv('output' + file_name, index=False)
                        print("Note: Dataset is empty")
                        continue
                    else:
                        df_filter = df_filter1.reset_index(drop=True)
                        df_filter2 = df_filter.groupby('Organism').apply(normalise_genome_position)
                        print("3 Genome position has been normalised.")

                        position_domain0 = df_filter2.reset_index(drop=True)
                        position_domain = position_domain0.groupby("Organism").apply(make_time_domain)
                        print("4 Time-domain signal was built.")

                        frequency_domain0 = position_domain.reset_index(drop=True)
                        frequency_domain0['PathName'] = store_path
                        frequency_domain = frequency_domain0.groupby('Organism').apply(fourier_trans)
                        print("5 Frequency-domain signal was generated.")

                        frequency_domain0.groupby('Organism').apply(make_freq_images)
                        print("6 Frequency plots have been produced.")

                        stat_table = final_table(frequency_domain)
                        print("7 Output table has been generated.")
                        
                        stat_table.to_csv(path_real + '/' + 'final_stats.' + file_name, index=False)
                        print('8 Run was successful.')


if __name__ == "__main__":
    main()
