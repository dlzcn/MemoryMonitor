#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ******************************************************
#         @author: Haifeng CHEN - optical.dlz@gmail.com
# @date (created): 2019-12-12 09:07
#           @file: memory_monitor.py
#          @brief: A tool to monitor memory usage of given process
#       @internal: 
#        revision: 14
#   last modified: 2020-03-06 12:24:48
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
import pandas as pd
from typing import Union, Tuple
from qtpy import QtCore, QtWidgets, QtGui
from utils.qapp import setHighDPI, setDarkStyle, loadQIcon
from utils.qapp import checkQLineEditValidatorState
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from parse_log import parse_memory_log

__version__ = '1.2.3'
__revision__ = 14
__app_tittle__ = 'MemoryUsageMonitor'


class MemoryLogParserRunnable(QtCore.QObject):
    """ Runnable object for parsing memory log  """
    queue = QtCore.Signal()
    ev = QtCore.Signal(object)

    def __init__(self, fpath, p_name=None):
        super().__init__()
        self._fpath = fpath
        self._p_name = p_name
        self.queue.connect(self.run)

    @QtCore.Slot()
    def run(self):
        self.ev.emit({'progress_init': ('Parsing ...', 200, 0, 0)})
        try:
            d = parse_memory_log(self._fpath, self._p_name)
            self.ev.emit({'progress_reset': 1})
            self.ev.emit({'memory_log': d})
        except Exception as e:
            error_msg = 'Failed to parse memory log {}. Error message is {}'.format(self._fpath, repr(e))
            logging.error(error_msg)
            self.ev.emit({'progress_reset': 1})
            self.ev.emit({'error': error_msg})


class TreeItemsSelector(QtWidgets.QDialog):
    """ A common item selector using tree widget """

    def __init__(self, items: list, title='Items Selector', item_cat='Features', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 200)
        self._items = {}
        self._init_ui(items, item_cat)

    def _init_ui(self, items, item_cat):
        """ Initialize the user interface """
        tree = QtWidgets.QTreeWidget()
        tree.setColumnCount(1)
        # tree.setHeaderHidden(True)
        tree.setHeaderLabel(item_cat)

        # parent = QtWidgets.QTreeWidgetItem(tree)
        # parent.setText(0, '{}'.format(item_cat))
        # parent.setFlags(parent.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
        for item in items:
            tree_item = QtWidgets.QTreeWidgetItem(tree)
            tree_item.setText(0, '{}'.format(item))
            tree_item.setFlags(tree_item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable)
            tree_item.setCheckState(0, QtCore.Qt.Unchecked)

        tree.itemChanged.connect(self._on_item_toggled)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(tree)
        vbox_layout.addWidget(btn_box)

        self.setLayout(vbox_layout)

    def _on_item_toggled(self, item, column):
        if item.checkState(column) == QtCore.Qt.Checked:
            checked = True
        elif item.checkState(column) == QtCore.Qt.Unchecked:
            checked = False
        self._items[item.text(column)] = checked

    @property
    def items(self) -> Tuple:
        items = [k for k, v in self._items.items() if v]
        return tuple(items)


class MemoryUsageMonitor(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QtCore.QSettings(QtCore.QSettings.NativeFormat,
                                          QtCore.QSettings.UserScope,
                                          'HF_AIO', 'MemoryUsageMonitor')
        self._pid = None
        self._ct = ''
        self._dq = collections.deque(maxlen=self._settings.value('dq_maxlen', 120, type=int))
        self._progress = QtWidgets.QProgressDialog(self)
        self._progress.setCancelButton(None)
        self._progress.setWindowTitle(__app_tittle__)
        self._progress.setWindowModality(QtCore.Qt.WindowModal)
        self._progress.setMinimumWidth(300)
        self._progress.reset()
        self._worker_thread = QtCore.QThread()
        self._worker_thread.start()
        self._log_parse_runnable = None  # type: Union[None, QtCore.QObject]
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._on_timer)
        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self):
        self.setMinimumSize(800, 600)
        self.setWindowTitle("{0} ({1}.{2})".format(
            __app_tittle__, __version__, __revision__))
        # self.setWindowIcon(loadQIcon('icons/app_icon.png'))
        # The main widget
        widget = QtWidgets.QWidget()
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                            QtWidgets.QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(widget.sizePolicy().hasHeightForWidth())
        widget.setSizePolicy(size_policy)
        # create widgets ... # the first row
        ctrl_layout = self._create_main_ctrls()
        # create matplotlib widgets and components
        canvas = self._setup_mpl_widget()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(canvas)
        main_layout.addLayout(ctrl_layout)
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.statusBar().showMessage('Launched ...', 1000)

    def _setup_plot_frame(self, monitor=True):
        self._mpl_ax.spines['bottom'].set_color('w')
        self._mpl_ax.spines['top'].set_color('w')
        self._mpl_ax.spines['right'].set_color('w')
        self._mpl_ax.spines['left'].set_color('w')
        # white text, ticks
        self._mpl_ax.set_title('Memory Usage Monitor',
                               color='w', fontdict={'fontsize': 10})
        self._mpl_ax.set_ylabel('Usage (MB)', color='w')
        self._mpl_ax.tick_params(axis='both', color='w')
        self._mpl_ax.tick_params(colors='w', labelsize=8)
        # dark background
        color = self.palette().color(QtGui.QPalette.Window).getRgbF()
        self._mpl_ax.figure.patch.set_facecolor(color)
        color = self.palette().color(QtGui.QPalette.Base).getRgbF()
        self._mpl_ax.set_facecolor(color)
        if monitor:
            x = np.linspace(0, 10 * np.pi, 100)
            self.line_rss = self._mpl_ax.plot(x, np.sin(x), '-', label='Mem Usage')[0]
            self.line_vms = self._mpl_ax.plot(
                x, np.sin(random.random() * np.pi + x), '--', label='VM Size')[0]
            self._mpl_ax.legend()
            self._mpl_ax.set_xlabel('Date', color='w')
        else:
            self._mpl_ax.grid(True)
            self._mpl_ax.set_xlabel('Elapsed Hours', color='w')

    def _setup_mpl_widget(self):
        canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self._mpl_ax = canvas.figure.subplots()
        canvas.figure.set_tight_layout(True)
        self.addToolBar(
            QtCore.Qt.TopToolBarArea,
            NavigationToolbar(self._mpl_ax.figure.canvas, self)
        )
        self._setup_plot_frame()
        return canvas

    def _create_main_ctrls(self):
        layout = QtWidgets.QHBoxLayout()

        label1 = QtWidgets.QLabel('Interval (second)')
        interval = QtWidgets.QLineEdit()
        interval.setValidator(QtGui.QIntValidator(0, 1000000000))
        interval.setObjectName('interval')
        interval.setAlignment(QtCore.Qt.AlignCenter)
        interval.setToolTip('Data sampling interval')
        interval.setText(self._settings.value('interval', '10', type=str))
        interval.textEdited[str].connect(self._update_settings)
        interval.textChanged.connect(self._check_validator_state)
        layout.addWidget(label1)
        layout.addWidget(interval)

        label2 = QtWidgets.QLabel('Process name')
        p_name = QtWidgets.QLineEdit()
        p_name.setObjectName('process_name')
        p_name.setAlignment(QtCore.Qt.AlignCenter)
        p_name.setToolTip('Name of the process including the extension.'
                          ' It is case sensitive and duplicated name not well supported!')
        p_name.setText(self._settings.value('process_name', '', type=str))
        p_name.textEdited[str].connect(self._update_settings)
        layout.addWidget(label2)
        layout.addWidget(p_name)

        label3 = QtWidgets.QLabel('Buffered data length*')
        dq_maxlen = QtWidgets.QLineEdit()
        dq_maxlen.setValidator(QtGui.QIntValidator(0, 9999))
        dq_maxlen.setObjectName('dq_maxlen')
        dq_maxlen.setAlignment(QtCore.Qt.AlignCenter)
        dq_maxlen.setToolTip('Maximal length of the buffered data points, press entry to apply the change on the fly!')
        dq_maxlen.setText(self._settings.value('dq_maxlen', '120', type=str))
        dq_maxlen.editingFinished.connect(self._on_buffer_size_changed)
        dq_maxlen.textEdited[str].connect(self._update_settings)
        dq_maxlen.textChanged.connect(self._check_validator_state)
        layout.addWidget(label3)
        layout.addWidget(dq_maxlen)

        self._start_btn = QtWidgets.QPushButton('Start')
        self._start_btn.clicked.connect(self._on_start)
        self._start_btn.setEnabled(True)
        self._stop_btn = QtWidgets.QPushButton('Stop')
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)

        layout.addWidget(self._start_btn)
        layout.addWidget(self._stop_btn)
        return layout

    def _setup_shortcuts(self):
        shortcut_t = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_T), self)
        shortcut_t.activated.connect(self._toggle_window_on_top)
        shortcut_s = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_S), self)
        shortcut_s.activated.connect(self._toggle_start_stop)
        shortcut_o = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_O), self)
        shortcut_o.activated.connect(self._open_memory_log)

    def _on_buffer_size_changed(self):
        try:
            val = self._settings.value('dq_maxlen', 120, type=int)
            self._dq = collections.deque(reversed(self._dq), maxlen=val)
            self._dq.reverse()
            msg = 'New buffer max length is {}, current size is {}'.format(val, len(self._dq))
            self.statusBar().showMessage(msg, 1000)
        except Exception as e:
            self.statusBar().showMessage(repr(e), 1000)

    def _toggle_window_on_top(self):
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowStaysOnTopHint)
        self.show()
        if self.windowFlags() & QtCore.Qt.WindowStaysOnTopHint:
            msg = 'Stays On Top: ON'
        else:
            msg = 'Stays On Top: OFF'
        self.statusBar().showMessage(msg, 1000)

    def _toggle_start_stop(self):
        if self._timer.isActive():
            self._on_stop()
        else:
            self._on_start()

    def _on_start(self):
        self._stop_btn.setEnabled(True)
        self._start_btn.setEnabled(False)
        interval = self._settings.value('interval', 10, type=int)
        p_name = self._settings.value('process_name', '', type=str)
        msg = 'Start monitor: [interval: {}, process name {}]'.format(interval, p_name)
        logging.debug(msg)
        self.statusBar().showMessage(msg, 1000)
        # start timer
        self._dq.clear()
        self._pid = None
        self._ct = ''
        self._timer.start(interval * 1000)
        self._mpl_ax.clear()
        self._setup_plot_frame()

    def _on_stop(self):
        self._stop_btn.setEnabled(False)
        self._start_btn.setEnabled(True)
        msg = 'Stop monitor: [pid: {}, create time: {}]'.format(self._pid, self._ct)
        logging.debug(msg)
        self.statusBar().showMessage(msg, 1000)
        # stop timer
        self._timer.stop()

    def _update_settings(self, q_str):
        w = self.sender()
        if isinstance(w, QtWidgets.QCheckBox):
            if w.checkState() == QtCore.Qt.Checked:
                self._settings.setValue(w.objectName(), '1')
            else:
                self._settings.setValue(w.objectName(), '0')
        elif isinstance(w, QtWidgets.QLineEdit):
            self._settings.setValue(w.objectName(), w.text())
        elif isinstance(w, QtWidgets.QComboBox):
            self._settings.setValue(w.objectName(),
                                    '{}'.format(w.currentIndex()))

    def _check_validator_state(self):
        checkQLineEditValidatorState(self.sender(), self.palette().color(QtGui.QPalette.Base))

    def closeEvent(self, event):
        super().closeEvent(event)

    def _update_process_id(self, p_name):
        # try to check whether this id is still valid
        if self._pid is not None:
            try:
                p = psutil.Process(self._pid)
                if p.name() != p_name:
                    self._pid = None
                    self._ct = ''
            except Exception:
                msg = 'Process [{}]-[{}] is Dead'.format(self._pid, self._ct)
                logging.info(msg)
                self.statusBar().showMessage(msg, 1000)
                self._pid, self._ct = None, ''
                self._dq.clear()
                self._mpl_ax.set_title(
                    'Memory Usage Monitor ({} Not Found)'.format(p_name),
                    color='w', fontdict={'fontsize': 10})
                self._mpl_ax.figure.canvas.draw_idle()

        # try to get a new pid
        if self._pid is None:
            for proc in psutil.process_iter(attrs=['pid', 'name']):
                if proc.info['name'] == p_name:
                    self._pid = proc.info['pid']
                    self._ct = datetime.datetime.fromtimestamp(
                        proc.create_time()).strftime('%Y-%m-%d %H:%M:%S')
                    self._mpl_ax.set_title('Memory Usage Monitor ({} - {})'.format(p_name, self._ct),
                                           color='w', fontdict={'fontsize': 10})
                    msg = 'New process [{}]-[{}] found'.format(self._pid, self._ct)
                    logging.info(msg)
                    self.statusBar().showMessage(msg, 1000)
                    break

    def _on_timer(self):
        p_name = self._settings.value('process_name', '', type=str)
        self._update_process_id(p_name)
        if self._pid is not None:
            process = psutil.Process(self._pid)
            memory_usage = process.memory_info()
            logging.info('[{}]-[{}]-[{}] - [{}, {}]'.format(
                self._pid, p_name, self._ct, memory_usage.rss, memory_usage.vms))
            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._dq.appendleft((ts, memory_usage.rss, memory_usage.vms))
            x = np.arange(0, len(self._dq))

            self.line_rss.set_xdata(x)
            rss = np.array([x[1] / 1024 / 1024 for x in self._dq])
            self.line_rss.set_ydata(rss)

            self.line_vms.set_xdata(x)
            vms = np.array([x[2] / 1024 / 1024 for x in self._dq])
            self.line_vms.set_ydata(vms)

            self._mpl_ax.set_ylim(0, max(np.max(vms), np.max(rss)) * 1.1)
            self._mpl_ax.set_xlim(
                0,
                min(max(len(x) * 1.2, self._dq.maxlen // 4), self._dq.maxlen)
            )

            ts = [x[0] for x in self._dq]
            labels = []
            for pos in self._mpl_ax.get_xticks():
                pos = int(pos)
                if pos < len(ts):
                    labels.append(ts[pos][5:])
                else:
                    labels.append('')
            self._mpl_ax.set_xticklabels(labels)

            self._mpl_ax.figure.canvas.draw()

    @QtCore.Slot(object)
    def _on_assist_worker_thread_event(self, d):
        """ d is python dict """
        if 'error' in d:
            error_msg = d['error']
            QtWidgets.QMessageBox.critical(self, __app_tittle__, error_msg)
        elif 'warn' in d:
            warn_msg = d['warn']
            QtWidgets.QMessageBox.warning(self, __app_tittle__, warn_msg)
        elif 'progress_init' in d:
            txt, duration, pos_min, pos_max = d['progress_init']
            self._progress.setLabelText(txt)
            self._progress.setMinimumDuration(duration)
            self._progress.setRange(pos_min, pos_max)
            self._progress.setValue(pos_min)
        elif 'progress_update' in d:
            self._progress.setValue(d['progress_update'])
        elif 'progress_reset' in d:
            self._progress.reset()
        elif 'memory_log' in d:
            self._draw_memory_log(d['memory_log'])

    def _draw_memory_log(self, d: pd.DataFrame):
        if d.empty:
            p_name = self._settings.value('process_name', '', type=str)
            QtWidgets.QMessageBox.warning(self, __app_tittle__,
                                          'Memory usage log of process `{}` is not found!'.format(p_name))
            return

        g = d.groupby(['Process'])
        items = list(g.groups.keys())
        if len(items) != 1:
            dlg = TreeItemsSelector(items, title='Select items to draw', item_cat='Process Information', parent=self)
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                items = dlg.items
            else:
                return

        if not items:
            return

        n = len(items)
        self._progress.setRange(0, n)
        self._progress.setValue(0)
        self._mpl_ax.clear()
        self._setup_plot_frame(False)
        interval = self._settings.value('interval', 10, type=int)
        length_lim = self._settings.value('length_limit', 100, type=int)
        convert_to_hours = 60 * 60 / interval
        not_empty_plot = False
        for key, grp in g:
            if key not in items or len(grp['rss']) < length_lim:
                logging.warning('{} dropped, not selected or not enough length'.format(key))
            else:
                not_empty_plot = True
                self._mpl_ax.plot(np.arange(len(grp['rss'])) / convert_to_hours, grp['rss'] / 1024 / 1024, label=key)
            self._progress.setValue(self._progress.value() + 1)
        if not_empty_plot:
            self._mpl_ax.legend()
        self._mpl_ax.figure.canvas.draw()
        self._progress.reset()

    def _open_memory_log(self):
        log_path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select Memory Log file',
            directory=self._settings.value('prev_log_dir', '.', type=str),
            filter='Memory Log (*.log)')
        if not log_path:
            return
        self._settings.setValue('prev_log_dir', os.path.dirname(log_path))
        # firstly stop monitor
        self._on_stop()
        p_name = self._settings.value('process_name', '', type=str)

        if self._log_parse_runnable is not None:
            self._log_parse_runnable.ev.disconnect(self._on_assist_worker_thread_event)
        # pass image to worker
        self._log_parse_runnable = MemoryLogParserRunnable(log_path, p_name)
        self._log_parse_runnable.moveToThread(self._worker_thread)
        self._log_parse_runnable.ev.connect(self._on_assist_worker_thread_event)
        self._log_parse_runnable.queue.emit()

    def center(self):
        frame_gm = self.frameGeometry()
        screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
        center_pt = QtWidgets.QApplication.desktop().screenGeometry(screen).center()
        frame_gm.moveCenter(center_pt)
        self.move(frame_gm.topLeft())


if __name__ == "__main__":
    # enable logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # file output to record memory usage
    fh = logging.FileHandler('memory.log')
    fh.setFormatter(formatter)
    fh.setLevel(logging.INFO)
    # we also need stream output for debugging
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.WARNING)
    # add the handlers to logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    # logging end
    setHighDPI()
    # create Qt Application
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(loadQIcon('icons/app_icon.png'))
    try:
        import qtmodern.styles

        qtmodern.styles.dark(app)
    except ModuleNotFoundError:
        setDarkStyle(app)
    # update default font for Windows 10
    if sys.platform == "win32":
        font = QtGui.QFont("Segoe UI", 9)
        app.setFont(font)
    # create the MainForm
    form = MemoryUsageMonitor()
    form.center()
    try:
        import qtmodern.windows

        mw = qtmodern.windows.ModernWindow(form)
        mw.show()
    except ModuleNotFoundError:
        form.show()
    sys.exit(app.exec_())
