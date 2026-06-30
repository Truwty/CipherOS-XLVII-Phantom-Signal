// CipherOS XLVII — AI HUD overlay: status chip + expandable content panel
import { App, Astal, Gtk, Gdk } from "astal/gtk3";
import { bind, Variable } from "astal";
import GLib from "gi://GLib";
import Gio  from "gi://Gio";

// ── HUD socket connection ────────────────────────────────────────────────────
interface AIStatus {
    status:   "operational" | "thinking" | "speaking" | "error";
    response: string;
}

interface SystemMetrics {
    cpu_percent: number;
    ram_percent: number;
    disk_percent: number;
    net_sent_mb: number;
    net_recv_mb: number;
}

const aiStatus    = Variable<AIStatus>({ status: "operational", response: "" });
const metrics     = Variable<SystemMetrics | null>(null);
const panelOpen   = Variable(false);
const panelContent = Variable("");
const alertQueue  = Variable<{ level: string; title: string; message: string }[]>([]);

function connectHUD() {
    const HUD_SOCKET = "/tmp/cipher_hud.sock";
    try {
        const sockFile = Gio.File.new_for_path(HUD_SOCKET);
        const sockAddr = new Gio.UnixSocketAddress({ path: HUD_SOCKET });
        const client   = new Gio.SocketClient();

        function tryConnect() {
            client.connect_async(sockAddr, null, (_, res) => {
                try {
                    const conn = client.connect_finish(res);
                    const stream = conn.get_input_stream() as Gio.InputStream;
                    const dataStream = new Gio.DataInputStream({ base_stream: stream });
                    readLine(dataStream);
                } catch {
                    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5000, () => { tryConnect(); return false; });
                }
            });
        }

        function readLine(ds: Gio.DataInputStream) {
            ds.read_line_async(GLib.PRIORITY_DEFAULT, null, (_, res) => {
                try {
                    const [line] = ds.read_line_finish_utf8(res);
                    if (line) {
                        handleMessage(JSON.parse(line));
                    }
                    readLine(ds);
                } catch {
                    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5000, () => { tryConnect(); return false; });
                }
            });
        }

        function handleMessage(msg: { type: string; data: unknown }) {
            if (msg.type === "ai_status") {
                const d = msg.data as AIStatus;
                aiStatus.set(d);
                if (d.response && d.response.length > 120) {
                    panelContent.set(d.response);
                    panelOpen.set(true);
                    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 15000, () => { panelOpen.set(false); return false; });
                }
            } else if (msg.type === "system_metrics") {
                metrics.set(msg.data as SystemMetrics);
            } else if (msg.type === "alert") {
                const d = msg.data as { level: string; title: string; message: string };
                alertQueue.set([...alertQueue.get(), d]);
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5000, () => {
                    alertQueue.set(alertQueue.get().slice(1));
                    return false;
                });
            }
        }

        tryConnect();
    } catch (e) {
        // HUD socket unavailable — retry later
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 10000, () => { connectHUD(); return false; });
    }
}

// ── Status chip ──────────────────────────────────────────────────────────────
function StatusChip() {
    const STATUS_ICON: Record<string, string> = {
        operational: "⬡",
        thinking:    "◌",
        speaking:    "◉",
        error:       "⊗",
    };
    return (
        <button
            className={bind(aiStatus).as(s => `cipher-chip status-${s.status}`)}
            onClicked={() => panelOpen.set(!panelOpen.get())}
            tooltipText="CipherOS AI Status — click to toggle panel"
        >
            <box spacing={6}>
                <label
                    className="chip-icon"
                    label={bind(aiStatus).as(s => STATUS_ICON[s.status] ?? "⬡")}
                />
                <label
                    className="chip-status"
                    label={bind(aiStatus).as(s => {
                        if (s.status === "thinking") return "Thinking…";
                        if (s.status === "speaking") return "Speaking…";
                        if (s.status === "error")    return "Error";
                        return "CipherOS";
                    })}
                />
            </box>
        </button>
    );
}

// ── Metrics mini-bar ─────────────────────────────────────────────────────────
function MetricsPill() {
    return (
        <box
            className="metrics-pill"
            visible={bind(metrics).as(m => m !== null)}
        >
            {bind(metrics).as(m => m ? (
                <box spacing={12}>
                    <label label={`CPU ${m.cpu_percent.toFixed(0)}%`}
                           className={m.cpu_percent > 85 ? "metric-warn" : "metric"} />
                    <label label={`RAM ${m.ram_percent.toFixed(0)}%`}
                           className={m.ram_percent > 80 ? "metric-warn" : "metric"} />
                    <label label={`DSK ${m.disk_percent.toFixed(0)}%`}
                           className={m.disk_percent > 85 ? "metric-warn" : "metric"} />
                </box>
            ) : <box />)}
        </box>
    );
}

// ── Expandable content panel ──────────────────────────────────────────────────
function ContentPanel() {
    return (
        <revealer
            revealChild={bind(panelOpen)}
            transitionType={Gtk.RevealerTransitionType.SLIDE_DOWN}
            transitionDuration={200}
        >
            <box className="content-panel" vertical spacing={8}>
                <box className="panel-header">
                    <label className="panel-title" label="CipherOS Response" hexpand />
                    <button
                        className="panel-close"
                        onClicked={() => panelOpen.set(false)}
                    >✕</button>
                </box>
                <scrolledwindow
                    className="panel-scroll"
                    vscrollbarPolicy={Gtk.PolicyType.AUTOMATIC}
                    hscrollbarPolicy={Gtk.PolicyType.NEVER}
                    heightRequest={300}
                >
                    <label
                        className="panel-text"
                        label={bind(panelContent)}
                        wrap
                        wrapMode={1}
                        xalign={0}
                    />
                </scrolledwindow>
                <box className="panel-actions" spacing={8}>
                    <button className="panel-btn" onClicked={() => {
                        import("astal/process").then(({ exec }) =>
                            exec(`wl-copy "${panelContent.get().replace(/"/g, '\\"')}"`));
                    }}>Copy</button>
                    <button className="panel-btn" onClicked={() => panelOpen.set(false)}>Dismiss</button>
                </box>
            </box>
        </revealer>
    );
}

// ── Alert banners ─────────────────────────────────────────────────────────────
function AlertBanners() {
    return (
        <box vertical spacing={4} className="alert-stack">
            {bind(alertQueue).as(alerts => alerts.slice(0, 3).map(a => (
                <box className={`alert-banner alert-${a.level}`} spacing={8}>
                    <label className="alert-icon"
                           label={a.level === "critical" ? "⚠" : "ℹ"} />
                    <box vertical>
                        <label className="alert-title" label={a.title} xalign={0} />
                        <label className="alert-msg"   label={a.message} xalign={0} wrap />
                    </box>
                </box>
            )))}
        </box>
    );
}

// ── Main HUD window ───────────────────────────────────────────────────────────
export default function CipherHUD(monitor: Gdk.Monitor) {
    const { TOP, RIGHT } = Astal.WindowAnchor;

    // Connect to HUD socket on first render
    GLib.idle_add(GLib.PRIORITY_DEFAULT, () => { connectHUD(); return false; });

    return (
        <window
            className="CipherHUD"
            gdkmonitor={monitor}
            exclusivity={Astal.Exclusivity.NORMAL}
            anchor={TOP | RIGHT}
            layer={Astal.Layer.OVERLAY}
            marginTop={46}
            marginRight={12}
            application={App}
        >
            <box vertical spacing={6} widthRequest={320}>
                <box spacing={8}>
                    <StatusChip />
                    <MetricsPill />
                </box>
                <ContentPanel />
                <AlertBanners />
            </box>
        </window>
    );
}
