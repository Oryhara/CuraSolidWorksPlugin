# Copyright (C) 2019 Thomas Karl Pietrowski

# Uranium/Cura
from UM.Logger import Logger  # @UnresolvedImport
from UM.i18n import i18nCatalog  # @UnresolvedImport

# Ensure first all imports from common are done
# # A movement somewhere below these lines might mix up PyWin32 with Comtypes
from .CommonReader import CommonExtension, CommonReader, OptionKeywords
from .ComFactory import ComConnector

# CIU
from .Windows.ServiceChecker import ComServiceChecker

i18n_catalog = i18nCatalog("CuraSolidWorksPlugin")


class CommonCOMExtension(CommonExtension):
    def __init__(self,
                 name,
                 id,
                 reader,
                 default_com_service_name,
                 default_com_service_id,
                 ):
        super().__init__(name,
                         id,
                         reader,
                         )

        # COM related variables
        self._com_service_ids_and_names = {}
        self._default_com_service_id = default_com_service_id
        self._default_com_service_name = default_com_service_name

        # TODO:
        # After having common tools make a quick check and remove when needed.
        self.prepareComServices()
        self.com_service_checker = ComServiceChecker(self)
        self.reader.applications = self.com_service_checker.operational_services

    def prepareMenu(self):
        self.setMenuName(self._name)

    def prepareComServices(self):
        self.add_com_service(self._default_com_service_id, self._default_com_service_name)

    @property
    def com_service_ids(self):
        return self._com_service_ids_and_names.keys()

    @property
    def com_service_ids_and_names(self):
        return self._com_service_ids_and_names

    def add_com_service(self, id, name):
        self._com_service_ids_and_names[id] = name

    def purge_com_services(self):
        self._com_service_ids_and_names = {}


class CommonCOMReader(CommonReader):
    def __init__(self):
        CommonReader.__init__(self)
        self.extension = None

    @property
    def preference_storage(self):
        return self.extension.preference_storage

    def startApp(self, options):
        Logger.log("d", "Calling %s...", options["app_name"])

        Logger.log("d", "CreateActiveObject..")
        options["app_was_active"] = True
        try:
            options["app_started_with_coinit"] = False
            options["app_instance"] = ComConnector.CreateActiveObject(options["app_name"])
            return options
        except Exception:
            Logger.logException("d", "Getting active object without Coinit failed")

        try:
            Logger.log("d", "CoInit..")
            ComConnector.CoInit()
            options["app_started_with_coinit"] = True
            options["app_instance"] = ComConnector.CreateActiveObject(options["app_name"])
            return options
        except Exception:
            Logger.logException("d", "Getting active object with Coinit failed")

        if options["app_started_with_coinit"]:
            Logger.log("d", "UnCoInit..")
            ComConnector.UnCoInit()

        Logger.log("d", "Trying to get new class object..")
        options["app_was_active"] = False
        try:

            options["app_started_with_coinit"] = False
            options["app_instance"] = ComConnector.CreateClassObject(options["app_name"])
            return options
        except Exception:
            Logger.logException("d", "Getting object without Coinit failed")

        try:
            Logger.log("d", "CoInit..")
            ComConnector.CoInit()
            options["app_started_with_coinit"] = True
            options["app_instance"] = ComConnector.CreateClassObject(options["app_name"])
            return options
        except Exception:
            Logger.logException("d", "Getting object with Coinit failed")

        raise Exception("Could not start service!")

    def postCloseApp(self, options):
        Logger.log("d", "postCloseApp..")
        if "app_started_with_coinit" in options.keys():
            if options["app_started_with_coinit"]:
                Logger.log("d", "UnCoInit..")
                ComConnector.UnCoInit()

    def read(self, file_path):
        options = self.readCommon(file_path)
        result = self.readOnMultipleAppLayer(options)

        # Unlock if needed
        if not self._parallel_execution_allowed:
            self.conversion_lock.release()

        return result
