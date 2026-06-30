// CipherOS XLVII — AGS Status Bar
import { App, Astal, Gtk, Gdk } from "astal/gtk3";
import { bind, Variable } from "astal";
import Battery   from "gi://AstalBattery";
import Network   from "gi://AstalNetwork";
import Mpris     from "gi://AstalMpris";
import Audio     from "gi://AstalAudio";
import Hyprland  from "gi://AstalHyprland";
import Tray      from "gi://AstalTray";

const hypr    = Hyprland.get_default();
const battery = Battery.get_default();
const network = Network.get_default();
const audio   = Audio.get_default();

// ── Workspaces ───────────────────────────────────────────────────────────────
function Workspaces() {
    return (
        <box className="workspaces">
            {bind(hypr, "workspaces").as(wss =>
                wss.sort((a, b) => a.id - b.id).map(ws => (
                    <button
                        className={bind(hypr, "focusedWorkspace").as(fw =>
                            ws.id === fw?.id ? "workspace active" : "workspace"
                        )}
                        onClicked={() => ws.focus()}
                    >
                        {ws.id}
                    </button>
                ))
            )}
        </box>
    );
}

// ── Active Window Title ───────────────────────────────────────────────────────
function ActiveWindow() {
    return (
        <label
            className="active-window"
            label={bind(hypr, "focusedClient").as(c =>
                c?.title ? (c.title.length > 60 ? c.title.slice(0, 57) + "…" : c.title) : "CipherOS"
            )}
        />
    );
}

// ── Clock ────────────────────────────────────────────────────────────────────
function Clock() {
    const time = Variable("").poll(1000, "date '+%H:%M'");
    const date = Variable("").poll(60000, "date '+%a %d %b'");
    return (
        <box className="clock-box" spacing={6}>
            <label className="clock" label={bind(time)} />
            <label className="date"  label={bind(date)} />
        </box>
    );
}

// ── Volume ───────────────────────────────────────────────────────────────────
function Volume() {
    return (
        <box className="volume" spacing={4}>
            <label label={bind(audio.defaultSpeaker, "mute").as(m => m ? "󰖁" : "󰕾")} />
            <label label={bind(audio.defaultSpeaker, "volume").as(v =>
                `${Math.round(v * 100)}%`
            )} />
        </box>
    );
}

// ── Network ──────────────────────────────────────────────────────────────────
function Network_() {
    return (
        <label
            className="network"
            label={bind(network, "primary").as(p => {
                if (p === Network.Primary.WIFI) return `  ${network.wifi?.ssid ?? "WiFi"}`;
                if (p === Network.Primary.WIRED) return "󰈀 ETH";
                return "󰤭 ";
            })}
        />
    );
}

// ── Battery ──────────────────────────────────────────────────────────────────
function BatteryWidget() {
    if (!battery.isPresent) return <box />;
    const ICONS = ["󰁺","󰁻","󰁼","󰁽","󰁾","󰁿","󰂀","󰂁","󰂂","󰁹"];
    return (
        <box className="battery" spacing={4}>
            <label label={bind(battery, "percentage").as(p => {
                const icon = ICONS[Math.floor(p * 9)];
                return battery.charging ? `󰂄 ${Math.round(p*100)}%` : `${icon} ${Math.round(p*100)}%`;
            })} />
        </box>
    );
}

// ── System Tray ──────────────────────────────────────────────────────────────
function SysTray() {
    const tray = Tray.get_default();
    return (
        <box className="systray">
            {bind(tray, "items").as(items => items.map(item => (
                <menubutton
                    className="tray-item"
                    tooltipMarkup={bind(item, "tooltipMarkup")}
                    usePopover={false}
                    menuModel={bind(item, "menuModel")}
                    actionGroup={bind(item, "actionGroup").as(ag => ["dbusmenu", ag])}
                >
                    <icon gicon={bind(item, "gicon")} pixelSize={16} />
                </menubutton>
            )))}
        </box>
    );
}

// ── CipherOS AI Button ───────────────────────────────────────────────────────
function CipherButton() {
    return (
        <button
            className="cipher-btn"
            onClicked={() => {
                import("astal/process").then(({ exec }) => exec("cipher voice --push-to-talk"));
            }}
            tooltipText="Press to talk to CipherOS (or press Super+Space)"
        >
            ⬡ Cipher
        </button>
    );
}

// ── Bar ──────────────────────────────────────────────────────────────────────
export default function Bar(monitor: Gdk.Monitor) {
    const { TOP, LEFT, RIGHT } = Astal.WindowAnchor;
    return (
        <window
            className="Bar"
            gdkmonitor={monitor}
            exclusivity={Astal.Exclusivity.EXCLUSIVE}
            anchor={TOP | LEFT | RIGHT}
            application={App}
        >
            <centerbox>
                <box className="bar-left" spacing={8} hexpand halign={Gtk.Align.START}>
                    <CipherButton />
                    <Workspaces />
                    <ActiveWindow />
                </box>
                <box className="bar-center" halign={Gtk.Align.CENTER}>
                    <Clock />
                </box>
                <box className="bar-right" spacing={10} hexpand halign={Gtk.Align.END}>
                    <SysTray />
                    <Network_ />
                    <Volume />
                    <BatteryWidget />
                </box>
            </centerbox>
        </window>
    );
}
