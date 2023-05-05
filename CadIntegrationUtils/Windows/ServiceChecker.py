# Copyright (c) 2019 Thomas Karl Pietrowski

import os
import winreg

# PyQt/Qt
from PyQt6.QtCore import QObject, QUrl, pyqtSlot
from PyQt6.QtQml import QQmlComponent, QQmlContext

# Uranium/Cura
from UM.i18n import i18nCatalog  # @UnresolvedImport
from UM.Extension import Extension  # @UnresolvedImport
from UM.Logger import Logger  # @UnresolvedImport
from UM.Message import Message  # @UnresolvedImport

# CIU
from ..Extras.Compat import ApplicationCompat
from ..Extras.SystemUtils import Filesystem

i18n_catalog = i18nCatalog("CadIntegrationUtils")


class ComServiceCheckerCore():
    "All functions, which are not UI related."

    def __init__(self, extension):
        self.extension = extension
        self._checks_done = False
        self._operational_services = []
        self.technical_infos_per_service = {}

        # Doing some routines after all plugins are loaded
        ApplicationCompat().pluginsLoaded.connect(self._onAfterPluginsLoaded)

    def _onAfterPluginsLoaded(self):
        self.preference_storage.addPreference("ciu.com.service_checks_at_startup", True)
        self.preference_storage.addPreference("ciu.com.emulate_service_version", 0)

        if not self._checks_done and self.preference_storage.getValue("ciu.com.service_checks_at_startup"):
            self.checkAllComServices()

    @property
    def preference_storage(self):
        return self.extension.preference_storage

    @property
    def services(self):
        if self.preference_storage.getValue("ciu.debug"):
            if self.preference_storage.getValue("ciu.com.emulate_service_version") not in self._operational_services:
                if self.preference_storage.getValue("ciu.com.emulate_service_version"):
                    dummy_service_id = "{}.{}".format(self.extension._default_service_name,
                                                      self.preference_storage.getValue(
                                                          "ciu.com.emulate_service_version"),
                                                      )
                return [dummy_service_id, ]

        return self.extension.com_service_ids

    @property
    def operational_services(self):
        if not self._checks_done:
            self.checkAllComServices()
        return self._operational_services

    def hasOperationalServices(self):
        return bool(self.operational_services)

    def isServiceRegistered(self, service_id):
        """
        Tests whether a service is registered in the registry.
        Every service ID must be assigned to an class ID.
        """
        try:
            winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                           service_id,
                           0,
                           winreg.KEY_READ,
                           )

            winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                              "{}\\CLSID".format(service_id),
                              )
            return True
        except Exception:
            return False

    def resolveWindowsService(self, service_id):
        """
        Resolves common service ids to api specific services.
        For example:
            Inventor.Application -> Inventor.Application.1
        """
        if not self.isServiceRegistered(service_id):
            return None

        try:
            registry_entry = "{}\\CurVer".format(service_id)
            service_id = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                                           registry_entry,
                                           )

        except Exception:
            try:
                class_id = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                                             "{}\\CLSID".format(service_id),
                                             )
                registry_entry = "CLSID\\{}\\ProgID".format(class_id)
                service_progid = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                                                   registry_entry,
                                                   )
            except Exception:
                # The CLSID must have a ProgID key!
                return None

            if not service_id == service_progid:
                # The ProgID must correspong to service_id after end of resolving
                return None

            return service_id

        return self.resolveWindowsService(service_id)

    def getCommandOfWindowsService(self, service_id):
        service_id = self.resolveWindowsService(service_id)
        registry_entry = "{}\\CLSID".format(service_id)
        clsid = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                                  registry_entry,
                                  )
        registry_entry = "CLSID\\{}\\LocalServer32".format(clsid)
        service_start_command = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                                                  registry_entry,
                                                  )
        Logger.log("d", "Automation command: {}".format(repr(service_start_command))
                   )
        return service_start_command

    def getPathToExecutable(self, service_id):
        open_command = self.getCommandOfWindowsService(service_id)
        return Filesystem.getExecutableInCommand(open_command)

    def isPathToExecutable(self, service_id):
        open_command = self.getCommandOfWindowsService(service_id)
        return Filesystem.isExecutableInCommand(open_command)

    def isServiceExecutableFound(self, service_id):
        # Also check whether the executable can be found..
        # Why? - SolidWorks 2017 lefts an key after uninstallation,
        # which points to an orphaned path.
        try:
            if not self.isPathToExecutable(service_id):
                Logger.log("e", "Could not find executable!")
                return False
        except Exception:
            Logger.logException("e", "Could not determine executable path of service")
            return False

        Logger.log("d", "Found the service's executable")
        return True

    def startupService(self, service_id, options={}):
        if not options:
            options = {"app_name": service_id,
                       }
        try:
            if "app_instance" not in options.keys():
                self.extension.reader.startApp(options)
        except Exception:
            Logger.logException("e", "Starting the service and getting the major revision number failed!")

        return (True, options)

    def shutdownService(self, options):
        if "app_instance" in options.keys():
            self.extension.reader.closeApp(options)
            self.extension.reader.postCloseApp(options)
        else:
            Logger.log("e", "Starting service failed!")
            return (False, options)

    def isServiceStartingUp(self,
                            service_id,
                            keep_instance_running=False,
                            options={}):
        service_id = self.resolveWindowsService(service_id)

        result = self.startupService(service_id, options)

        if not keep_instance_running:
            self.shutdownService(options)

        return result

    def doBasicChecks(self,
                      service_id,
                      keep_instance_running=False,
                      options={},
                      ):
        # Needs to be overwritten with service specific checks

        if not keep_instance_running:
            self.shutdownService(options)

        return (True, options)

    def doAdvancedChecks(self,
                         service_id,
                         keep_instance_running=False,
                         options={},
                         ):
        # Needs to be overwritten with service specific checks

        if not keep_instance_running:
            self.shutdownService(options)

        return (True, options)

    def isComServiceOperational(self, service_id):
        Logger.log("i", "CIU: Testing COM service {}!".format(repr(service_id)))
        info_dict = {"registered": False,
                     "executable": False,
                     "starting": False,
                     "basic_checks": False,
                     "advanced_checks": False,
                     }
        if self.preference_storage.getValue("ciu.debug"):
            # TODO: GENERATE SERVICE NAME
            if self.preference_storage.getValue("ciu.com.emulate_service_version") is service_id:
                Logger.log("d", "DEBUG: Passing all tests!")
                for key in info_dict.keys():
                    info_dict[key] = True
                return (True, info_dict)

        # Checking whether the service is registered
        if not self.isServiceRegistered(service_id):
            Logger.log("w", "Found no COM service!".format(service_id))
            return (False, info_dict)
        info_dict["registered"] = True

        if not self.isServiceExecutableFound(service_id):
            Logger.log("w", "Found no executable for the service!")
            return (False, info_dict)
        info_dict["executable"] = True

        result, options = self.isServiceStartingUp(service_id,
                                                   keep_instance_running=True,
                                                   )
        if not result:
            Logger.log("w", "Could not start COM service!")
            return (False, info_dict)
        info_dict["starting"] = True

        result, options = self.doBasicChecks(service_id,
                                             keep_instance_running=True,
                                             options=options,
                                             )
        if not result:
            Logger.log("w", "Service does not do basic confirmations!.")
            return (False, info_dict)
        info_dict["basic_checks"] = True

        result, options = self.doAdvancedChecks(service_id,
                                                options=options,
                                                )
        if not result:
            Logger.log("w", "Can't find some basic functions to control '{}'!")
            return (False, info_dict)
        info_dict["advanced_checks"] = True

        Logger.log("i", "Success! The service seems to be valid!")
        return (True, info_dict)

    def checkAllComServices(self, skip_all_tests=False):
        Logger.log("i", "Checking all COM services...")
        self._operational_services = []
        self.technical_infos_per_service = {}
        for service in self.services:
            if skip_all_tests or self.preference_storage.getValue("ciu.debug"):
                self._operational_services.append(service)
                if self.preference_storage.getValue("ciu.debug"):
                    self.technical_infos_per_service[service] = self.isComServiceOperational(service)[1]
                continue
            result, info = self.isComServiceOperational(service)
            self.technical_infos_per_service[service] = info
            if result:
                self._operational_services.append(service)
        self._checks_done = True
        Logger.log("i", "All checks done!")


class DialogHelper(QObject):
    @pyqtSlot(str, result=bool)
    def getPreferenceAsBool(self, name):
        return self.preference_storage.getValue(name, forced_type=bool)

    @pyqtSlot(str, bool)
    def setPreferenceAsBool(self, name, value):
        return self.preference_storage.setValue(name, value, forced_type=bool)

    @pyqtSlot(str, result=int)
    def getPreferenceAsIntValue(self, name):
        return self.preference_storage.setValue(name, forced_type=int)

    @pyqtSlot(str, int)
    def getPreferenceAsIntValue(self, name, value):
        return self.preference_storage.setValue(name, value, forced_type=int)

    @pyqtSlot(str, result=float)
    def getPreferenceAsFloat(self, name):
        return self.preference_storage.getValue(name, forced_type=float)

    @pyqtSlot(str, float)
    def setPreferenceAsFloat(self, name, value):
        return self.preference_storage.getValue(name, value, forced_type=float)

    @pyqtSlot(str, result=bool)
    def isServiceOperational(self, service_id):
        return service_id in self.operational_services


class ComServiceChecker(ComServiceCheckerCore, QObject):
    "All core functionality plus UX"

    qml_directory = os.path.dirname(os.path.abspath(__file__))
    qml_file = os.path.join(qml_directory, "ServiceChecker.qml")

    def __init__(self, extension):
        QObject.__init__(self)
        ComServiceCheckerCore.__init__(self, extension)

        Logger.log("d", "Adding ServiceChecker to the menu!")
        self.qml_dialog = None
        extension.addMenuItem("CIU: Service checker",
                              self._openQmlDialog,
                              )

        missing_services_message = "Dear customer,\n\nThe plugin could not find the required software on your computer or there is something wrong with your installation..\n\nWith kind regards\n - Thomas Karl Pietrowski"  # noqa
        self._missing_services_notification = Message(i18n_catalog.i18nc("@info:status",
                                                                         missing_services_message,
                                                                         ),
                                                      0)
        self._missing_services_notification.setTitle(self.extension._menu_name)
        self._missing_services_notification.addAction("more_details",
                                                      i18n_catalog.i18nc("@action:button", "More details"),
                                                      "[no_icon]",
                                                      "[no_description]",
                                                      button_style=Message.ActionButtonStyle.DEFAULT,
                                                      button_align=Message.ActionButtonAlignment.ALIGN_RIGHT,
                                                      )
        self._missing_services_notification.actionTriggered.connect(self._missing_services_callback)

    def _missing_services_callback(self, message, action):
        if action == "more_details":
            self._openQmlDialog()
            self._missing_services_notification.hide()

    def _createDialog(self, dialog_qml):
        dialog_qml = QUrl.fromLocalFile(dialog_qml)
        component = QQmlComponent(ApplicationCompat().qml_engine, dialog_qml)

        # We need access to engine (although technically we can't)
        context = QQmlContext(ApplicationCompat().qml_engine.rootContext())
        context.setContextProperty("manager", self)
        dialog = component.create(context)
        if dialog is None:
            Logger.log("e", "QQmlComponent status: {}". format(component.status()))
            Logger.log("e", "QQmlComponent errorString: {}".format(component.errorString()))
        return dialog, context, component

    def _openQmlDialog(self):
        if not self.qml_dialog:
            self.qml_dialog, self.qml_context, self.qml_component = self._createDialog(self.qml_file)
        self.qml_dialog.show()

    def _onAfterPluginsLoaded(self):
        super()._onAfterPluginsLoaded()
        if not self.hasOperationalServices():
            self._missing_services_notification.show()

    @pyqtSlot(str, str, result=bool)
    def getTechnicalInfoOfService(self, service_id, property):
        return bool(self.technical_infos_per_service[service_id][property])

    @pyqtSlot(result=list)
    def getServiceList(self):
        versions = list(self.technical_infos_per_service.keys())
        versions.sort()
        versions.reverse()
        return versions

    @pyqtSlot(str, result=str)
    def getServiceName(self, service_id):
        if service_id in self.extension.com_service_ids_and_names.keys():
            return self.extension.com_service_ids_and_names[service_id]
        else:
            # The service's name must be known.
            # However, adding this step just in case.
            return "Unknown service name ({})".format(service_id)
