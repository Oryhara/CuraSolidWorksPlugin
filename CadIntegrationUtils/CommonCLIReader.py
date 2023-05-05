# Copyright (C) 2019 Thomas Karl Pietrowski

# Uranium
from UM.Platform import Platform  # @UnresolvedImport
from UM.Logger import Logger  # @UnresolvedImport

# CIU
from .CommonReader import CommonReader  # @UnresolvedImport

# built-ins
import os
import subprocess

# OS dependent
if Platform.isWindows():
    import winreg
elif Platform.isOSX():
    from urllib.parse import urlparse
    import objc
    import LaunchServices


class OtherCLI():
    def findPathsForFilepath(self, filepath):
        return []

    def findPathsForExtension(self, extension):
        return []


class MacOSCLI(OtherCLI):
    def findPathsForFilepath(self, filepath):
        filepath_objc = objc.FSRef.from_pathname(filepath)
        application_location = LaunchServices.LSGetApplicationForItem(filepath_objc,
                                                                      0x000004,
                                                                      None,
                                                                      None)[2]
        application_url = application_location.description()
        application_path = urlparse(application_url).path
        return [application_path, ]


class WindowsCLI(OtherCLI):
    def findPathsForExtension(self, extension):
        paths = []
        for found_paths in (self.findPathsForExtensionRootClassic(extension),
                            self.findPathsForExtensionUserClassic(extension),
                            self.findPathsForExtensionUserModern(extension),
                            ):
            if type(found_paths) is list:
                for path in found_paths:
                    if path not in paths:
                        paths.insert(0, path)
            else:
                Logger.log("e", "Unknown data type for \"found_paths\": {}".format(type(found_paths)))
        return paths

    def findPathsForExtensionUserModern(self, extension):
        key_base = winreg.HKEY_CURRENT_USER
        appid = None

        try:
            user_choice = winreg.OpenKey(key_base,
                                         os.path.join("Software",
                                                      "Microsoft",
                                                      "Windows",
                                                      "CurrentVersion",
                                                      "Explorer",
                                                      "FileExts",
                                                      extension,
                                                      "UserChoice"
                                                      ),
                                         )
            key_len = winreg.QueryInfoKey(user_choice)[1]
            for pos in range(key_len):
                entry = winreg.EnumValue(user_choice, pos)
                if entry[0].lower() == "ProgId".lower() and not appid:
                    appid = entry[1]
        except Exception:
            Logger.logException("e", "Exception, while looking for AppID: \"{}\"".format(extension))
            return []

        if appid:
            key_path = os.path.join("Software", "Classes", appid)

            result = self._findPathsForExtensionClassic(appid,
                                                        key_base,
                                                        key_path,
                                                        )
            Logger.log("d", "The result is: \"{}\"".format(result))
            return result

    def findPathsForExtensionRootClassic(self, extension):
        key_base = winreg.HKEY_CLASSES_ROOT
        key_path = os.path.join("{}")

        result = self._findPathsForExtensionClassic(extension,
                                                    key_base,
                                                    key_path,
                                                    )
        Logger.log("d", "The result is: \"{}\"".format(result))
        return result

    def findPathsForExtensionUserClassic(self, extension):
        key_base = winreg.HKEY_CURRENT_USER
        key_path = os.path.join("Software", "Classes", "{}")

        result = self._findPathsForExtensionClassic(extension,
                                                    key_base,
                                                    key_path,
                                                    )
        Logger.log("d", "The result is: \"{}\"".format(result))
        return result

    def _findPathsForExtensionClassic(self, extension, key_base, key_path):
        try:
            file_class = winreg.QueryValue(key_base,
                                           key_path.format(extension),
                                           )
        except FileNotFoundError as e:
            Logger.log("i", "File extension not found in registry: \"{}\"".format(extension))
            return []
        except Exception as e:
            Logger.logException("e", "Unknown exception, while looking for extension: {}".format(extension))
            return []

        if file_class and not file_class == extension:
            if not file_class == extension:
                # Otherwise we might end up in an endless loop
                Logger.log("d", "File extension seems to be an alias. Following {}...".format(repr(file_class)))
                result = self._findPathsForExtensionClassic(file_class, key_base, key_path)

                if not result:
                    Logger.log("d", "Class <{}> gave no result. Determining the command here.".format(repr(file_class)))
                else:
                    return result

        try:
            command = winreg.QueryValue(key_base, os.path.join(key_path.format(extension),
                                                               "shell",
                                                               "open",
                                                               "command"
                                                               ),
                                        )
        except FileNotFoundError as e:
            Logger.log("i", "File extension not found in registry: \"{}\"".format(extension))
            return []
        except Exception as e:
            Logger.logException("e", "Unknown exception, while looking for the path of extension: {}".format(extension))
            return []

        return self._convertCommandIntoPath(command)

    def _convertCommandIntoPath(self, command):
        try:
            splitted_command = command.split("\"")
            while "" in splitted_command:
                splitted_command.remove("")
            splitted_command = splitted_command[0]
            path = os.path.dirname(splitted_command)
        except Exception as e:
            Logger.logException("e", "Unknown exception, while formatting : <{}>".format(command))
            return []

        if not os.path.isdir(path):
            return []
        else:
            return [path, ]


# OS dependent
if Platform.isWindows():
    PlatformCLI = WindowsCLI
elif Platform.isOSX():
    PlatformCLI = MacOSCLI
else:
    PlatformCLI = OtherCLI


class CommonCLIReader(CommonReader, PlatformCLI):
    def __init__(self):
        super().__init__()
        self._parallel_execution_allowed = True

        self._additional_paths_by_extensions = []
        self._additional_paths_by_filepath = []

        self._application_location = {Platform.PlatformType.OSX: "Contents/MacOS",
                                      }

    def preStartApp(self):
        # Nothing needs to be prepared before starting
        pass

    def startApp(self, options):
        # No start needed..
        return options

    def openForeignFile(self, options):
        # We open the file, while converting.. No actual opening of the file needed..
        return options

    def read(self, file_path):
        # Before entering the conversion procedure look for assignments for this file.
        self._additional_paths_by_filepath = self.findPathsForFilepath(file_path)

        # Doing the actual conversion
        options = self.readCommon(file_path)
        result = super().readOnSingleAppLayer(options)

        # Unlock if needed
        if not self._parallel_execution_allowed:
            self.conversion_lock.release()

        return result

    def executeCommand(self, command, cwd=os.path.curdir, shell=None):
        "Executes an command represented as a list."
        "Just like subprocess.Popen expectes it to be."
        "Furthermore it is using the found paths to expand the PATH environment variable."

        if shell is None:
            if Platform.isWindows():
                shell = True
            else:
                shell = False

        environment_with_additional_path = os.environ.copy()
        additional_paths = []
        if self._additional_paths_by_filepath:
            additional_paths += self._additional_paths_by_filepath
        if self._additional_paths_by_extensions:
            additional_paths += self._additional_paths_by_extensions

        if Platform.getType() in self._application_location.keys():
            additional_paths_copy = additional_paths.copy()
            additional_paths = []
            for additional_path in additional_paths_copy:
                additional_path = os.path.join(additional_path,
                                               self._application_location[Platform.getType()],
                                               )
                additional_path = os.path.realpath(additional_path)
                additional_paths.append(additional_path)

        environment_with_additional_path["PATH"] = os.pathsep.join(
            additional_paths + environment_with_additional_path["PATH"].split(os.pathsep))

        Logger.log("i", "Executing command: {}".format(command))
        Logger.log("i", "...with PATH: {}".format(environment_with_additional_path["PATH"]))
        p = subprocess.Popen(command,
                             cwd=cwd,
                             env=environment_with_additional_path,
                             shell=shell,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             )
        stdout, stderr = p.communicate()
        return p.returncode

    def scanForAllPaths(self):
        "DEPRECATED"
        self.findPathsForAllExtensions()

    def findPathsForAllExtensions(self):
        "Finding all installation paths for all registered file extensions."
        self._additional_paths_by_extensions = []
        for file_extension in self._supported_extensions:
            found_paths = self.findPathsForExtension(file_extension)
            for found_path in found_paths:
                # Validating results be the platform class
                if os.path.isdir(found_path):
                    self._additional_paths_by_extensions.append(found_path)
                else:
                    Logger.log("e", "Found paths for {}, but does not exist: {}".format(file_extension, found_paths))
        Logger.log("d", "The result is: {}".format(repr(self._additional_paths_by_extensions)))
