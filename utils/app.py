#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ******************************************************
#         @author: Haifeng CHEN - optical.dlz@gmail.com
# @date (created): 2019-06-27 11:31
#           @file: app.py
#          @brief: 
#       @internal: 
#        revision: 8
#   last modified: 2019-11-28 15:41:23
# *****************************************************


import os
import sys
import logging
import multiprocessing
from typing import Tuple, Union
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler


def open_file(filename):
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        import subprocess
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])


def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))


def get_application_path():
    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif sys.argv[0]:
        application_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    elif __file__:
        application_path = os.path.dirname(__file__)
    else:
        application_path = os.getcwd()

    return application_path


class WriteStream(object):
    """ The new Stream Object which replaces the default stream associated with sys.stdout
    This object just puts data in a queue!
    """

    def __init__(self, queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        return


def logger_init_for_worker(q: multiprocessing.Queue):
    """  Init logger in worker process
    :param q: multiprocess.Queue
    """
    # all records from worker processes go to qh and then into q
    qh = QueueHandler(q)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(qh)


def logger_init_main(filename=None, mp=False) -> \
        Tuple[Union[QueueListener, None], Union[multiprocessing.Queue, None]]:
    """ Init logger for current process
    :param filename: str or None
        File rotating handler will be used if filename is given. Otherwise stream handler is used
    :param mp: bool
        Set Ture if you want to handle logging information in worker process
    :return: Tuple
        QueueListner, multiprocessing.Queue
    """
    # this is the handler for all log records
    if filename is not None:
        handler = RotatingFileHandler(
            filename, encoding='utf-8', maxBytes=1 << 22, backupCount=10)
    else:
        handler = logging.StreamHandler()
    if multiprocessing:
        handler.setFormatter(
            logging.Formatter(
                fmt='%(asctime)s %(levelname)-8s: %(process)-6s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt='%(asctime)s %(levelname)-8s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # add the handler to the logger so records from this process are handled
    logger.addHandler(handler)

    if mp:
        q = multiprocessing.Queue()
        # ql gets records from the queue and sends them to the handler
        ql = QueueListener(q, handler)
        ql.start()
        return ql, q
    else:
        return None, None
