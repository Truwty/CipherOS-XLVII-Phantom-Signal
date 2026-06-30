// CipherOS XLVII — AGS v2 Entry Point
import { App } from "astal/gtk3";
import style from "./style.scss";
import Bar from "./widgets/Bar";
import CipherHUD from "./widgets/CipherHUD";
import NotificationPopups from "./widgets/Notifications";

App.start({
    css: style,
    icons: `${SRC}/icons`,
    main() {
        App.get_monitors().map(Bar);
        App.get_monitors().map(CipherHUD);
        App.get_monitors().map(NotificationPopups);
    },
});
