# -*- encoding:utf-8 -*-
from __future__ import print_function
from __future__ import division

from contextlib import contextmanager
from IPython.display import display
import os
import sys
import warnings

sys.path.insert(0, os.path.abspath('../'))
warnings.filterwarnings('ignore')
warnings.simplefilter('ignore')


# noinspection PyUnresolvedReferences,PyProtectedMember
class WidgetBase(object):
    """界面组件基类，限定最终widget为self.widget"""

    def __call__(self):
        return self.widget

    def display(self):
        """显示使用统一display"""
        display(self.widget)


@contextmanager
def show_ui_ct():
    print('正在初始化界面元素，请稍后...')
    go_on = True

    yield go_on
    if go_on:
        from IPython.display import clear_output
        clear_output()
