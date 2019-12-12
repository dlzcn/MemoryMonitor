#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ******************************************************
#         @author: Haifeng CHEN - optical.dlz@gmail.com
# @date (created): 2019-10-22 21:27
#           @file: mpl.py
#          @brief: Matplotlib utilities
#       @internal: 
#        revision: 2
#   last modified: 2019-10-25 10:49:40
# *****************************************************

import sys
import matplotlib.pyplot as plt


def mpl_setup_cjk_font():
    """ update matplotlib sans-serif font list for CJK """
    import locale
    country_or_region, _ = locale.getdefaultlocale()
    if sys.platform == 'win32':
        if country_or_region == 'zh_CN':
            plt.rcParams['font.sans-serif'].insert(0, 'Microsoft YaHei')
        elif country_or_region == 'zh_TW':
            plt.rcParams['font.sans-serif'].insert(0, 'Microsoft JhengHei')
        elif country_or_region == 'jp_JP':
            plt.rcParams['font.sans-serif'].insert(0, 'Meiryo')
        elif country_or_region == 'ko_KR':
            plt.rcParams['font.sans-serif'].insert(0, 'Malgun Gothic')
        else:
            plt.rcParams['font.sans-serif'] = \
                ['Microsoft YaHei', 'Microsoft JhengHei', 'Meiryo', 'Malgun Gothic', 'Lucida Sans Unicode'] \
                + plt.rcParams['font.sans-serif']
    elif sys.platform == 'darwin':
        if country_or_region == 'zh_CN':
            plt.rcParams['font.sans-serif'].insert(0, 'PingFang SC')
        elif country_or_region == 'zh_TW':
            plt.rcParams['font.sans-serif'].insert(0, 'PingFang TC')
        elif country_or_region == 'jp_JP':
            plt.rcParams['font.sans-serif'].insert(0, 'Hiragino Sans')
        elif country_or_region == 'ko_KR':
            plt.rcParams['font.sans-serif'].insert(0, 'Apple SD Gothic Neo')
        else:
            plt.rcParams['font.sans-serif'] = \
                ['PingFang SC', 'PingFang TC', 'PingFang HK', 'Hiragino Sans', 'Apple SD Gothic Neo', 'Source Han Sans',
                 'Noto Sans CJK'] \
                + plt.rcParams['font.sans-serif']
    else:
        if country_or_region == 'zh_CN':
            plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Noto Sans CJK'] + plt.rcParams['font.sans-serif']
        elif country_or_region == 'zh_TW':
            plt.rcParams['font.sans-serif'] = ['Source Han Sans TW', 'Noto Sans CJK'] + plt.rcParams['font.sans-serif']
        elif country_or_region == 'jp_JP':
            plt.rcParams['font.sans-serif'] = ['Source Han Sans JP', 'Noto Sans CJK'] + plt.rcParams['font.sans-serif']
            # plt.rcParams['font.sans-serif'] = ['TakaoGothic', 'TakaoPGothic', 'Droid Sans Japanese'] +
            # plt.rcParams['font.sans-serif']
        elif country_or_region == 'ko_KR':
            plt.rcParams['font.sans-serif'] = ['Source Han Sans KR', 'Noto Sans CJK'] + plt.rcParams['font.sans-serif']
        else:
            plt.rcParams['font.sans-serif'] = ['Droid Sans Fallback', 'Source Han Sans', 'Noto Sans CJK'] + \
                                              plt.rcParams['font.sans-serif']

    plt.rcParams['axes.unicode_minus'] = False
