# Copyright (C) 2019 Thomas Karl Pietrowski

# Comtypes modules
import comtypes  # @UnusedImport # @UnresolvedImport
import comtypes.client  # @UnresolvedImport
import ctypes


class ComConnector:
    def getByVarInt():
        return ctypes.byref(ctypes.c_int())

    def CreateClassObject(app_name):
        return comtypes.client.GetClassObject(app_name).CreateInstance()

    def CreateActiveObject(app_name):
        return comtypes.client.GetActiveObject(app_name).CreateInstance()

    def CoInit():
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)

    def UnCoInit():
        comtypes.CoUninitialize()

    def GetComObject(toBeObjected):
        return toBeObjected._comobj

    @property
    def IntByRef(self):
        int_value = ctypes.c_int()
        return ctypes.byref(int_value)
