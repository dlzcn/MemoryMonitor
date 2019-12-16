# ******************************************************
#         @author: Haifeng CHEN - optical.dlz@gmail.com
# @date (created): 2019-12-16 09:52
#           @file: parse_log.py
#          @brief: Parser memory monitor log
#       @internal: 
#        revision: 1
#   last modified: 2019-12-16 09:52:11
# *****************************************************

import re
import sys
import pandas as pd


def parse_memory_log(f, exe_name=None) -> pd.DataFrame:
    """ Parse memory monitor log """
    if exe_name is None:
        pattern = r'.* \[(.*)\]-\[(.*)\]-\[(.*)\] - \[(.*)\]'
    else:
        pattern = r'.* \[(.*)\]-\[{}]-\[(.*)\] - \[(.*)\]'.format(exe_name)

    rst = []
    with open(f, 'r') as b:
        for line in b.readlines():
            g = re.search(pattern, line)
            if g:
                groups = g.groups()
                if exe_name is None:
                    exe_name = groups[1]
                try:
                    full_name = '[{}] - started [{}]'.format(exe_name, groups[-2])
                    data = [full_name, ] + [int(x) for x in groups[-1].split(',')]
                    rst.append(tuple(data))
                except Exception as e:
                    print(repr(e))

    df = pd.DataFrame(rst, columns=['Process', 'rss', 'vms'])
    return df


if __name__ == '__main__':
    import numpy as np
    import matplotlib.pyplot as plt
    d = parse_memory_log(sys.argv[1])
    if len(sys.argv) > 2:
        num = int(sys.argv[2])
    else:
        num = 10

    fig, ax = plt.subplots(figsize=(10, 4))
    for key, grp in d.groupby(['Process']):
        ax.plot(np.arange(len(grp['rss']) * num / 60), grp['rss'], label=key)

    ax.legend()
    plt.show()