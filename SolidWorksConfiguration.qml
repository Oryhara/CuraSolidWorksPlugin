// Copyright (c) 2017 Ultimaker B.V.
// Copyright (c) 2019 Thomas Karl Pietrowski

import QtQuick 2.1
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.1 as UM

UM.Dialog
{
    width: Math.floor(screenScaleFactor * 365);
    minimumWidth: width;
    maximumWidth: width;

    height: Math.floor(screenScaleFactor * 180);
    minimumHeight: height;
    maximumHeight: height;

    title: catalog.i18nc("@title:window", "SolidWorks plugin: Configuration")

    onVisibilityChanged:
    {
        if (visible)
        {
            qualityDropdown.updateCurrentIndex();
            installationsDropdown.updateCurrentIndex();
            showWizardCheckBox.checked = manager.getBoolValue("show_export_settings_always");
            autoRotateCheckBox.checked = manager.getBoolValue("auto_rotate");
        }
    }

    GridLayout
    {
        anchors.fill: parent
        UM.I18nCatalog{id: catalog; name: "SolidWorksPlugin"}

        columns: 1

        property Item showWizard: showWizardCheckBox
        property Item autoRotateCheckBox: autoRotateCheckBox
        property Item qualityDropdown: qualityDropdown
        //property Item choiceModel: choiceModel
        property Item installationsDropdown: installationsDropdown

        Row {
            width: parent.width

            Label {
                text: catalog.i18nc("@label", "First choice:");
                width: 100 * screenScaleFactor
                anchors.verticalCenter: parent.verticalCenter
            }

            ComboBox
            {
                id: installationsDropdown
                currentIndex: 0
                width: 240 * screenScaleFactor

                //style: UM.Theme.styles.combobox_color

                function ensureListWithEntries()
                {
                    var versions = manager.getVersionsList();
                    var version = 0;
                    var operational = true;
                    model.clear();

                    model.append({ text: catalog.i18nc("@text:menu", "Latest installed version (Recommended)"), code: -1 });
                    for(var i = 0; i < versions.length; ++i)
                    {
                        version = versions[i];
                        operational = manager.isVersionOperational(version);
                        if (operational) {
                            model.append({ text: manager.getFriendlyName(version), code: version });
                        }
                    }
                    model.append({ text: catalog.i18nc("@text:menu", "Default version"), code: -2 });
                    updateCurrentIndex()
                }

                function updateCurrentIndex()
                {
                    var index = 0; // Top element in the list below by default
                    var currentSetting = manager.getIntValue("preferred_installation");
                    for (var i = 0; i < model.count; ++i)
                    {
                        if (model.get(i).code == currentSetting)
                        {
                            index = i;
                            break;
                        }
                    }
                    currentIndex = index;
                }

                Component.onCompleted: {
                    ensureListWithEntries();
                }

                function saveInstallationCode()
                {
                    var code = model.get(currentIndex).code;
                    manager.setIntValue("preferred_installation", code);
                }

                model: ListModel
                {
                    id: installationsModel

                    Component.onCompleted:
                    {
                        append({ text: "NONE", code: -3 });
                    }
                }
            }
        }
        Row
        {
            width: parent.width

            Label {
                text: catalog.i18nc("@action:label", "Quality:")
                width: 100 * screenScaleFactor
                anchors.verticalCenter: parent.verticalCenter
            }

            ComboBox
            {
                id: qualityDropdown

                currentIndex: updateCurrentIndex()
                width: 240 * screenScaleFactor

                function updateCurrentIndex()
                {
                    var index = 0; // Top element in the list below by default
                    var currentChoice = manager.getIntValue("export_quality");
                    for (var i = 0; i < model.count; ++i)
                    {
                        if (model.get(i).code == currentChoice)
                        {
                            index = i;
                            break;
                        }
                    }
                    currentIndex = index;
                }

                function saveQualityCode()
                {
                    var code = model.get(currentIndex).code;
                    manager.setIntValue("export_quality", code);
                }

                model: ListModel
                {
                    id: choiceModel

                    Component.onCompleted:
                    {
                        append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Fine (3D-printing)"), code: 30 });
                        append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Coarse (3D-printing)"), code: 20 });
                        append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Fine (SolidWorks)"), code: 10 });
                        append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Coarse (SolidWorks)"), code: 0 });
                        append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Keep settings unchanged"), code: -1 });
                    }
                }
            }
        }
        Row
        {
            width: parent.width
            CheckBox
            {
                id: showWizardCheckBox
                text: catalog.i18nc("@label", "Show wizard before opening SolidWorks files");
                checked: manager.getBoolValue("show_export_settings_always");
            }
        }
        Row
        {
            width: parent.width
            CheckBox
            {
                id: autoRotateCheckBox
                text: catalog.i18nc("@label", "Automatically rotate opened file into normed orientation");
                checked: manager.getBoolValue("auto_rotate");
            }
        }
    }

    rightButtons: [
        Button
        {
            id: ok_button
            text: catalog.i18nc("@action:button", "Save")
            onClicked:
            {
                qualityDropdown.saveQualityCode();
                installationsDropdown.saveInstallationCode();
                manager.setBoolValue("show_export_settings_always", showWizardCheckBox.checked);
                manager.setBoolValue("auto_rotate", autoRotateCheckBox.checked);
                close();
            }
            enabled: true
        },
        Button
        {
            id: cancel_button
            text: catalog.i18nc("@action:button", "Cancel")
            onClicked:
            {
                close();
            }
            enabled: true
        }
    ]
}
