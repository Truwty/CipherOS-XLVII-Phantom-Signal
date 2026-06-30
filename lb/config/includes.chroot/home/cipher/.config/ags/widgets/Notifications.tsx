// CipherOS — Dunst-style notification popups via AGS
import { App, Astal, Gtk, Gdk } from "astal/gtk3";
import { bind, timeout } from "astal";
import Notifd from "gi://AstalNotifd";

const notifd = Notifd.get_default();

function Notification({ n }: { n: Notifd.Notification }) {
    return (
        <box className={`notification urgency-${n.urgency}`} vertical spacing={6}>
            <box spacing={8}>
                {n.appIcon && <icon icon={n.appIcon} pixelSize={20} />}
                <label className="notif-summary" label={n.summary} hexpand xalign={0} />
                <button className="notif-close" onClicked={() => n.dismiss()}>✕</button>
            </box>
            {n.body && (
                <label
                    className="notif-body"
                    label={n.body}
                    wrap xalign={0}
                    wrapMode={1}
                />
            )}
        </box>
    );
}

export default function NotificationPopups(monitor: Gdk.Monitor) {
    const { TOP, RIGHT } = Astal.WindowAnchor;
    return (
        <window
            className="Notifications"
            gdkmonitor={monitor}
            anchor={TOP | RIGHT}
            layer={Astal.Layer.OVERLAY}
            marginTop={46} marginRight={12}
            application={App}
        >
            <box vertical spacing={8} widthRequest={360}>
                {bind(notifd, "notifications").as(notifs =>
                    notifs.slice(0, 5).map(n => <Notification n={n} />)
                )}
            </box>
        </window>
    );
}
