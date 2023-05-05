# Copyright (c) 2019 Thomas Karl Pietrowski

__plugin_name__ = "3DS SolidWorks plugin"
__plugin_id__ = "CuraSolidWorksPlugin"

# built-ins
import os

# Uranium
from UM.Message import Message  # @UnresolvedImport
from UM.Platform import Platform  # @UnresolvedImport
from UM.i18n import i18nCatalog  # @UnresolvedImport

i18n_catalog = i18nCatalog(__plugin_id__)

if Platform.isWindows():
    # For installation check
    import winreg
    # The reader plugin itself
    from . import SolidWorksReader  # @UnresolvedImport


def getMetaData():
    metaData = {"mesh_reader": [{
        "extension": "SLDPRT",
        "description": i18n_catalog.i18nc("@item:inlistbox", "3DS SolidWorks part file")
    },
        {
        "extension": "SLDASM",
        "description": i18n_catalog.i18nc("@item:inlistbox", "3DS SolidWorks assembly file")
    },
        {
        "extension": "SLDDRW",
        "description": i18n_catalog.i18nc("@item:inlistbox", "3DS SolidWorks drawing file")
    },
    ]
    }

    return metaData


def register(app):
    plugin_data = {}
    if Platform.isWindows():
        reader = SolidWorksReader.SolidWorksReader()
        extension = SolidWorksReader.SolidWorksExtension(__plugin_name__,
                                                         __plugin_id__,
                                                         reader,
                                                         "3DS SolidWorks",
                                                         "SldWorks.Application",
                                                         )
        plugin_data["mesh_reader"] = reader
        plugin_data["extension"] = extension
    else:
        not_correct_os_message = Message(i18n_catalog.i18nc("@info:status",
                                                            "Dear customer,\nYou are currently running this plugin on an operating system other than Windows. This plugin will only work on Windows with 3DS SolidWorks installed, including an valid license. Please install this plugin on a Windows machine with 3DS SolidWorks installed.\n\nWith kind regards\n - Thomas Karl Pietrowski"  # noqa
                                                            ),
                                         0)
        not_correct_os_message.setTitle("SolidWorks plugin")
        not_correct_os_message.show()

    return plugin_data
