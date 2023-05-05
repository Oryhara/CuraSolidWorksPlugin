# PyQt6/Qt
from PyQt6.QtCore import pyqtSlot  # @UnresolvedImport

# UM/Cura
from UM.Logger import Logger  # @UnresolvedImport

# CIU
from .Compat import Deprecations


class PreferencesAdvanced:
    def __init__(self, namespace):
        self.namespace = namespace
        self.type_storage = {}

    def addPreference(self, name, default):
        if default is None:
            raise ValueError("NoneType default values are not allowed. Use either False or 0!")
        self.type_storage[name] = type(default)
        Deprecations.getPreferences().addPreference("{}/{}".format(self.namespace, name), default)

    def getValue(self, name, forced_type=None):
        result = Deprecations.getPreferences().getValue("{}/{}".format(self.namespace, name))  # Received as a string
        target_type = self.determineTargetType(name, forced_type)

        # Forcing type conversion when the type is known. Should be normally the case.
        if target_type:
            # Corrections if the result out of Cura's preference storage is a string..
            if type(result) is str:
                # Special steps for booleans
                if target_type is bool:
                    if result.lower() == "true":
                        result = True
                    elif result.lower() == "false":
                        result = False
                    else:
                        # Assuming that the text is an int or float from now..
                        result = float(result)  # "1.2"
                        result = int(result)  # 1.2

            # Special steps for integers
            if target_type is int and type(result) is not int:
                # Giving a stored int a last chance if the value has been saved as float
                result = float(result)
            result = target_type(result)

        return result

    def setValue(self, name, value, forced_type=None):
        target_type = self.determineTargetType(name, forced_type)  # Received as a string

        # Special conversion of some data types
        # if target_type:
        #    if target_type == foo_type:
        #        value = foo(bar)
        value = str(value)

        # Passing all as strings as it will be stored and restored in strings into the config file later
        result = Deprecations.getPreferences().setValue("{}/{}".format(self.namespace, name), value)

        return None

    def determineTargetType(self, name, forced_type=None):
        "Checking for the targetted type of data"

        target_type = None
        stored_type = None
        if name in self.type_storage.keys():
            stored_type = self.type_storage[name]
            target_type = stored_type
        if forced_type:
            if stored_type and forced_type is not stored_type:
                Logger.log("w", "Stored type as set by default value does not fit to forced type!")
            target_type = forced_type
        return target_type
