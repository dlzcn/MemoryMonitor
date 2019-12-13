#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ******************************************************
#         @author: Haifeng CHEN - optical.dlz@gmail.com
# @date (created): 2019-12-12 09:07
#           @file: memory_monitor.py
#          @brief: A tool to monitor memory usage of given process
#       @internal: 
#        revision: 8
#   last modified: 2019-12-13 15:12:53
# *****************************************************

import os
import sys
import psutil
import random
import sqlite3
import logging
import datetime
import collections
import numpy as np
import matplotlib.pyplot as plt
from qtpy import QtCore, QtWidgets, QtGui
from utils.qapp import setHighDPI, setDarkStyle, loadQIcon
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)

__version__ = '1.1.0'
__revision__ = 8
__app_tittle__ = 'MemoryUsageMonitor'


class MemoryUsageMonitor(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QtCore.QSettings(QtCore.QSettings.NativeFormat,
                                         QtCore.QSettings.UserScope,
                                         'HF_AIO', 'MemoryUsageMonitor')
        self.pid = None
        self.ct = ''
        self.dq = collections.deque(maxlen=self.settings.value('dq_maxlen', 120, type=int))
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.onTimer)
        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        self.setMinimumSize(800, 600)
        self.setWindowTitle("{0} ({1}.{2})".format(
            __app_tittle__, __version__, __revision__))
        self.setWindowIcon(loadQIcon('icons/app_icon.png'))
        # The main widget
        widget = QtWidgets.QWidget()
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                            QtWidgets.QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(widget.sizePolicy().hasHeightForWidth())
        widget.setSizePolicy(size_policy)
        # create widgets ... # the first row
        ctrl_layout = self._createMainCtrls()
        # create matplotlib widgets and components
        canvas = self._setupMplWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(canvas)
        main_layout.addLayout(ctrl_layout)
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.statusBar().showMessage('Launched ...', 1000)

    def _setupMplWidget(self):
        canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self.mpl_ax = canvas.figure.subplots()
        canvas.figure.set_tight_layout(True)
        self.addToolBar(
            QtCore.Qt.TopToolBarArea,
            NavigationToolbar(self.mpl_ax.figure.canvas, self)
        )
        # the frame
        self.mpl_ax.spines['bottom'].set_color('w')
        self.mpl_ax.spines['top'].set_color('w')
        self.mpl_ax.spines['right'].set_color('w')
        self.mpl_ax.spines['left'].set_color('w')
        # white text, ticks
        self.mpl_ax.set_title('Memory Usage Monitor',
                              color='w', fontdict={'fontsize': 10})
        # self.mpl_ax.set_xlabel('Sampling points', color='w')
        self.mpl_ax.set_ylabel('Usage (MB)', color='w')
        self.mpl_ax.tick_params(axis='both', color='w')
        self.mpl_ax.tick_params(colors='w', labelsize=8)
        # dark background
        color = self.palette().color(QtGui.QPalette.Window).getRgbF()
        self.mpl_ax.figure.patch.set_facecolor(color)
        color = self.palette().color(QtGui.QPalette.Base).getRgbF()
        self.mpl_ax.set_facecolor(color)
        x = np.linspace(0, 10 * np.pi, 100)
        self.line_rss = self.mpl_ax.plot(x, np.sin(x), '-', label='Mem Usage')[0]
        self.line_vms = self.mpl_ax.plot(
            x, np.sin(random.random() * np.pi + x), '--', label='VM Size')[0]
        self.mpl_ax.legend()

        return canvas

    def _createMainCtrls(self):
        layout = QtWidgets.QHBoxLayout()

        label1 = QtWidgets.QLabel('Interval (second)')
        interval = QtWidgets.QLineEdit()
        interval.setValidator(QtGui.QIntValidator(0, 1000000000))
        interval.setObjectName('interval')
        interval.setAlignment(QtCore.Qt.AlignCenter)
        interval.setToolTip('Data sampling interval')
        interval.setText(self.settings.value('interval', '10', type=str))
        interval.textEdited[str].connect(self.updateSettings)
        layout.addWidget(label1)
        layout.addWidget(interval)

        label2 = QtWidgets.QLabel('Process name')
        p_name = QtWidgets.QLineEdit()
        p_name.setObjectName('process_name')
        p_name.setAlignment(QtCore.Qt.AlignCenter)
        p_name.setToolTip('Name of the process including the extension.'
                          ' It is case sensitive and duplicated name not well supported!')
        p_name.setText(self.settings.value('process_name', '', type=str))
        p_name.textEdited[str].connect(self.updateSettings)
        layout.addWidget(label2)
        layout.addWidget(p_name)

        label3 = QtWidgets.QLabel('Buffered data length*')
        dq_maxlen = QtWidgets.QLineEdit()
        dq_maxlen.setValidator(QtGui.QIntValidator(0, 9999))
        dq_maxlen.setObjectName('dq_maxlen')
        dq_maxlen.setAlignment(QtCore.Qt.AlignCenter)
        dq_maxlen.setToolTip('Maximal length of the buffered data points, press entry to apply the change on the fly!')
        dq_maxlen.setText(self.settings.value('dq_maxlen', '120', type=str))
        dq_maxlen.editingFinished.connect(self.onBufferSizedChanged)
        dq_maxlen.textEdited[str].connect(self.updateSettings)
        layout.addWidget(label3)
        layout.addWidget(dq_maxlen)

        self.start_btn = QtWidgets.QPushButton('Start')
        self.start_btn.clicked.connect(self.onStart)
        self.start_btn.setEnabled(True)
        self.stop_btn = QtWidgets.QPushButton('Stop')
        self.stop_btn.clicked.connect(self.onStop)
        self.stop_btn.setEnabled(False)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        return layout

    def setup_shortcuts(self):
        shortcut_t = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_T), self)
        shortcut_t.activated.connect(self.toggleWindowOnTop)
        shortcut_s = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_S), self)
        shortcut_s.activated.connect(self.toggleStartStop)

    def onBufferSizedChanged(self):
        try:
            val = self.settings.value('dq_maxlen', 120, type=int)
            self.dq = collections.deque(reversed(self.dq), maxlen=val)
            self.dq.reverse()
            msg = 'New buffer max length is {}, current size is {}'.format(val, len(self.dq))
            self.statusBar().showMessage(msg, 1000)
        except Exception as e:
            self.statusBar().showMessage(repr(e), 1000)

    def toggleWindowOnTop(self):
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowStaysOnTopHint)
        self.show()
        if self.windowFlags() & QtCore.Qt.WindowStaysOnTopHint:
            msg = 'Stays On Top: ON'
        else:
            msg = 'Stays On Top: OFF'
        self.statusBar().showMessage(msg, 1000)

    def toggleStartStop(self):
        if self.timer.isActive():
            self.onStop()
        else:
            self.onStart()

    def onStart(self):
        self.stop_btn.setEnabled(True)
        self.start_btn.setEnabled(False)
        interval = self.settings.value('interval', 10, type=int)
        p_name = self.settings.value('process_name', '', type=str)
        msg = 'Start monitor: [interval: {}, process name {}]'.format(interval, p_name)
        logging.debug(msg)
        self.statusBar().showMessage(msg, 1000)
        # start timer
        self.dq.clear()
        self.pid = None
        self.ct = ''
        self.timer.start(interval * 1000)

    def onStop(self):
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        msg = 'Stop monitor: [pid: {}, create time: {}]'.format(self.pid, self.ct)
        logging.debug(msg)
        self.statusBar().showMessage(msg, 1000)
        # stop timer
        self.timer.stop()

    def updateSettings(self, q_str):
        w = self.sender()
        if isinstance(w, QtWidgets.QCheckBox):
            if w.checkState() == QtCore.Qt.Checked:
                self.settings.setValue(w.objectName(), '1')
            else:
                self.settings.setValue(w.objectName(), '0')
        elif isinstance(w, QtWidgets.QLineEdit):
            self.settings.setValue(w.objectName(), w.text())
        elif isinstance(w, QtWidgets.QComboBox):
            self.settings.setValue(w.objectName(),
                                   '{}'.format(w.currentIndex()))

    def closeEvent(self, event):
        super().closeEvent(event)

    def _update_process_id(self, p_name):
        # try to check whether this id is still valid
        if self.pid is not None:
            try:
                p = psutil.Process(self.pid)
                if p.name() != p_name:
                    self.pid = None
                    self.ct = ''
            except Exception:
                msg = 'Process [{}]-[{}] is Dead'.format(self.pid, self.ct)
                logging.info(msg)
                self.statusBar().showMessage(msg, 1000)
                self.pid, self.ct = None, ''
                self.mpl_ax.set_title(
                    'Memory Usage Monitor ({} Not Found)'.format(p_name),
                    color='w', fontdict={'fontsize': 10})
                self.mpl_ax.figure.canvas.draw_idle()

        # try to get a new pid
        if self.pid is None:
            for proc in psutil.process_iter(attrs=['pid', 'name']):
                if proc.info['name'] == p_name:
                    self.pid = proc.info['pid']
                    self.ct = datetime.datetime.fromtimestamp(
                        proc.create_time()).strftime('%Y-%m-%d %H:%M:%S')
                    self.mpl_ax.set_title('Memory Usage Monitor ({} - {})'.format(p_name, self.ct),
                                          color='w', fontdict={'fontsize': 10})
                    msg = 'New process [{}]-[{}] found'.format(self.pid, self.ct)
                    logging.info(msg)
                    self.statusBar().showMessage(msg, 1000)
                    break

    def onTimer(self):
        p_name = self.settings.value('process_name', '', type=str)
        self._update_process_id(p_name)
        if self.pid is not None:
            process = psutil.Process(self.pid)
            memory_usage = process.memory_info()
            logging.info('[{}]-[{}]-[{}] - [{}, {}]'.format(
                self.pid, p_name, self.ct, memory_usage.rss, memory_usage.vms))
            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.dq.appendleft((ts, memory_usage.rss, memory_usage.vms))
            x = np.arange(0, len(self.dq))

            self.line_rss.set_xdata(x)
            rss = np.array([x[1] / 1024 / 1204 for x in self.dq])
            self.line_rss.set_ydata(rss)

            self.line_vms.set_xdata(x)
            vms = np.array([x[2] / 1024 / 1204 for x in self.dq])
            self.line_vms.set_ydata(vms)

            self.mpl_ax.set_ylim(0, max(np.max(vms), np.max(rss)) * 1.1)
            self.mpl_ax.set_xlim(
                0,
                min(max(len(x) * 1.2, self.dq.maxlen // 4), self.dq.maxlen)
            )

            ts = [x[0] for x in self.dq]
            labels = []
            for pos in self.mpl_ax.get_xticks():
                pos = int(pos)
                if pos < len(ts):
                    labels.append(ts[pos][5:])
                else:
                    labels.append('')
            self.mpl_ax.set_xticklabels(labels)

            self.mpl_ax.figure.canvas.draw()


if __name__ == "__main__":
    # enable logging
    logging.basicConfig(
        filename='memory_monitor.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    setHighDPI()
    # create Qt Application
    app = QtWidgets.QApplication(sys.argv)
    # set dark style
    setDarkStyle(app)
    # update default font for Windows 10
    if sys.platform == "win32":
        font = QtGui.QFont("Segoe UI", 9)
        app.setFont(font)
    # create the MainForm
    form = MemoryUsageMonitor()
    form.show()
    sys.exit(app.exec_())
