# Copyright (c) 2019 Thomas Karl Pietrowski
__plugin_name__ = "3DS SolidWorks plugin"
__plugin_id__ = "CuraSolidWorksPlugin"

# TODOs:
# * Adding selection to separately import parts from an assembly

# Build-ins
import math
import os
import winreg

# 3rd-party
import numpy

# Cura/Uranium
from UM.Application import Application  # @UnresolvedImport
from UM.i18n import i18nCatalog  # @UnresolvedImport
from UM.Logger import Logger  # @UnresolvedImport
from UM.Math.Matrix import Matrix  # @UnresolvedImport
from UM.Math.Vector import Vector  # @UnresolvedImport
from UM.Math.Quaternion import Quaternion  # @UnresolvedImport
from UM.Mesh.MeshReader import MeshReader  # @UnresolvedImport
from UM.Message import Message  # @UnresolvedImport
from UM.PluginRegistry import PluginRegistry  # @UnresolvedImport
from UM.Version import Version  # @UnresolvedImport

# CIU
from .CadIntegrationUtils.CommonComReader import CommonCOMExtension, CommonCOMReader
from .CadIntegrationUtils.ComFactory import ComConnector
from .CadIntegrationUtils.Extras.SystemUtils import Filesystem
from .CadIntegrationUtils.Extras.Preferences import PreferencesAdvanced
from .CadIntegrationUtils.Extras.WindowsUtils import RegistryTools

# This plugin
from .SolidWorksConstants import SolidWorksEnums, SolidWorkVersions
from .SolidWorksDialogHandler import SolidWorksDialogHandler, SolidWorksReaderWizard

# Since 3.4: Register Mimetypes:
if Version(Application.getInstance().getVersion()) >= Version("3.4"):
    from UM.MimeTypeDatabase import MimeTypeDatabase, MimeType

i18n_catalog = i18nCatalog(__plugin_id__)

EMULATE_VERSION_API = 25


class SolidWorksExtension(CommonCOMExtension):
    def __init__(self,
                 name,
                 id,
                 reader,
                 default_service_name,
                 default_service_id,
                 ):

        super().__init__(name,
                         id,
                         reader,
                         default_service_name,
                         default_service_id,
                         )

        if self.preference_storage.getValue("ciu.debug"):
            Logger.log("w", "RUNNING IN DEBUG MODE!")
            error_message = Message(i18n_catalog.i18nc(
                "@info:status", "RUNNING IN DEBUG MODE!\nIT IS INTENDED THAT THE PLUGIN WILL MISSBEHAVE!!!"))
            error_message.setTitle(__plugin_name__)
            error_message.show()

        # General settings
        self.preference_storage.addPreference("checks_at_initialization", True)

        # conversion settings
        self.preference_storage.addPreference("preferred_installation", -1)
        self.preference_storage.addPreference("export_quality", 10)
        self.preference_storage.addPreference("auto_rotate", True)

        # UI settings
        self.preference_storage.addPreference("show_export_settings_always", True)

        # False is not implemented now! Therefore always True.
        self._convert_assembly_into_once = True

        self.wizard = SolidWorksReaderWizard(self)

        # Service checker
        # Assigning further SolidWorks specific checks
        self.com_service_checker.doBasicChecks = self.com_service_checker_basic
        self.com_service_checker.doAdvancedChecks = self.com_service_checker_advanced

    def prepareMenu(self):
        self._old_dialog_handler = SolidWorksDialogHandler(self)
        super().prepareMenu()

    def prepareComServices(self):
        super().prepareComServices()

        # Service checker
        # Lookup for versioned service ids
        service_ids = RegistryTools().getServicesFromRegistry(self._default_com_service_id)
        Logger.log("d", "service_ids: {}".format(service_ids))
        if service_ids:
            self.purge_com_services()
            for service_id in service_ids:
                service_version = RegistryTools().getEnumOfVersionedServiceID(self._default_com_service_id, service_id)
                service_name = self.getServiceNameByVersion(service_version)
                self.add_com_service(service_id, service_name)

    def getVersionedServiceName(self,
                                version,
                                ):
        return "SldWorks.Application.{}".format(version)

    def getServiceNameByVersion(self,
                                version,
                                ):
        if version in SolidWorkVersions.major_version_name.keys():
            return SolidWorkVersions.major_version_name[version]
        else:
            return self.getVersionedServiceName(version)

    def com_service_checker_basic(self,
                                  version,
                                  keep_instance_running=False,
                                  options={},
                                  ):
        # Also shall confirm the correct major revision from the running instance
        if not options:
            options = {"app_name": self.getVersionedServiceName(version),
                       }
        revision = [-1, ]
        try:
            if "app_instance" not in options.keys():
                self.startApp(options)
            revision = self.getRevisionNumber(options)
        except Exception:
            Logger.logException("e", "Starting the service and getting the major revision number failed!")

        if "app_instance" in options.keys():
            if not keep_instance_running:
                self.closeApp(options)
                if not options["app_was_active"] and not self.getOpenDocuments(options):
                    Logger.log(
                        "d",
                        "Looks like we opened SolidWorks and there are no open files. Let's close SolidWorks again!"
                    )
                    # SolidWorks API: ?
                    options["app_instance"].ExitApp()
                self.postCloseApp(options)
        else:
            Logger.log("e", "Starting service failed!")
            return (False, options)

        if revision[0] == version:
            return (True, options)

        Logger.log("e", "Revision does not fit to {}.x.y: {}".format(version, revision[0]))
        return (False, options)

    def com_service_checker_advanced(self,
                                     version,
                                     keep_instance_running=False,
                                     options={},
                                     ):
        functions_to_be_checked = ("OpenDoc7",  # SolidWorks API: 2008 FCS (Rev 16.0)
                                   "CloseDoc",  # SolidWorks API: 2008 FCS (Rev 16.0)
                                   )

        # Also shall confirm the correct major revision from the running instance
        if not options:
            options = {"app_name": self.getVersionedServiceName(version),
                       }
        functions_found = True
        try:
            if "app_instance" not in options.keys():
                self.startApp(options)
            for func in functions_to_be_checked:
                try:
                    getattr(options["app_instance"], func)
                except Exception:
                    Logger.logException("e", "Error which occurred when checking for some functions")
                    functions_found = False
        except Exception:
            Logger.logException("e", "Starting the service and checking for some functions failed!")

        if "app_instance" in options.keys():
            if not keep_instance_running:
                self.closeApp(options)
                if not options["app_was_active"] and not self.getOpenDocuments(options):
                    Logger.log(
                        "d",
                        "Looks like we opened SolidWorks and there are no open files. Let's close SolidWorks again!"
                    )
                    # SolidWorks API: ?
                    options["app_instance"].ExitApp()
                self.postCloseApp(options)
        else:
            Logger.log("e", "Starting service failed!")
            return (False, options)

        if functions_found:
            return (True, options)
        else:
            Logger.log("e", "Could not find some functions!")
            return (False, options)

    def getRevisionNumber(self, options):
        # Getting revision after starting
        if self.preference_storage.getValue("ciu.debug"):
            return [EMULATE_VERSION_API, 0, 0]

        # SolidWorks API: ?
        revision_number = options["app_instance"].RevisionNumber
        if isinstance(revision_number, str):
            revision_number = [int(x) for x in revision_number.split(".")]
            try:
                options["version_major"] = revision_number[0]
                Logger.log("d", "Major version is: {}".format(options["version_major"]))
                options["version_minor"] = revision_number[1]
                Logger.log("d", "Minor version is: {}".format(options["version_minor"]))
                options["version_patch"] = revision_number[2]
                Logger.log("d", "Patch version is: {}".format(options["version_patch"]))
            except IndexError:
                Logger.logException(
                    "w",
                    "Unable to parse revision number from SolidWorks.RevisionNumber. revision_number is: {revision_number}.".format(  # noqa
                        revision_number=revision_number,
                    )
                )
            except Exception:
                Logger.logException("c", "Unexpected error: revision_number = {revision_number}".format(
                    revision_number=revision_number))
        else:
            Logger.log("c", "revision_number has a wrong type: {}".format(type(revision_number)))

        return revision_number


class SolidWorksReader(CommonCOMReader):
    def __init__(self):
        super().__init__()

        if Version(Application.getInstance().getVersion()) >= Version("3.4"):
            MimeTypeDatabase.addMimeType(MimeType(name="application/x-extension-sldprt",
                                                  comment="3DS SolidWorks part file",
                                                  suffixes=["sldprt"]
                                                  )
                                         )
            MimeTypeDatabase.addMimeType(MimeType(name="application/x-extension-sldasm",
                                                  comment="3DS SolidWorks assembly file",
                                                  suffixes=["sldasm"]
                                                  )
                                         )
            MimeTypeDatabase.addMimeType(MimeType(name="application/x-extension-slddrw",
                                                  comment="3DS SolidWorks drawing file",
                                                  suffixes=["slddrw"]
                                                  )
                                         )

        self._extension_part = ".SLDPRT"
        self._extension_assembly = ".SLDASM"
        self._extension_drawing = ".SLDDRW"
        self._supported_extensions = [self._extension_part.lower(),
                                      self._extension_assembly.lower(),
                                      self._extension_drawing.lower(),
                                      ]

        self.quality_classes = {
            30: "Fine (3D-printing)",
            20: "Coarse (3D-printing)",
            10: "Fine (SolidWorks)",
            0: "Coarse (SolidWorks)",
            -1: "Keep settings unchanged",
        }

        self.root_component = None

        # Results of the validation checks of each version
        self.operational_versions = []
        self.technical_infos_per_version = {}

    @property
    def _prefered_app_name(self):
        installation_code = self.preference_storage.getValue("preferred_installation")

        if installation_code is -1:
            return None  # We have no preference
        elif installation_code is -2:
            return self._default_app_name  # Use system default service
        elif installation_code in self.operational_versions:
            return self.getVersionedServiceName(installation_code)  # Use chosen version
        return None

    def preRead(self, options):
        super().preRead(options)

        Logger.log("d", "Showing wizard, if needed..")
        self.extension.wizard.showConfigUI(blocking=True)
        if self.extension.wizard.getCancelled():
            Logger.log("d", "User cancelled conversion of file!")
            return MeshReader.PreReadResult.cancelled
        Logger.log("d", "Continuing to convert file..")

        return MeshReader.PreReadResult.accepted

    def setAppVisible(self, state, options):
        # SolidWorks API: ?
        options["app_instance"].Visible = state

    def getAppVisible(self, state, options):
        # SolidWorks API: ?
        return options["app_instance"].Visible

    def preStartApp(self, options):
        options["app_export_quality"] = self.preference_storage.getValue("export_quality")
        options["app_auto_rotate"] = self.preference_storage.getValue("auto_rotate")

    def startApp(self, options):
        if self.preference_storage.getValue("ciu.debug"):
            options["tempFileKeep"] = True
        else:
            super().startApp(options)

            # Tell SolidWorks we operating in the background
            # SolidWorks API: 2006 SP2 (Rev 14.2)
            options["app_operate_in_background"] = options["app_instance"].CommandInProgress
            options["app_instance"].CommandInProgress = True

            # Allow SolidWorks to run in the background and be invisible
            # SolidWorks API: ?
            options["app_instance_user_control"] = options["app_instance"].UserControl
            options["app_instance"].UserControl = False

            # If the following property is true, then the SolidWorks frame will be visible
            # on a call to ISldWorks::ActivateDoc2; so set it to false
            # SolidWorks API: ?
            options["app_instance_visible"] = options["app_instance"].Visible
            options["app_instance"].Visible = False

            # Keep SolidWorks frame invisible when ISldWorks::ActivateDoc2 is called
            # SolidWorks API: ?
            options["app_frame"] = options["app_instance"].Frame
            options["app_frame_invisible"] = options["app_frame"].KeepInvisible
            options["app_frame"].KeepInvisible = True

        # Updating options["fileFormats"] depending on the started version
        revision = self.extension.getRevisionNumber(options)
        options["fileFormats"] = []  # Ordered list of preferred formats

        # WORKAROUND: DISABLING 3MF-USAGE. THE READER RETURNS A NODE, WHICH FAILS TO BE ROTATED.
        #             WHEN DOING A SIMPLE ROATATION IT BLOWS UP THE MEMORY!
        # TODO: Adding check whether all readers are available per format!
        if revision[0] >= 25:
            options["fileFormats"].append("3mf")
        options["fileFormats"].append("stl")

        version_name = self.extension.getServiceNameByVersion(revision[0])
        Logger.log("d", "Started: %s", version_name)

        return options

    def closeApp(self, options):
        if "app_frame" in options.keys():
            # Normally, we want to do that, but this confuses SolidWorks more than needed, it seems.
            Logger.log("d", "Rolling back changes on app_frame.")
            if "app_frame_invisible" in options.keys():
                options["app_frame"].KeepInvisible = options["app_frame_invisible"]

        if "app_instance" in options.keys():
            # Same here. By logic I would assume that we need to undo it,
            # but when processing multiple parts, SolidWorks gets confused again..
            # Or there is another sense..
            Logger.log("d", "Rolling back changes on app_instance.")
            if "app_instance_visible" in options.keys():
                # SolidWorks API: ?
                options["app_instance"].Visible = options["app_instance_visible"]
            if "app_instance_user_control" in options.keys():
                # SolidWorks API: ?
                options["app_instance"].UserControl = options["app_instance_user_control"]
            if "app_operate_in_background" in options.keys():
                # SolidWorks API: 2006 SP2 (Rev 14.2)
                options["app_instance"].CommandInProgress = options["app_operate_in_background"]
        Logger.log("d", "Closed SolidWorks.")

    def walkComponentsInAssembly(self, root=None):
        if root is None:
            root = self.root_component

        children = root.GetChildren

        if children:
            children = [self.walkComponentsInAssembly(child) for child in children]
            return root, children
        else:
            return root

        """
        models = options["sw_model"].GetComponents(True)

        for model in models:
            #Logger.log("d", model.GetModelDoc2())
            #Logger.log("d", repr(model.GetTitle))
            Logger.log("d", repr(model.GetPathName))
            #Logger.log("d", repr(model.GetType))
            if model.GetPathName in ComponentsCount.keys():
                ComponentsCount[model.GetPathName] = ComponentsCount[model.GetPathName] + 1
            else:
                ComponentsCount[model.GetPathName] = 1

        for key in ComponentsCount.keys():
            Logger.log("d", "Found %s %s-times in the assembly!" %(key, ComponentsCount[key]))
        """

    def getOpenDocuments(self, options):
        open_files = []
        # SolidWorks API: 98Plus
        open_file = options["app_instance"].GetFirstDocument
        while open_file:
            open_files.append(open_file)
            open_file = open_file.GetNext
        Logger.log("i", "Found {} open files..".format(len(open_files)))
        return open_files

    def getOpenDocumentPaths(self, options):
        paths = []
        for document in self.getOpenDocuments(options):
            paths.append(document.GetPathName)
        return paths

    def getOpenDocumentFilepathDict(self, options):
        """
        Returns a dictionary of filepaths and document objects

        - Apparently we can't get .GetDocuments working
        """

        open_files = self.getOpenDocuments(options)
        open_file_paths = {}
        for open_file in open_files:
            open_file_paths[os.path.normpath(open_file.GetPathName)] = open_file
            open_file = open_file.GetNext
        return open_file_paths

    def getDocumentTitleByFilepath(self, options, filepath):
        open_files = self.getOpenDocumentFilepathDict(options)
        for open_file_path in open_files.keys():
            if os.path.normpath(filepath) == open_file_path:
                Logger.log("i", "Found title '{}' for file <{}>".format(open_files[open_file_path].GetTitle,
                                                                        open_file_path)
                           )
                return open_files[open_file_path].GetTitle
        return None

    def getDocumentsInDrawing(self, options):
        referenceModelNames = []
        # SolidWorks API: ?
        swView = options["sw_model"].GetFirstView
        while swView is not None:
            if swView.GetReferencedModelName not in referenceModelNames and swView.GetReferencedModelName != "":
                referenceModelNames.append(swView.GetReferencedModelName)
            swView = swView.GetNextView
        return referenceModelNames

    def countDocumentsInDrawing(self, options):
        return len(self.getDocumentsInDrawing(options))

    def activatePreviousFile(self, options):
        if "sw_previous_active_file" in options.keys():
            if options["sw_previous_active_file"]:
                error = ComConnector.getByVarInt()
                # SolidWorks API: >= 20.0.x
                options["app_instance"].ActivateDoc3(options["sw_previous_active_file"].GetTitle,
                                                     True,
                                                     SolidWorksEnums.swRebuildOnActivation_e.swDontRebuildActiveDoc,
                                                     error
                                                     )
        return options

    def openForeignFile(self, options):
        if self.preference_storage.getValue("ciu.debug"):
            return options
        open_file_paths = self.getOpenDocumentPaths(options)

        # SolidWorks API: X
        options["sw_previous_active_file"] = options["app_instance"].ActiveDoc
        # If the file has not been loaded open it!
        if not os.path.normpath(options["foreignFile"]) in open_file_paths:
            Logger.log("d", "Opening the foreign file!")
            if options["foreignFormat"].upper() == self._extension_part:
                filetype = SolidWorksEnums.swDocumentTypes_e.swDocPART
            elif options["foreignFormat"].upper() == self._extension_assembly:
                filetype = SolidWorksEnums.swDocumentTypes_e.swDocASSEMBLY
            elif options["foreignFormat"].upper() == self._extension_drawing:
                filetype = SolidWorksEnums.swDocumentTypes_e.swDocDRAWING
            else:
                raise NotImplementedError("Unknown extension. Something went terribly wrong!")

            # SolidWorks API: 2008 FCS (Rev 16.0)
            documentSpecification = options["app_instance"].GetOpenDocSpec(options["foreignFile"])

            # NOTE: SPEC: FileName
            # documentSpecification.FileName

            # NOTE: SPEC: DocumentType
            # TODO: Really needed here?!
            documentSpecification.DocumentType = filetype

            # TODO: Test the impact of LightWeight = True
            # documentSpecification.LightWeight = True
            documentSpecification.Silent = True

            # TODO: Double check, whether file was really opened read-only..
            documentSpecification.ReadOnly = True

            documentSpecificationObject = ComConnector.GetComObject(documentSpecification)
            # SolidWorks API: 2008 FCS (Rev 16.0)
            options["sw_model"] = options["app_instance"].OpenDoc7(documentSpecificationObject)

            if documentSpecification.Warning:
                Logger.log("w", "Warnings happened while opening your SolidWorks file!")
            if documentSpecification.Error:
                Logger.log("e", "Errors happened while opening your SolidWorks file!")
                error_message = Message(i18n_catalog.i18nc(
                    "@info:status",
                    "SolidWorks reported errors while opening your file. We recommend to solve these issues inside SolidWorks itself."  # noqa
                    )
                )
                error_message.setTitle(__plugin_name__)
                error_message.show()
            options["sw_opened_file"] = True
        else:
            Logger.log("d", "Foreign file has already been opened!")
            options["sw_model"] = self.getOpenDocumentFilepathDict(options)[os.path.normpath(options["foreignFile"])]
            options["sw_opened_file"] = False

        if options["foreignFormat"].upper() == self._extension_drawing:
            count_of_documents = self.countDocumentsInDrawing(options)
            if count_of_documents == 0:
                error_message = Message(i18n_catalog.i18nc(
                    "@info:status",
                    "Found no models inside your drawing. Could you please check its content again and make sure one part or assembly is inside?\n\nThanks!"  # noqa
                    )
                )
                error_message.setTitle(__plugin_name__)
                error_message.show()
            elif count_of_documents > 1:
                error_message = Message(i18n_catalog.i18nc(
                    "@info:status",
                    "Found more than one part or assembly inside your drawing. We currently only support drawings with exactly one part or assembly inside.\n\nSorry!"  # noqa
                    )
                )
                error_message.setTitle(__plugin_name__)
                error_message.show()
            else:
                options["sw_drawing"] = options["sw_model"]
                options["sw_drawing_opened"] = options["sw_opened_file"]
                options["foreignFile"] = self.getDocumentsInDrawing(options)[0]
                options["foreignFormat"] = os.path.splitext(options["foreignFile"])[1]
                self.activatePreviousFile(options)

                options = self.openForeignFile(options)

        error = ComConnector.getByVarInt()
        # SolidWorks API: >= 20.0.x
        # SolidWorks API: 2001Plus FCS (Rev. 10.0) - GetTitle
        options["app_instance"].ActivateDoc3(options["sw_model"].GetTitle,
                                             True,
                                             SolidWorksEnums.swRebuildOnActivation_e.swDontRebuildActiveDoc,
                                             error,
                                             )

        # Might be useful in the future, but no need for this ATM
        # self.configuration = options["sw_model"].getActiveConfiguration
        # self.root_component = self.configuration.GetRootComponent

        # EXPERIMENTAL: Browse single parts in assembly
        # if filetype == SolidWorksEnums.FileTypes.SWassembly:
        #    Logger.log("d", 'walkComponentsInAssembly: ' + repr(self.walkComponentsInAssembly()))

        return options

    def exportFileAs(self, options, quality_enum=None):
        if self.preference_storage.getValue("ciu.debug"):
            _plugin_dir = os.path.split(__file__)[0]
            _test_file = os.path.join(_plugin_dir,
                                      "tests",
                                      "file_type_examples",
                                      "test_cube.{}".format(options["tempType"].lower())
                                      )
            if not os.path.isfile(_test_file):
                Logger.log("w", "Test file not found!")
            options["tempFile"] = _test_file
            Logger.log("w", "Overriding 'tempFile' with: {}".format(options["tempFile"]))
            return options

        # # Backing up everything
        if options["foreignFormat"].upper() == self._extension_assembly:
            # Backing up current setting of swSTLComponentsIntoOneFile
            # SolidWorks API: 2009 FCS (Rev 17.0)
            swSTLComponentsIntoOneFileBackup = options["app_instance"].GetUserPreferenceToggle(
                SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile)

        # Backing up quality settings
        # SolidWorks API: ?
        swExportSTLQualityBackup = options["app_instance"].GetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality)
        swExportSTLAngleToleranceBackup = options["app_instance"].GetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLAngleTolerance)
        swExportSTLDeviationBackup = options["app_instance"].GetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLDeviation)

        # Backing up the default unit for STLs to mm, which is expected by Cura
        # SolidWorks API: ?
        swExportStlUnitsBackup = options["app_instance"].GetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits)
        # Backing up the output type temporary to binary
        # SolidWorks API: 2009 FCS (Rev 17.0)
        swSTLBinaryFormatBackup = options["app_instance"].GetUserPreferenceToggle(
            SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat)

        # # Setting everything up
        # Export for assemblies
        if options["foreignFormat"].upper() == self._extension_assembly:
            # Setting up swSTLComponentsIntoOneFile
            # SolidWorks API: 2001 Plus FCS (Rev 10.0)
            options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile,
                                                            self.extension._convert_assembly_into_once)

        # Setting  quality
        # -2 := Custom (not supported yet!)
        # -1 := Keep settings unchanged
        #  0 := Coarse (as defined by SolidWorks)
        # 10 := Fine (as defined by SolidWorks)
        # 20 := Coarse (3D printing profile)
        # 30 := Fine (3D printing profile)

        if quality_enum is -1 or quality_enum < -1:
            Logger.log("i", "Using settings, which are currently set in SolidWorks!")
        elif quality_enum in range(0, 10):
            Logger.log("i", "Using SolidWorks' coarse quality!")
            # Give actual value for quality
            # SolidWorks API: ?
            options["app_instance"].SetUserPreferenceIntegerValue(
                SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                SolidWorksEnums.swSTLQuality_e.swSTLQuality_Coarse
            )
        elif quality_enum in range(10, 20):
            Logger.log("i", "Using SolidWorks' fine quality!")
            # Give actual value for quality
            # SolidWorks API: ?
            options["app_instance"].SetUserPreferenceIntegerValue(
                SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                SolidWorksEnums.swSTLQuality_e.swSTLQuality_Fine
            )
        elif quality_enum in range(20, 30):
            Logger.log("i", "Using coarse quality for 3D printing!")
            # Give actual value for quality
            options["app_instance"].SetUserPreferenceIntegerValue(
                SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                SolidWorksEnums.swSTLQuality_e.swSTLQuality_Custom
            )
            options["app_instance"].SetUserPreferenceIntegerValue(
                SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLAngleTolerance,
                5.0
            )
            options["app_instance"].SetUserPreferenceIntegerValue(
                SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLDeviation,
                0.4
            )
        elif quality_enum >= 30:
            Logger.log("i", "Using fine quality for 3D printing!")
            # Give actual value for quality
            options["app_instance"].SetUserPreferenceIntegerValue(
                SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                SolidWorksEnums.swSTLQuality_e.swSTLQuality_Custom
            )
            options["app_instance"].SetUserPreferenceIntegerValue(
                SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLAngleTolerance,
                1.0
            )
            options["app_instance"].SetUserPreferenceIntegerValue(
                SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLDeviation,
                0.1
            )
        else:
            Logger.log("e", "Invalid value for quality: {}".format(repr(quality_enum)))

        # Changing the default unit for STLs to mm, which is expected by Cura
        # SolidWorks API: ?
        options["app_instance"].SetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits,
            SolidWorksEnums.swLengthUnit_e.swMM
        )

        # Changing the output type temporary to binary
        # SolidWorks API: 2001 Plus FCS (Rev 10.0)
        options["app_instance"].SetUserPreferenceToggle(
            SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat,
            True
        )

        options["sw_model"].SaveAs(options["tempFile"])

        # Restoring swSTLBinaryFormat
        # SolidWorks API: 2001 Plus FCS (Rev 10.0)
        options["app_instance"].SetUserPreferenceToggle(
            SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat,
            swSTLBinaryFormatBackup
        )

        # Restoring swExportStlUnits
        # SolidWorks API: ?
        options["app_instance"].SetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits,
            swExportStlUnitsBackup
        )

        # Restoring swSTL*
        options["app_instance"].SetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLAngleTolerance,
            swExportSTLAngleToleranceBackup
        )
        options["app_instance"].SetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLDeviation,
            swExportSTLDeviationBackup
        )
        # SolidWorks API: ?
        options["app_instance"].SetUserPreferenceIntegerValue(
            SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
            swExportSTLQualityBackup
        )

        if options["foreignFormat"].upper() == self._extension_assembly:
            # Restoring swSTLComponentsIntoOneFile
            # SolidWorks API: 2001 Plus FCS (Rev 10.0)
            options["app_instance"].SetUserPreferenceToggle(
                SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile,
                swSTLComponentsIntoOneFileBackup
            )

        return options

    def closeForeignFile(self, options):
        if "app_instance" in options.keys():
            if "sw_opened_file" in options.keys():
                if options["sw_opened_file"]:
                    # SolidWorks API: ?
                    # SolidWorks API: 2001Plus FCS (Rev. 10.0) - GetTitle
                    options["app_instance"].CloseDoc(options["sw_model"].GetTitle)
            if "sw_drawing_opened" in options.keys():
                if options["sw_drawing_opened"]:
                    # SolidWorks API: ?
                    options["app_instance"].CloseDoc(options["sw_drawing"].GetTitle)
            self.activatePreviousFile(options)

    def nodePostProcessing(self, options, scene_nodes, revision=None):
        Logger.log("d", "Doing postprocessing on: {}".format(repr(scene_nodes)))
        super().nodePostProcessing(options, scene_nodes)
        # # Auto-rotation
        if options["app_auto_rotate"]:
            if options["tempType"] == "stl":
                Logger.log("d", "Doing auto-rotation..")
                # Known problem under SolidWorks 2016 until 2018:
                # Exported models are rotated by -90 degrees. This rotates them back!
                rotation = Quaternion.fromAngleAxis(math.radians(90), Vector.Unit_X)
                zero_translation = Matrix(data=numpy.zeros(3, dtype=numpy.float64))
                for scene_node in scene_nodes:
                    if not scene_node.hasChildren():
                        scene_node.rotate(rotation)
                        mesh_data = scene_node.getMeshData()
                        transformation_matrix = scene_node.getLocalTransformation()
                        transformation_matrix.setTranslation(zero_translation)
                        scene_node.setMeshData(mesh_data.getTransformed(transformation_matrix))
                    else:
                        Logger.log("d", "Passing children: {}".format(repr(scene_node.getChildren())))
                        self.nodePostProcessing(options, scene_node.getChildren(), revision=revision)
                return scene_nodes
            elif options["tempType"] == "3mf":
                for scene_node in scene_nodes:
                    zero_translation = Matrix()
                    scene_node.setTransformation(zero_translation)
                return scene_nodes
        return scene_nodes
