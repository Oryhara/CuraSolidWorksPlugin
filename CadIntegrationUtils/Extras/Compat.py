from UM.Application import Application  # @UnresolvedImport
from UM.Version import Version  # @UnresolvedImport

if not Version("3.3") <= Version(Application.getInstance().getVersion()):
    from UM.Preferences import Preferences  # @UnresolvedImport


class Deprecations:
    def getPreferences():
        if Version("3.3") <= Version(Application.getInstance().getVersion()):
            return Application.getInstance().getPreferences()
        else:
            return Preferences.getInstance()


class ApplicationCompat(object):
    @property
    def qml_engine(self):
        if Version(Application.getInstance().getVersion()) >= Version("3.3"):
            return Application.getInstance()._qml_engine
        else:
            return Application.getInstance()._engine

    @property
    def pluginsLoaded(self):
        app_instance = Application.getInstance()
        if "pluginsLoaded" in dir(app_instance):
            return app_instance.pluginsLoaded
        elif "engineCreatedSignal" in dir(app_instance):
            return app_instance.engineCreatedSignal
        else:
            return None
