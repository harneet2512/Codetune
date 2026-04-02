"""Capture screenshots of CodeTune demo and assemble into a GIF."""

import asyncio
import os
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "screenshots"
GIF_PATH = Path(__file__).parent.parent / "codetune-demo.gif"
URL = "http://localhost:3000"

VIEWPORT = {"width": 1440, "height": 900}


async def capture():
    OUTPUT_DIR.mkdir(exist_ok=True)
    screenshots = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,  # retina quality
            color_scheme="dark",
        )
        page = await ctx.new_page()

        # Navigate and wait for React to render
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # --- Shot 1: Playground (default view) ---
        print("Capturing: Playground...")
        path = str(OUTPUT_DIR / "01_playground.png")
        await page.screenshot(path=path, full_page=False)
        screenshots.append(path)

        # --- Shot 2: Click Run to start block animation, wait a bit ---
        print("Capturing: Playground running...")
        # Find and click the Run button
        run_btn = page.locator("button", has_text="Run All Models")
        if await run_btn.count() > 0:
            await run_btn.first.click()
            await page.wait_for_timeout(3000)  # let blocks animate
            path = str(OUTPUT_DIR / "02_playground_running.png")
            await page.screenshot(path=path, full_page=False)
            screenshots.append(path)
            await page.wait_for_timeout(4000)  # more animation
            path = str(OUTPUT_DIR / "03_playground_animated.png")
            await page.screenshot(path=path, full_page=False)
            screenshots.append(path)

        # --- Shot 3: Eval Dashboard ---
        print("Capturing: Eval Dashboard...")
        eval_btn = page.locator("button", has_text="Eval Dashboard")
        if await eval_btn.count() > 0:
            await eval_btn.first.click()
            await page.wait_for_timeout(1500)
            path = str(OUTPUT_DIR / "04_eval_dashboard.png")
            await page.screenshot(path=path, full_page=False)
            screenshots.append(path)

            # Scroll down to see more of the dashboard
            await page.evaluate("document.querySelector('main').scrollBy(0, 500)")
            await page.wait_for_timeout(500)
            path = str(OUTPUT_DIR / "05_eval_scrolled.png")
            await page.screenshot(path=path, full_page=False)
            screenshots.append(path)

        # --- Shot 4: Models ---
        print("Capturing: Models...")
        models_btn = page.locator("button", has_text="Models")
        if await models_btn.count() > 0:
            await models_btn.first.click()
            await page.wait_for_timeout(1500)
            path = str(OUTPUT_DIR / "06_models.png")
            await page.screenshot(path=path, full_page=False)
            screenshots.append(path)

        # --- Shot 5: Connectors ---
        print("Capturing: Connectors...")
        conn_btn = page.locator("button", has_text="Connectors")
        if await conn_btn.count() > 0:
            await conn_btn.first.click()
            await page.wait_for_timeout(1500)
            path = str(OUTPUT_DIR / "07_connectors.png")
            await page.screenshot(path=path, full_page=False)
            screenshots.append(path)

            # Try to expand a tool
            try_btn = page.locator("text=search_repos").first
            if await try_btn.count() > 0:
                await try_btn.click()
                await page.wait_for_timeout(1000)
                path = str(OUTPUT_DIR / "08_connectors_expanded.png")
                await page.screenshot(path=path, full_page=False)
                screenshots.append(path)

        await browser.close()

    # --- Assemble GIF ---
    print(f"\nAssembling GIF from {len(screenshots)} screenshots...")
    if not screenshots:
        print("No screenshots captured!")
        return

    frames = []
    for s in screenshots:
        img = Image.open(s)
        # Resize for GIF (half size to keep file manageable)
        w, h = img.size
        img = img.resize((w // 2, h // 2), Image.LANCZOS)
        # Convert to palette mode for GIF
        img = img.convert("RGB")
        frames.append(img)

    # Duration per frame in ms (longer pause on first and last)
    durations = []
    for i in range(len(frames)):
        if i == 0 or i == len(frames) - 1:
            durations.append(3000)  # 3s on first/last
        else:
            durations.append(2000)  # 2s per frame

    frames[0].save(
        str(GIF_PATH),
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )

    gif_size = os.path.getsize(GIF_PATH) / (1024 * 1024)
    print(f"GIF saved: {GIF_PATH} ({gif_size:.1f} MB)")
    print(f"Screenshots saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(capture())
