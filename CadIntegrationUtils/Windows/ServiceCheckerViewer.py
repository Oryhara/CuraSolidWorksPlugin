# Copyright (c) 2019 Thomas Karl Pietrowski

import os
import sys

# PyQt/Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

if __name__ == "__main__":
    qml_directory = os.path.dirname(os.path.abspath(__file__))
    qml_file = os.path.join(qml_directory,
                            "ServiceChecker.qml"
                            )

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.load(qml_file)

    sys.exit(app.exec_())
