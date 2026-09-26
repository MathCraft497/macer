# 由 Macer 编译器生成 —— 请勿手动修改
from __future__ import annotations
import sys
from macer.runtime import *
from macer.runtime import __macer_wrap__

class macer_lang_Object:
    def __getitem__(self, text):
        return text
    def toString(self):
        return macer_lang_String(['O', 'b', 'j', 'e', 'c', 't'])
    def __eq__(self, other):
        return (self == other)

class com_example_app_App(macer_lang_Object):
    def run(self):
        sh = com_example_util_StringHelper()
        mh = com_example_util_MathHelper()
        math = macer_math_Math()
        print(sh.shout(macer_lang_String(['h', 'e', 'l', 'l', 'o'])))
        print((macer_lang_String(['s', 'q', 'u', 'a', 'r', 'e', '(', '5', ')', ' ', '=', ' ']) + _str_from_chars(_chars_of(mh.square(5)))))
        print((macer_lang_String(['c', 'u', 'b', 'e', '(', '3', ')', ' ', '=', ' ']) + _str_from_chars(_chars_of(mh.cube(3)))))
        print((macer_lang_String(['m', 'a', 'x', '(', '1', '0', ',', ' ', '7', ')', ' ', '=', ' ']) + _str_from_chars(_chars_of(mh.max(10, 7)))))
        print((macer_lang_String(['M', 'a', 't', 'h', '.', 'P', 'I', ' ', '=', ' ']) + _str_from_chars(_chars_of(math.PI))))

class com_example_util_StringHelper(macer_lang_Object):
    def upper(self, s):
        return s
    def join(self, a, b):
        return (a + b)
    def shout(self, s):
        return self.join(self.upper(s), macer_lang_String(['!', '!', '!']))

class macer_lang_String(macer_lang_Object):
    def __init__(self, cs):
        self.chars = None
        self.chars = cs
    def length(self):
        return len(self.chars)
    def isEmpty(self):
        return (len(self.chars) == 0)
    def at(self, i):
        return self.chars[i]
    def concat(self, other):
        result = []
        i = 0
        while (i < len(self.chars)):
            result.append(self.chars[i])
            i = (i + 1)
        i = 0
        while (i < len(other.chars)):
            result.append(other.chars[i])
            i = (i + 1)
        return macer_lang_String(result)
    def upper(self):
        result = []
        i = 0
        while (i < len(self.chars)):
            result.append(_char_toUpper(self.chars[i]))
            i = (i + 1)
        return macer_lang_String(result)
    def lower(self):
        result = []
        i = 0
        while (i < len(self.chars)):
            result.append(_char_toLower(self.chars[i]))
            i = (i + 1)
        return macer_lang_String(result)
    def reverse(self):
        result = []
        i = (len(self.chars) - 1)
        while (i >= 0):
            result.append(self.chars[i])
            i = (i - 1)
        return macer_lang_String(result)
    def trim(self):
        start = 0
        end = len(self.chars)
        while ((start < end)  and  (_char_toInt(self.chars[start]) <= 32)):
            start = (start + 1)
        while ((end > start)  and  (_char_toInt(self.chars[(end - 1)]) <= 32)):
            end = (end - 1)
        return self.slice(start, end)
    def slice(self, a):
        return self.slice(a, len(self.chars))
    def slice(self, a, b):
        result = []
        i = a
        while (i < b):
            result.append(self.chars[i])
            i = (i + 1)
        return macer_lang_String(result)
    def repeat(self, n):
        result = []
        k = 0
        while (k < n):
            i = 0
            while (i < len(self.chars)):
                result.append(self.chars[i])
                i = (i + 1)
            k = (k + 1)
        return macer_lang_String(result)
    def find(self, sub):
        if (len(sub.chars) == 0):
            return 0
        i = 0
        while ((i + len(sub.chars)) <= len(self.chars)):
            j = 0
            match = True
            while (j < len(sub.chars)):
                if (_char_toInt(self.chars[(i + j)]) != _char_toInt(sub.chars[j])):
                    match = False
                j = (j + 1)
            if match:
                return i
            i = (i + 1)
        return (-1)
    def contains(self, sub):
        return (self.find(sub) >= 0)
    def startsWith(self, prefix):
        if (len(prefix.chars) > len(self.chars)):
            return False
        i = 0
        while (i < len(prefix.chars)):
            if (_char_toInt(self.chars[i]) != _char_toInt(prefix.chars[i])):
                return False
            i = (i + 1)
        return True
    def endsWith(self, suffix):
        if (len(suffix.chars) > len(self.chars)):
            return False
        off = (len(self.chars) - len(suffix.chars))
        i = 0
        while (i < len(suffix.chars)):
            if (_char_toInt(self.chars[(off + i)]) != _char_toInt(suffix.chars[i])):
                return False
            i = (i + 1)
        return True
    def replace(self, old, repl):
        result = []
        i = 0
        while (i < len(self.chars)):
            if (((i + len(old.chars)) <= len(self.chars))  and  (self.slice(i, (i + len(old.chars))).find(old) == 0)):
                j = 0
                while (j < len(repl.chars)):
                    result.append(repl.chars[j])
                    j = (j + 1)
                i = (i + len(old.chars))
            else:
                result.append(self.chars[i])
                i = (i + 1)
        return macer_lang_String(result)
    def __add__(self, other):
        return self.concat(other)
    def __eq__(self, other):
        if (len(self.chars) != len(other.chars)):
            return False
        i = 0
        while (i < len(self.chars)):
            if (_char_toInt(self.chars[i]) != _char_toInt(other.chars[i])):
                return False
            i = (i + 1)
        return True
    def __ne__(self, other):
        return (not (self == other))
    def __getitem__(self, text):
        return self

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

__set_string_class(macer_lang_String)

if __name__ == '__main__':
    __macer_wrap__(main)