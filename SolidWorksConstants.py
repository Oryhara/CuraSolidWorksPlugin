# Copyright (c) 2019 Thomas Karl Pietrowski


class SolidWorkVersions:
    major_version_name = {16: "SolidWorks 2008",
                          17: "SolidWorks 2009",
                          18: "SolidWorks 2010",
                          19: "SolidWorks 2011",
                          20: "SolidWorks 2012",
                          21: "SolidWorks 2013",
                          22: "SolidWorks 2014",
                          23: "SolidWorks 2015",
                          24: "SolidWorks 2016",
                          25: "SolidWorks 2017",
                          26: "SolidWorks 2018",
                          27: "SolidWorks 2019",
                          }


class SolidWorksEnums:
    class swRebuildOnActivation_e:
        swUserDecision = 0
        swDontRebuildActiveDoc = 1
        swRebuildActiveDoc = 2

    class swUserPreferenceToggle_e:
        swSTLBinaryFormat = 69

    class swDocumentTypes_e:
        swDocNONE = 0
        swDocPART = 1
        swDocASSEMBLY = 2
        swDocDRAWING = 3

    swSTLQuality = 78

    class swLengthUnit_e:
        swMM = 0
        swCM = 1
        swMETER = 2
        swINCHES = 3
        swFEET = 4
        swFEETINCHES = 5
        swANGSTROM = 6
        swNANOMETER = 7
        swMICRON = 8
        swMIL = 9
        swUIN = 10

    class swUserPreferenceIntegerValue_e:
        swExportSTLQuality = 78
        swExportStlUnits = 211

    class swUserPreferenceDoubleValue_e:
        swSTLDeviation = 2
        swSTLAngleTolerance = 3

    class swSTLQuality_e:
        swSTLQuality_Coarse = 1
        swSTLQuality_Fine = 2
        swSTLQuality_Custom = 3

    class UserPreferences:
        swSTLComponentsIntoOneFile = 72
