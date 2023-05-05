# Copyright (C) 2019 Thomas Karl Pietrowski

# Python built-ins
import os
import sys

# Uranium/Cura
from UM.Logger import Logger  # @UnresolvedImport

# Trying to import one of the COM modules
try:
    from .PyWin32Connector import ComConnector
    Logger.log("i", "ComFactory: Using pywin32!")
except ImportError:
    from .ComTypesConnector import ComConnector
    Logger.logException("i", "ComFactory: Using comtypes!")
