#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ******************************************************
#         @author: Haifeng CHEN - optical.dlz@gmail.com
# @date (created): 2019-12-17 13:06
#           @file: ema.py
#          @brief: 
#       @internal: 
#        revision: 
#   last modified: 2019-12-17 13:06:07
# *****************************************************

import numpy as np


def exponential_moving_average(x, n, use_sma=False):
    """
    compute a n period exponetial moving average.
    NaN is not allowed in the input X
    """
    x = np.asarray(x)
    ema = np.zeros(x.shape)

    if use_sma:
        # get the first value, use SMA
        ema_prev = np.sum(x[:n])/n
        start = n
    else:
        # use the first value directly from x
        ema_prev = x[0]
        start = 1

    ema[0] = ema_prev
    alpha = 2.0 / (1 + n)

    for i in np.arange(start, len(x)):
        ema_prev = alpha * (x[i] - ema_prev) + ema_prev
        ema[i] = ema_prev

    if start == n:
        ema[:n] = ema[n]
    return ema

