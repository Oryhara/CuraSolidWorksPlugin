# Copyright (C) 2019 Thomas Karl Pietrowski

# Buildins
import os
import time
import tempfile
import threading
import uuid
import platform

# Uranium/Cura
from UM.Application import Application  # @UnresolvedImport
from UM.Extension import Extension  # @UnresolvedImport
from UM.Logger import Logger  # @UnresolvedImport
from UM.i18n import i18nCatalog  # @UnresolvedImport
from UM.Mesh.MeshReader import MeshReader  # @UnresolvedImport
from UM.Message import Message  # @UnresolvedImport
from UM.PluginRegistry import PluginRegistry  # @UnresolvedImport

# CIU
from .Extras.Compat import ApplicationCompat
from .Extras.Preferences import PreferencesAdvanced
from .Extras.SystemUtils import registerThirdPartyModules

# Loading third party modules
third_party_dir = os.path.realpath(__file__)
third_party_dir = os.path.dirname(third_party_dir)
third_party_dir = os.path.join(third_party_dir, "3rd-party")
if os.path.isdir(third_party_dir):
    registerThirdPartyModules(third_party_dir)

if platform.system() == "Windows":
    from .Extras.SystemUtils import convertDosPathIntoLongPath

i18n_catalog = i18nCatalog("CadIntegrationUtils")


class OptionKeywords:
    application_name = "app_name"
    application_instance = "app_instance"
    application_export_quality = "app_export_quality"
    import_file = "foreignFile"
    export_file = "tempFile"
    export_file_preserve = "tempFileKeep"
    export_format = "tempType"
    export_formats = "fileFormats"


class CommonExtension(Extension):
    def __init__(self,
                 name,
                 id,
                 reader,
                 ):
        super().__init__()

        # Plugin related variables
        self._name = name

        # Prefereces for all parameters and settings
        self.preference_storage = PreferencesAdvanced(id)
        self.preference_storage.addPreference("ciu.debug", False)

        self.reader = reader
        self.reader.extension = self

        # Setting up menu entries
        self.prepareMenu()

    def prepareMenu(self):
        self.setMenuName(self._name)


class CommonReader(MeshReader):
    conversion_lock = threading.Lock()

    def __init__(self):
        super().__init__()

        self.applications = []
        self.application_preferred = None

        # By default allow no parallel execution. Just to be failsave...
        self._parallel_execution_allowed = False

        # # Start/stop behaviour

        # Technically neither preloading nor keeping the instance up,
        # is possible, since Cura calls the file reader from different/new threads
        # The error when trying to use it here is:
        # > pywintypes.com_error:
        # (-2147417842, 'The application called an interface that was marshalled for a different thread.', None, None)
        self._app_preload = False
        self._app_keep_running = False

        """
        if self._app_preload and not self._app_keep_running:
            self._app_keep_running = True
        """

        # Preparations
        """
        if self._app_preload:
            Logger.log("d", "Preloading %s..." %(self._app_friendlyName))
            self.startApp()
        """

        # Quality
        self.quality_classes = None

        # Doing some routines after all plugins are loaded
        ApplicationCompat().pluginsLoaded.connect(self._onAfterPluginsLoaded)

    def _onAfterPluginsLoaded(self):
        return None

    def preStartApp(self, options):
        pass

    def getAppVisible(self, state):
        raise NotImplementedError("Toggle for visibility not implemented!")

    def setAppVisible(self, state, options):
        raise NotImplementedError("Toggle for visibility not implemented!")

    def closeApp(self, options):
        raise NotImplementedError("Procedure how to close your app is not implemented!")

    def postCloseApp(self, options):
        pass

    def openForeignFile(self, options):
        "This function shall return options again."
        "It optionally contains other data, which is needed by the reader"
        "for other tasks later."
        raise NotImplementedError("Opening files is not implemented!")

    def exportFileAs(self, options, quality_enum=None):
        raise NotImplementedError("Exporting files is not implemented!")

    def closeForeignFile(self, options):
        raise NotImplementedError("Closing files is not implemented!")

    def renameNodes(self, options, scene_nodes):
        for scene_node in scene_nodes:
            if not scene_node.hasChildren():
                mesh_data = scene_node.getMeshData()

                Logger.log("d", "File path in mesh was: {}".format(mesh_data.getFileName()))
                mesh_data = mesh_data.set(file_name=options[OptionKeywords.import_file])
                scene_node.setMeshData(mesh_data)
            else:
                self.renameNodes(options, scene_node.getAllChildren())
        return scene_nodes

    def nodePostProcessing(self, options, scene_nodes):
        self.renameNodes(options, scene_nodes)
        return scene_nodes

    def readCommon(self, file_path):
        "Common steps for each read"

        options = {OptionKeywords.import_file: file_path,
                   "foreignFormat": os.path.splitext(file_path)[1],
                   OptionKeywords.export_file_preserve: False,
                   OptionKeywords.export_formats: [],
                   }

        # Let's convert only one file at a time!
        if not self._parallel_execution_allowed:
            self.conversion_lock.acquire()

        # Append all formats which are not preferred to the end of the list
        return options

    def preRead(self, options):
        return MeshReader.PreReadResult.accepted

    def readOnSingleAppLayer(self, options):
        scene_node = None

        # Tell the loaded application to open a file...
        Logger.log("d", "... and opening file.")
        options = self.openForeignFile(options)

        # Trying to convert into all formats 1 by 1 and continue with the successful export
        Logger.log("i", "Trying to convert into one of: %s", options[OptionKeywords.export_formats])
        for file_format in options[OptionKeywords.export_formats]:
            Logger.log("d", "Trying to convert <%s>...", os.path.split(options[OptionKeywords.import_file])[1])
            options[OptionKeywords.export_format] = file_format

            # Creating a new unique filename in the temporary directory..
            tempdir = tempfile.gettempdir()
            Logger.log("d", "Using suggested tempdir: {}". format(repr(tempdir)))
            if platform.system() == "Windows":
                tempdir = convertDosPathIntoLongPath(tempdir)
            options[OptionKeywords.export_file] = os.path.join(tempdir,
                                                               "{}.{}".format(uuid.uuid4(), file_format.upper()),
                                                               )
            Logger.log("d", "... into '%s' format: <%s>", file_format, options[OptionKeywords.export_file])
            # Export using quality classes if possible
            if self.quality_classes is None:
                quality_classes = {None: None}
            else:
                quality_classes = self.quality_classes

            quality_enums = list(quality_classes.keys())
            quality_enums.sort()
            quality_enums.reverse()

            if OptionKeywords.application_export_quality in options.keys():
                quality_enum_target = options[OptionKeywords.application_export_quality]
                while quality_enums[0] > quality_enum_target:
                    del quality_enums[0]

            for quality_enum in quality_enums:
                try:
                    self.exportFileAs(options, quality_enum=quality_enum)
                except Exception:
                    Logger.logException("e", "Could not export <{}> into {}.".format(
                        options[OptionKeywords.import_file], repr(file_format)))
                    continue

                if os.path.isfile(options[OptionKeywords.export_file]):
                    size_of_file_mb = os.path.getsize(options[OptionKeywords.export_file]) / 1024 ** 2
                    Logger.log("d", "Found temporary file! (size: {}MB)".format(size_of_file_mb))
                    break
                else:
                    Logger.log("c", "Temporary file not found after export! (next quality class..)")
                    continue
            if not os.path.isfile(options[OptionKeywords.export_file]):
                Logger.log("c", "Temporary file not found after export! (next file format..)")
                continue

            if OptionKeywords.application_export_quality in options.keys():
                if quality_enum is not quality_enum_target:
                    error_message = Message(
                        i18n_catalog.i18nc("@info:status",
                                           "Could not export using \"{}\" quality!\nFelt back to \"{}\".".format(
                                                self.quality_classes[quality_enum_target],
                                                self.quality_classes[quality_enum]
                                                )
                                           )
                    )
                    error_message.show()

            # Opening the resulting file in Cura
            try:
                reader = Application.getInstance().getMeshFileHandler(
                ).getReaderForFile(options[OptionKeywords.export_file])
                if not reader:
                    Logger.log("d", "Found no reader for {}. That's strange...".format(file_format))
                    continue
                Logger.log("d", "Using reader: %s", reader.getPluginId())
                scene_node = reader.read(options[OptionKeywords.export_file])
                if not scene_node:
                    Logger.log("d", "Scene node is {}. Trying next format and therefore other file reader!".format(
                        repr(scene_node)))
                    continue
                elif not isinstance(scene_node, list):
                    # This part is needed for reloading converted files into STL
                    # Cura will try otherwise to reopen the temp file, which is already removed.
                    scene_node = [scene_node, ]

                self.nodePostProcessing(options, scene_node)

                break
            except Exception:
                Logger.logException("e", "Failed to open exported <%s> file in Cura!", file_format)
                continue
            finally:
                # Whatever happens, remove the temp_file again..
                max_tries = 3
                for ntry in range(1, max_tries+1):
                    try:
                        if not options[OptionKeywords.export_file_preserve]:
                            fargs = (ntry,
                                     max_tries,
                                     file_format,
                                     options[OptionKeywords.export_file],
                                     )
                            Logger.log("d", "({}/{}) Removing temporary {} file, called <{}>".format(*fargs)
                                       )
                            os.remove(options[OptionKeywords.export_file])
                        else:
                            Logger.log("d", "Keeping temporary {} file, called <{}>".format(
                                file_format, options[OptionKeywords.export_file]))
                        break
                    except Exception:
                        Logger.logException("e", "Failed to remove temporary file... waiting for another 5s...")
                        time.sleep(5)
                        continue

        return scene_node

    def readOnMultipleAppLayer(self, options):
        scene_node = None

        list_of_apps = self.applications
        prefered_app = self.application_preferred
        if prefered_app:
            if prefered_app in list_of_apps:
                list_of_apps.remove(prefered_app)
            list_of_apps = [prefered_app, ] + list_of_apps

        for app_name in list_of_apps:
            if prefered_app and app_name is not prefered_app:
                Logger.log("e", "Couldn't use prefered app. Had to fall back!")
            options[OptionKeywords.application_name] = app_name

            # Preparations before starting the application
            self.preStartApp(options)
            try:
                # Start the app by its name...
                self.startApp(options)

                scene_node = self.readOnSingleAppLayer(options)
                if scene_node:
                    # We don't need to test the next application.
                    # The result is already there...
                    break

            except Exception:
                Logger.logException("e", "Failed to export using {}...".format(repr(app_name)))
                # Let's try with the next application...
                continue
            finally:
                # Closing document in the app
                self.closeForeignFile(options)
                # Closing the app again..
                self.closeApp(options)
                # Nuke the instance!
                if OptionKeywords.application_instance in options.keys():
                    del options[OptionKeywords.application_instance]
                # .. and finally do some cleanups
                self.postCloseApp(options)

        if not scene_node:
            Logger.log("d", "Scene node is {}. We had no luck to use any of the readers to get the mesh data!".format(
                repr(scene_node)))
            return scene_node

        return scene_node
