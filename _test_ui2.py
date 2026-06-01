import asyncio

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        errors = []
        page.on("pageerror", lambda err: errors.append(f"JS Error: {err}"))

        print("1. Loading page...")
        await page.goto("http://127.0.0.1:8081", timeout=15000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        print(f"   Title: {await page.title()}")

        if errors:
            for e in errors:
                print(f"   {e}")

        print("\n2. Checking task loading...")
        task_cards = await page.query_selector_all(".task-tile")
        print(f"   Task cards found: {len(task_cards)}")

        task_search = await page.query_selector("#taskSearch")
        print(f"   Search bar exists: {task_search is not None}")

        if len(task_cards) == 0:
            print("   Checking taskCards innerHTML...")
            html = await page.inner_html("#taskCards")
            print(f"   #taskCards content ({len(html)} chars): {html[:200]}")

        print("\n3. Checking credentials panel...")
        creds_panel = await page.query_selector("#panel-credentials")
        print(f"   panel-credentials exists: {creds_panel is not None}")
        if creds_panel:
            hidden = await creds_panel.get_attribute("class")
            print(f"   panel-credentials class: {hidden}")

        print("\n4. Checking switchPanel function...")
        switch_result = await page.evaluate("""
            try {
                if (typeof switchPanel !== 'function') return 'switchPanel not a function';
                return 'switchPanel exists';
            } catch(e) { return 'Error: ' + e.message; }
        """)
        print(f"   {switch_result}")

        print("\n5. Checking loadTasks function...")
        tasks_result = await page.evaluate("""
            try {
                if (typeof loadTasks !== 'function') return 'loadTasks not a function';
                if (typeof allTasks === 'undefined') return 'allTasks is undefined';
                return 'loadTasks exists, allTasks: ' + JSON.stringify(allTasks);
            } catch(e) { return 'Error: ' + e.message; }
        """)
        print(f"   {tasks_result}")

        print("\n6. Testing switchPanel('credentials')...")
        await page.evaluate("switchPanel('credentials')")
        await page.wait_for_timeout(500)
        tasks_vis = await page.locator("#panel-tasks").is_hidden()
        creds_vis = await page.locator("#panel-credentials").is_visible()
        print(f"   tasks hidden: {tasks_vis}, credentials visible: {creds_vis}")

        print("\n7. Testing switchPanel('tasks')...")
        await page.evaluate("switchPanel('tasks')")
        await page.wait_for_timeout(500)
        tasks_vis = await page.locator("#panel-tasks").is_visible()
        print(f"   tasks visible: {tasks_vis}")

        task_cards_after = await page.query_selector_all(".task-tile")
        print(f"   Task cards after switch: {len(task_cards_after)}")

        print("\n8. Checking history panel...")
        await page.evaluate("switchPanel('history')")
        await page.wait_for_timeout(1000)
        history = await page.query_selector("#historyList")
        if history:
            html = await history.inner_html()
            print(f"   History content ({len(html)} chars): {html[:200]}")
        else:
            print("   #historyList not found!")

        print("\n9. Checking WebSocket connection...")
        ws_result = await page.evaluate("""
            try {
                if (typeof _connectWS !== 'function') return '_connectWS not found';
                return '_connectWS exists';
            } catch(e) { return 'Error: ' + e.message; }
        """)
        print(f"   {ws_result}")

        print("\n10. Final errors:")
        if errors:
            for e in errors:
                print(f"    {e}")
        else:
            print("    No JS errors detected")

        await browser.close()

asyncio.run(main())
