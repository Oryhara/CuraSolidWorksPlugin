# Copyright (C) 2019 Thomas Karl Pietrowski

import os
import sys
import platform
import site

from .Logger import Logger

try:
    import win32api
    win32api_imported = True
except Exception:
    Logger.log("i", "Skipping usage of win32 extensions")
    win32api_imported = False


def registerThirdPartyModules(third_party_dir):
    third_party_dir = os.path.realpath(third_party_dir)
    Logger.log("i", "Adding 3rd-party modules from: {}".format(third_party_dir))

    # Collecting platform info
    platform_info = [platform.python_implementation().lower(),
                     "{0}.{1}".format(*platform.python_version_tuple()),
                     platform.system().lower(),
                     platform.machine().lower(),
                     ]
    Logger.log("i", "Platform is: {}".format(platform_info))

    # Generating directory names
    platform_dirs = ["-".join(platform_info[:x] + ["common", ])
                     for x in range(len(platform_info))] + ["-".join(platform_info), ]
    platform_dirs.reverse()

    # Looking for directories
    found_platform_dirs = []
    for subdir in platform_dirs:
        subdir = os.path.join(third_party_dir, subdir)
        if os.path.isdir(subdir):
            found_platform_dirs.append(subdir)

    # Looking for modules in these directories
    for found_platform_dir in found_platform_dirs:
        for entry in os.listdir(found_platform_dir):
            entry_abs = os.path.join(found_platform_dir, entry)
            if not os.path.isdir(entry_abs):
                continue
            # Ensure that the found path is at the beginning of sys.path
            while entry_abs in sys.path:
                sys.path.remove(entry_abs)
            site.addsitedir(entry_abs)
            Logger.log("i", "Adding module: {}".format(entry))


def convertDosPathIntoLongPath(dosPath):
    # TODO: Move the code into the COM compat layer!
    # longpath = ctypes.create_unicode_buffer(1024)
    # if not ctypes.windll.kernel32.GetLongPathNameW(dosPath, longpath, 1024): # GetLongPathNameW: @UndefinedVariable
    #    # This basically indicates that the call of the function failed, since nothing has been passed to the buffer.
    #    # It is better to catch these situations and raise an error here!
    #    raise ValueError("Bad path passed!")
    # return longpath.value
    if "win32api" in globals():
        dosPath = win32api.GetLongPathName(dosPath)
    return dosPath


class Filesystem:
    def splitCommandString(self, command):
        command = command.split(" ")  # NO! a regular .split() won't work here
        command_len = len(command)

        # In case we have quotes
        if command.count("\"") % 2:
            raise Exception("Uneven count of quotes!")

        command_splitted = []
        i = 0
        while i < command_len:
            entry = command[i]
            if entry.startswith("\""):
                j = i
                while "\"" not in entry[1:]:
                    j += 1
                    entry += " {}".format(command[j])
                i = j
            if entry.startswith("\"") and entry.endswith("\"") and entry.count("\"") == 2:
                entry = entry[1:-1]
            command_splitted.append(entry)
            i += 1

        # In case a shortname has been used
        if platform.system() is "Windows":
            long_name = None
            try:
                long_name = win32api.GetLongPathName(command_splitted[0])
            except Exception:
                pass
            if long_name:
                command_splitted[0] = long_name

        return command_splitted

    @classmethod
    def getExecutableInCommand(self, command, with_environment=False):
        if with_environment:
            if platform.system() is "Windows":
                environment_dirs = os.environ["PATH"].split(os.pathsep)
            else:
                environment_dirs = []

        if type(command) is str:
            command = self.splitCommandString(self, command)

        # In case we had no quotes but whitespaces only - seems to be a new convention around Windows 10
        while not os.path.isfile(command[0]) and len(command) > 1:
            if with_environment:
                for directory in environment_dirs:
                    command_with_env = os.path.join(directory, command[0])
                    if os.path.isfile(command_with_env):
                        break
            command[0] = "{} {}".format(command[0], command[1])
            command.pop(1)

        return command[0]

    @classmethod
    def isExecutableInCommand(self, command, with_environment=False):
        return os.path.isfile(self.getExecutableInCommand(command, with_environment))
