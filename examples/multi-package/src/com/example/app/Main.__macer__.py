# 由 Macer 编译器生成 —— 请勿手动修改
from __future__ import annotations
import sys
from macer.runtime import *
from macer.runtime import __macer_wrap__

class macer_lang_Object:
    def __getitem__(self, text):
        return text
    def toString(self):
        return 'Object'
    def __eq__(self, other):
        return (self == other)

class com_example_app_App(macer_lang_Object):
    def run(self):
        sh = com_example_util_StringHelper()
        mh = com_example_util_MathHelper()
        math = macer_math_Math()
        print(sh.shout('hello'))
        print(('square(5) = ' + str(mh.square(5))))
        print(('cube(3) = ' + str(mh.cube(3))))
        print(('max(10, 7) = ' + str(mh.max(10, 7))))
        print(('Math.PI = ' + str(math.PI)))

class com_example_util_StringHelper(macer_lang_Object):
    def upper(self, s):
        return s
    def join(self, a, b):
        return (a + b)
    def shout(self, s):
        return self.join(self.upper(s), '!!!')

class com_example_util_MathHelper(macer_lang_Object):
    def square(self, x):
        return (x * x)
    def cube(self, x):
        return ((x * x) * x)
    def max(self, a, b):
        if (a > b):
            return a
        else:
            return b

class macer_math_Math(macer_lang_Object):
    def __init__(self):
        self.PI = 3.141592653589793
    def max(self, a, b):
        if (a > b):
            return a
        else:
            return b
    def min(self, a, b):
        if (a < b):
            return a
        else:
            return b

def main():
    app = com_example_app_App()
    app.run()

if __name__ == '__main__':
    __macer_wrap__(main)