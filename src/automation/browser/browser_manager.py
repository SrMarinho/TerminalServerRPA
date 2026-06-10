import asyncio
import ctypes


class BrowserManager:
    @staticmethod
    def get_screen_size() -> tuple[int, int]:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    @staticmethod
    async def maximize_cdp(
        context,
        page,
        screen_w: int | None = None,
        screen_h: int | None = None,
    ) -> None:
        """Maximise a browser window via Chrome DevTools Protocol.

        When screen_w and screen_h are provided the window is first positioned
        at (0,0) with full viewport size before maximising — required for TS remote sessions.
        """
        session = await context.new_cdp_session(page)
        win_info = await session.send("Browser.getWindowForTarget")
        if screen_w and screen_h:
            await session.send(
                "Browser.setWindowBounds",
                {
                    "windowId": win_info["windowId"],
                    "bounds": {
                        "left": 0,
                        "top": 0,
                        "width": screen_w,
                        "height": screen_h,
                        "windowState": "normal",
                    },
                },
            )
        await session.send(
            "Browser.setWindowBounds",
            {"windowId": win_info["windowId"], "bounds": {"windowState": "maximized"}},
        )
        await session.detach()
        if screen_w and screen_h:
            await page.set_viewport_size({"width": screen_w, "height": screen_h})

    @classmethod
    async def launch(cls, playwright) -> tuple:
        """Launch Chromium, create context + page, maximise the local window."""
        browser = await playwright.chromium.launch(headless=False, args=["--start-maximized"])
        screen_w, screen_h = cls.get_screen_size()
        context = await browser.new_context(viewport=None, accept_downloads=True)
        page = await context.new_page()
        await cls.maximize_cdp(context, page)
        await page.bring_to_front()
        await asyncio.sleep(1)
        return browser, context, page, screen_w, screen_h
