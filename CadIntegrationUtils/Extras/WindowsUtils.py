# Copyright (c) 2019 Thomas Karl Pietrowski

import winreg


class RegistryTools(object):
    def getServicesFromRegistry(self, service_family):
        versions = []
        registered_services = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, None)
        key_prefix = "{}.".format(service_family)
        i = 0
        while True:
            try:
                key = winreg.EnumKey(registered_services, i)
                if key.startswith(key_prefix):
                    try:
                        # Testing whether the suffix is an integer or not!
                        int(key[len(key_prefix):])
                        versions.append(key)
                    except ValueError:
                        pass
                i += 1
            except WindowsError:
                break

        # Sorting all results and making the latest version the most recent one (top of list)
        versions.sort()
        versions.reverse()
        return versions

    def getEnumOfVersionedServiceID(self, service_family, service_id):
        return int(service_id[len("{}.".format(service_family)):])

    def isCLSID(clsid):
        return

    def getCLSID(id):
        return


class Service(object):
    def __init__(self, id):
        self.__regtools = RegistryTools()
        self.id = id

    @property
    def CLSID(self):
        return self.__regtools.getCLSID(self.id)
