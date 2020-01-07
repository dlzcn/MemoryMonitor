#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ******************************************************
#         @author: Haifeng CHEN - optical.dlz@gmail.com
# @date (created): 2019-10-23 09:26
#           @file: qapp.py
#          @brief: utilities for QT application
#       @internal: 
#        revision: 3
#   last modified: 2019-11-26 12:59:34
# *****************************************************

from PyQt5 import QtCore, QtWidgets, QtGui


def setHighDPI():
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


def setDarkStyle(app):
    try:
        from utils.darkpalette import QDarkPalette
        dark = QDarkPalette()
        dark.set_app(app)
    except ImportError:
        pass
    except TypeError:
        pass


def loadQIcon(ico_name):
    """Load ico file as QT icon object"""
    import os
    from utils.app import get_application_path
    icon = QtGui.QIcon()
    icon_path = os.path.join(get_application_path(), ico_name)
    icon.addPixmap(QtGui.QPixmap(icon_path),
                   QtGui.QIcon.Normal, QtGui.QIcon.Off)
    return icon


def transverseWidgets(layout):
    """Get all widgets inside of the given layout and the sub-layouts"""
    w_lists = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.layout():
            # if type(item) == QtGui.QLayoutItem:
            w_lists.extend(transverseWidgets(item.layout()))
            # if type(item) == QtGui.QWidgetItem:
        if item.widget():
            w = item.widget()
            w_lists.append(w)
            if w.layout():
                w_lists.extend(transverseWidgets(w.layout()))
    return w_lists


def alignComboBoxText(combo, QT_Align):
    """
        Use setAlignment to align text in QComboBox
    """
    combo.setEditable(True)
    combo.lineEdit().setReadOnly(True)
    combo.lineEdit().setAlignment(QT_Align)
    for i in range(combo.count()):
        combo.setItemData(i, QT_Align, QtCore.Qt.TextAlignmentRole)


def ndarrayToQImage(img):
    """ convert numpy array image to QImage """
    if img.dtype != 'uint8':
        raise ValueError('Only support 8U data')

    if img.dim == 3:
        t = QtGui.QImage.Format_RGB888
    elif img.dim == 2:
        t = QtGui.QImage.Format_Grayscale8
    else:
        raise ValueError('Only support 1 and 3 channel image')

    qimage = QtGui.QImage(img.data,
                          img.shape[1], img.shape[0],
                          img.strides[0], t)
    return qimage


def checkQLineEditValidatorState(editor: QtWidgets.QLineEdit, color: QtGui.QColor):
    """ Update QLineEdit background color according to state of its Validator
    :param editor
        The QLineEdit widget object
    :param color
        The default background color
    """
    validator = editor.validator()
    if validator is None:
        return
    state = validator.validate(editor.text(), 0)[0]
    if state == QtGui.QValidator.Acceptable:
        bk_color = color
    elif state == QtGui.QValidator.Intermediate:
        bk_color = QtGui.QColor(255, 127, 14)
    else:
        bk_color = QtGui.QColor(214, 39, 40)
    editor.setStyleSheet('QLineEdit { background-color: %s }' % bk_color.name())


class Receiver(QtCore.QObject):
    """ A QObject (to be run in a QThread) which sits waiting for data to come through a Queue.Queue().
    It blocks until data is available, and one it has got something from the queue, it sends
    it to the "MainThread" by emitting a Qt Signal
    """
    textout = QtCore.pyqtSignal(str)

    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    @QtCore.pyqtSlot()
    def run(self):
        while True:
            text = self.queue.get()
            self.textout.emit(text)
