'''
Created on 17.03.2019

@author: Thomas Pietrowski
'''

try:
    from UM.Logger import Logger
except Exception:
    class Logger:
        @classmethod
        def log(self, level, msg):
            print("<{}>: {}".format(level, msg))
