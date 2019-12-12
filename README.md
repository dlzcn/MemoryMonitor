# Memory monitor

Simple memory usage monitor program based on psutil and Qt.
An interval adjustable timer is used to poll memory usage of process
with dedicated name and then display the latest changable sampled points
on the main windows, sampled points are also recorded in log.

Matplotlib is used to diplay the chart. Python logging module is used to
record sampled points.
