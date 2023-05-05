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

    height: Math.floor(screenScaleFactor * 250);
    minimumHeight: height;
    maximumHeight: height;

    title: catalog.i18nc("@title:window", "CIU: Service checker")

    GridLayout
    {
        anchors.fill: parent
        columnSpacing: 16 * screenScaleFactor
        rowSpacing: 10 * screenScaleFactor
        columns: 1

        property Item installationCheckDropdown: installationCheckDropdown

        UM.I18nCatalog{id: catalog; name: "CadIntegrationUtils"}

        Row {
            width: parent.width

            ComboBox
            {
                id: installationCheckDropdown
                currentIndex: 0
                width: parent.width
                editable: false

                function ensureListWithEntries()
                {
                    var services = manager.getServiceList();
                    model.clear();

                    if(services.length >= 1)
                    {
                        var service = "";
                        for(var i = 0; i < services.length; ++i)
                        {
                            service = services[i];
                            model.append({ text: manager.getServiceName(service), service: service });
                        }
                    } else {
                        model.append({ text: "- No service found -", service: "" });
                    }
                    currentIndex = 0;
                    updateCheckBoxes(model.get(currentIndex).service);
                }

                function updateCheckBoxes(service)
                {
                    if(service.length > 0)
                    {
                        checkCOMFound.checked = manager.getTechnicalInfoOfService(service, "registered");
                        checkExecutableFound.checked = manager.getTechnicalInfoOfService(service, "executable");
                        checkCOMStarting.checked = manager.getTechnicalInfoOfService(service, "starting");
                        checkRevisionVerified.checked = manager.getTechnicalInfoOfService(service, "basic_checks");
                        checkFunctions.checked = manager.getTechnicalInfoOfService(service, "advanced_checks");
                    } else {
                        checkCOMFound.checked = false;
                        checkExecutableFound.checked = false;
                        checkCOMStarting.checked = false;
                        checkRevisionVerified.checked = false;
                        checkFunctions.checked = false;
                    }
                }

                onActivated:
                {
                    updateCheckBoxes(model.get(currentIndex).service);
                }

                Component.onCompleted: {
                    ensureListWithEntries();
                }

                model: ListModel
                {
                    id: installationsModel

                    Component.onCompleted:
                    {
                        append({ text: "_INSTALLATION", service: "" });
                    }
                }
            }
        }
        Row
        {
            width: parent.width
            CheckBox
            {
                id: checkCOMFound
                text: catalog.i18nc("@label", "COM service found");
                enabled: false;
                checked: false;
            }
        }
        Row
        {
            width: parent.width
            CheckBox
            {
                id: checkExecutableFound
                text: catalog.i18nc("@label", "Executable found");
                enabled: false;
                checked: false;
            }
        }
        Row
        {
            width: parent.width
            CheckBox
            {
                id: checkCOMStarting
                text: catalog.i18nc("@label", "COM starting");
                enabled: false;
                checked: false;
            }
        }
        Row
        {
            width: parent.width
            CheckBox
            {
                id: checkRevisionVerified
                text: catalog.i18nc("@label", "Revision number");
                enabled: false;
                checked: false;
            }
        }
        Row
        {
            width: parent.width
            CheckBox
            {
                id: checkFunctions
                text: catalog.i18nc("@label", "Functions available");
                enabled: false;
                checked: false;
            }
        }
    }

    rightButtons: [
        //Button
        //{
        //    id: do_not_remember_button
        //    text: catalog.i18nc("@action:button", "Close")
        //    onClicked:
        //    {
        //        close();
        //    }
        //    enabled: true
        //}
        Button
        {
            id: close_button
            text: catalog.i18nc("@action:button", "Close")
            onClicked:
            {
                close();
            }
            enabled: true
        }
    ]
}
