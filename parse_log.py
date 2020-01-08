# ******************************************************
#         @author: Haifeng CHEN - optical.dlz@gmail.com
# @date (created): 2019-12-16 09:52
#           @file: parse_log.py
#          @brief: Parser memory monitor log
#       @internal: 
#        revision: 3
#   last modified: 2020-01-08 10:04:22
# *****************************************************

import re
import logging
import pandas as pd


def parse_memory_log(f, exe_name=None) -> pd.DataFrame:
    """ Parse memory monitor log """
    if exe_name is None:
        pattern = r'.* \[(.*)\]-\[(.*)\]-\[(.*)\] - \[(.*)\]'
    else:
        pattern = r'.* \[(.*)\]-\[{}]-\[(.*)\] - \[(.*)\]'.format(exe_name)

    compile_regex = re.compile(pattern, re.IGNORECASE)
    rst = []
    with open(f, 'r') as b:
        for line in b.readlines():
            # g = re.search(pattern, line)
            g = compile_regex.search(line)
            if g:
                groups = g.groups()
                if exe_name is None:
                    exe_name = groups[1]
                try:
                    full_name = '[{}] - started [{}]'.format(exe_name, groups[-2])
                    data = [full_name, ] + [int(x) for x in groups[-1].split(',')]
                    rst.append(tuple(data))
                except Exception as e:
                    logging.error(repr(e), exc_info=True)

    df = pd.DataFrame(rst, columns=['Process', 'rss', 'vms'])
    return df


if __name__ == '__main__':
    import argparse
    import numpy as np
    import matplotlib.pyplot as plt
    from utils.ema import exponential_moving_average
    # parse opt
    argtable = argparse.ArgumentParser(
        description='Memory Monitor log viewer')
    argtable.add_argument('-f', '--log', dest='log',
                          help='the memory monitor log',
                          default='')
    argtable.add_argument('--ignore', dest='ignore',
                          action='store_true',
                          help='Set to ignore data with points less than given count',
                          default=False)
    argtable.add_argument('--ignore_n', dest='ignore_n',
                          help='Minimal data point for analysis',
                          type=int, default=100)
    argtable.add_argument('--interval', dest='interval',
                          help='Sampling time interval in seconds',
                          type=int, default=10)
    argtable.add_argument('--ema', dest='ema',
                          action='store_true',
                          help='Set to use Exponential Moving Average to smooth data',
                          default=False)
    argtable.add_argument('--ema_n', dest='ema_n',
                          help='N of the EMA function',
                          type=int, default=10)

    opt = argtable.parse_args()

    d = parse_memory_log(opt.log)

    fig, ax = plt.subplots(figsize=(10, 4))
    for key, grp in d.groupby(['Process']):
        dat_len = len(grp['rss'])
        if opt.ignore and dat_len < opt.ignore_n:
            continue
        if opt.ema:
            ax.plot(
                np.arange(dat_len) * opt.interval / 60,
                exponential_moving_average(grp['rss'], opt.ema_n),
                label=key
            )
        else:
            ax.plot(
                np.arange(dat_len) * opt.interval / 60,
                grp['rss'],
                label=key
            )

    ax.legend()
    plt.show()
