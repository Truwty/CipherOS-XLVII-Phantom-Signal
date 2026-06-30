// CipherOS XLVII — SDDM Login Theme
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SddmComponents 2.0

Rectangle {
    id: root
    width: 1920; height: 1080
    color: "#08081a"

    // ── Animated background gradient ──────────────────────────────────────
    AnimatedImage {
        id: bg
        anchors.fill: parent
        source: "assets/wallpaper.png"
        fillMode: Image.PreserveAspectCrop
        opacity: 0.45
    }

    // Dark overlay
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#cc08081a" }
            GradientStop { position: 0.5; color: "#88080814" }
            GradientStop { position: 1.0; color: "#ee08081a" }
        }
    }

    // ── Scanning line animation ───────────────────────────────────────────
    Rectangle {
        id: scanLine
        width: parent.width; height: 2
        color: Qt.rgba(0, 0.82, 1, 0.12)
        y: 0
        NumberAnimation on y {
            from: 0; to: root.height
            duration: 6000
            loops: Animation.Infinite
            easing.type: Easing.Linear
        }
    }

    // ── Logo & title ──────────────────────────────────────────────────────
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.18
        spacing: 8

        Text {
            text: "⬡ CIPHEROS"
            font.family: "JetBrains Mono"
            font.pixelSize: 42
            font.weight: Font.Bold
            color: "#00d4ff"
            anchors.horizontalCenter: parent.horizontalCenter
            style: Text.Glow
            styleColor: Qt.rgba(0, 0.82, 1, 0.4)
        }
        Text {
            text: "XLVII · PHANTOM SIGNAL"
            font.family: "JetBrains Mono"
            font.pixelSize: 14
            color: "#4499bb"
            letterSpacing: 4
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    // ── Clock ─────────────────────────────────────────────────────────────
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.32
        spacing: 4

        Text {
            id: clockTime
            anchors.horizontalCenter: parent.horizontalCenter
            font.family: "JetBrains Mono"
            font.pixelSize: 72
            font.weight: Font.Light
            color: "#c8e8ff"
        }
        Text {
            id: clockDate
            anchors.horizontalCenter: parent.horizontalCenter
            font.family: "JetBrains Mono"
            font.pixelSize: 16
            color: "#7ab8d4"
            letterSpacing: 2
        }
        Timer {
            interval: 1000; running: true; repeat: true
            onTriggered: {
                var d = new Date()
                clockTime.text = Qt.formatTime(d, "hh:mm")
                clockDate.text = Qt.formatDate(d, "dddd, dd MMMM yyyy").toUpperCase()
            }
            Component.onCompleted: triggered()
        }
    }

    // ── Login panel ───────────────────────────────────────────────────────
    Rectangle {
        id: loginPanel
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.58
        width: 360; height: 180
        color: Qt.rgba(0.05, 0.05, 0.11, 0.92)
        border.color: Qt.rgba(0, 0.82, 1, 0.25)
        border.width: 1
        radius: 12

        Column {
            anchors.centerIn: parent
            spacing: 14
            width: parent.width - 48

            // User selector
            ComboBox {
                id: userCombo
                width: parent.width
                model: userModel
                textRole: "name"
                currentIndex: userModel.lastIndex
                font.family: "JetBrains Mono"
                font.pixelSize: 13

                background: Rectangle {
                    color: Qt.rgba(0.08, 0.08, 0.2, 0.9)
                    border.color: Qt.rgba(0, 0.82, 1, 0.3)
                    border.width: 1
                    radius: 6
                }
                contentItem: Text {
                    text: userCombo.displayText
                    color: "#c8e8ff"
                    font: userCombo.font
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 10
                }
            }

            // Password field
            TextField {
                id: passwordField
                width: parent.width
                placeholderText: "Enter password"
                echoMode: TextInput.Password
                font.family: "JetBrains Mono"
                font.pixelSize: 13
                color: "#c8e8ff"

                background: Rectangle {
                    color: Qt.rgba(0.08, 0.08, 0.2, 0.9)
                    border.color: passwordField.activeFocus
                        ? Qt.rgba(0, 0.82, 1, 0.7)
                        : Qt.rgba(0, 0.82, 1, 0.3)
                    border.width: 1
                    radius: 6
                }

                Keys.onReturnPressed: doLogin()
                Component.onCompleted: forceActiveFocus()
            }

            // Login button
            Button {
                id: loginBtn
                width: parent.width
                height: 38
                text: "AUTHENTICATE"
                font.family: "JetBrains Mono"
                font.pixelSize: 12
                font.weight: Font.Bold
                onClicked: doLogin()

                background: Rectangle {
                    color: loginBtn.pressed
                        ? Qt.rgba(0, 0.82, 1, 0.35)
                        : loginBtn.hovered
                        ? Qt.rgba(0, 0.82, 1, 0.2)
                        : Qt.rgba(0, 0.82, 1, 0.12)
                    border.color: Qt.rgba(0, 0.82, 1, 0.55)
                    border.width: 1
                    radius: 6
                }
                contentItem: Text {
                    text: loginBtn.text
                    font: loginBtn.font
                    color: "#00d4ff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }

    // ── Error message ─────────────────────────────────────────────────────
    Text {
        id: errorMsg
        anchors.horizontalCenter: parent.horizontalCenter
        y: loginPanel.y + loginPanel.height + 16
        color: "#ff4488"
        font.family: "JetBrains Mono"
        font.pixelSize: 12
        visible: text !== ""
    }

    // ── Power row ─────────────────────────────────────────────────────────
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        spacing: 20

        Button {
            text: "⏻  Power Off"
            font.family: "JetBrains Mono"
            font.pixelSize: 11
            onClicked: sddm.powerOff()
            background: Rectangle {
                color: "transparent"
                border.color: Qt.rgba(1, 0.27, 0.53, 0.35)
                border.width: 1; radius: 6
            }
            contentItem: Text {
                text: parent.text; color: "#cc4488"
                font: parent.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
        Button {
            text: "↺  Reboot"
            font.family: "JetBrains Mono"
            font.pixelSize: 11
            onClicked: sddm.reboot()
            background: Rectangle {
                color: "transparent"
                border.color: Qt.rgba(0, 0.82, 1, 0.25)
                border.width: 1; radius: 6
            }
            contentItem: Text {
                text: parent.text; color: "#7ab8d4"
                font: parent.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    // ── Auth logic ────────────────────────────────────────────────────────
    Connections {
        target: sddm
        onLoginFailed: {
            errorMsg.text = "Authentication failed — try again"
            passwordField.text = ""
            passwordField.forceActiveFocus()
        }
    }

    function doLogin() {
        errorMsg.text = ""
        sddm.login(
            userModel.data(userModel.index(userCombo.currentIndex, 0), Qt.UserRole + 1),
            passwordField.text,
            sessionModel.data(sessionModel.index(0, 0), Qt.UserRole + 1)
        )
    }
}
