"""Background removal: online shortcuts and desktop tool recommendations."""

from __future__ import annotations

import os
import webbrowser

from tkinter import BOTH, Frame, ttk

from ui.tools.panel_base import ToolPanel, build_resource_card, build_tool_hint

ILOVEIMG_BG_URL = "https://www.iloveimg.com/remove-background"
PIXLR_BG_URL = "https://pixlr.com/remove-background/"
GIMP_URL = "https://www.gimp.org/"
INKSCAPE_URL = "https://inkscape.org/"
MS_PAINT_HELP_URL = "https://support.microsoft.com/windows/use-microsoft-paint-to-remove-background"


class BackgroundRemovalToolPanel(ToolPanel):
    panel_id = "background_removal"
    tab_key = "tools_panel_bg_remove"

    def build(self, parent: Frame) -> None:
        app = self.app
        scroll_area, body = app._make_vertical_scroll(parent)
        scroll_area.pack(fill=BOTH, expand=True, padx=10, pady=10)
        build_tool_hint(body, app, "tools_bg_remove_hint")

        online = ttk.LabelFrame(body, text=self._tr("tools_bg_online_title"))
        app.translated.append((online, "tools_bg_online_title", "text"))
        online.pack(fill=BOTH, expand=False, pady=(0, 4))
        build_resource_card(
            online,
            app,
            title_key="tools_bg_iloveimg_title",
            desc_key="tools_bg_iloveimg_desc",
            url=ILOVEIMG_BG_URL,
            badge_key="tools_badge_online",
            on_open=lambda: webbrowser.open(ILOVEIMG_BG_URL),
        )
        build_resource_card(
            online,
            app,
            title_key="tools_bg_pixlr_title",
            desc_key="tools_bg_pixlr_desc",
            url=PIXLR_BG_URL,
            badge_key="tools_badge_online",
            on_open=lambda: webbrowser.open(PIXLR_BG_URL),
        )

        desktop = ttk.LabelFrame(body, text=self._tr("tools_bg_desktop_title"))
        app.translated.append((desktop, "tools_bg_desktop_title", "text"))
        desktop.pack(fill=BOTH, expand=False, pady=(12, 4))
        build_resource_card(
            desktop,
            app,
            title_key="tools_bg_gimp_title",
            desc_key="tools_bg_gimp_desc",
            url=GIMP_URL,
            action_key="tools_open_website",
            badge_key="tools_badge_desktop",
            on_open=lambda: webbrowser.open(GIMP_URL),
        )
        build_resource_card(
            desktop,
            app,
            title_key="tools_bg_mspaint_title",
            desc_key="tools_bg_mspaint_desc",
            url=MS_PAINT_HELP_URL,
            action_key="tools_open_paint",
            badge_key="tools_badge_desktop",
            on_open=self._open_ms_paint,
        )
        build_resource_card(
            desktop,
            app,
            title_key="tools_bg_inkscape_title",
            desc_key="tools_bg_inkscape_desc",
            url=INKSCAPE_URL,
            action_key="tools_open_website",
            badge_key="tools_badge_desktop",
            on_open=lambda: webbrowser.open(INKSCAPE_URL),
        )

    def _open_ms_paint(self) -> None:
        try:
            os.startfile("mspaint.exe")
        except OSError:
            webbrowser.open(MS_PAINT_HELP_URL)
