"""Browser tests: full-screen map, floating card, bottom search bar, filters and AI search."""

import os
import re

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

CARD = ".st-key-card"
CHAT = "[data-testid=stChatInput] textarea"


def open_app(page: Page, url: str) -> None:
    page.goto(url)
    expect(page.locator(CARD)).to_contain_text("Hakutulos", timeout=30_000)
    expect(page.locator("iframe").first).to_be_visible()


def test_search_bar_at_bottom(page: Page, app_url):
    page.set_viewport_size({"width": 1280, "height": 800})
    open_app(page, app_url)
    expect(page.locator(CARD)).to_contain_text("Kaikki kuviot")
    expect(page.locator(".stat").first).to_contain_text("4")

    frame = page.locator(".st-key-map iframe").bounding_box()
    assert frame["width"] >= 1280 - 1

    chat = page.locator("[data-testid=stChatInput]").bounding_box()
    assert chat["y"] + chat["height"] > 800 - 120, "search bar should sit at the bottom of the view"


def test_no_horizontal_scroll_on_phone(page: Page, app_url):
    page.set_viewport_size({"width": 390, "height": 844})
    open_app(page, app_url)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390


def test_filter_popover_and_zero_result(page: Page, app_url):
    open_app(page, app_url)
    page.get_by_role("button", name="Suodattimet").click()
    area_min = page.get_by_label("Pinta-ala vähintään (ha)")
    area_min.fill("2")
    area_min.press("Enter")
    expect(page.locator(CARD)).to_contain_text("Löytyi 3 kuviota, yhteensä 9,5 ha.")

    area_min.fill("100")
    area_min.press("Enter")
    expect(page.locator(CARD)).to_contain_text("Hakuehdoilla ei löytynyt yhtään kuviota.")


def test_ai_disabled_by_env(page: Page, app_url_ai_off):
    open_app(page, app_url_ai_off)
    expect(page.locator(CHAT)).to_be_disabled()
    expect(page.locator(CHAT)).to_have_attribute("placeholder", re.compile("AI_ENABLED=false"))


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="needs GEMINI_API_KEY for the real Gemini API")
def test_conversational_search_with_gemini(page: Page, app_url):
    open_app(page, app_url)
    page.locator(CHAT).fill("Etsi isot metsäkuviot, jotka osuvat Natura 2000 -alueelle")
    page.locator(CHAT).press("Enter")
    expect(page.locator(CARD)).to_contain_text("Tarkentava kysymys", timeout=60_000)

    page.locator(CHAT).fill("Yli kaksi hehtaaria")
    page.locator(CHAT).press("Enter")
    # Synthetic data: only stand 1 is over 2 ha and on Natura (stand 4 is a sliver).
    expect(page.locator(CARD)).to_contain_text("Löytyi 1 kuvio, yhteensä 3 ha.", timeout=60_000)
    expect(page.locator(CARD)).to_contain_text("pinta-ala vähintään 2 ha")


@pytest.mark.parametrize("viewport", [(1440, 900), (768, 1024), (390, 844)], ids=["desktop", "tablet", "phone"])
def test_header_card_and_map_layout(page: Page, app_url, viewport):
    w, h = viewport
    page.set_viewport_size({"width": w, "height": h})
    open_app(page, app_url)
    expect(page.get_by_role("heading", level=1, name="Metsäkuviohaku")).to_be_visible()
    expect(page.get_by_role("button", name="Suodattimet")).to_be_visible()
    leaflet_loc = page.frame_locator(".st-key-map iframe").locator(".leaflet-container")
    expect(leaflet_loc).to_be_visible()

    # Map starts right below the header and reaches the bottom edge: no white band.
    # Poll briefly: st_folium first renders at its default height, then the CSS takes over.
    for _ in range(20):
        header = page.locator(".st-key-appbar").bounding_box()
        frame = page.locator(".st-key-map iframe").bounding_box()
        leaflet = leaflet_loc.bounding_box()
        if (abs(frame["y"] - header["height"]) <= 1 and abs(frame["y"] + frame["height"] - h) <= 1
                and abs(leaflet["height"] - frame["height"]) <= 1):
            break
        page.wait_for_timeout(250)
    assert abs(frame["y"] - header["height"]) <= 1
    assert abs(frame["y"] + frame["height"] - h) <= 1
    assert abs(leaflet["height"] - frame["height"]) <= 1
    card = page.locator(CARD).bounding_box()
    # Card stays inside the viewport.
    assert card["x"] >= 0 and card["x"] + card["width"] <= w
    assert page.evaluate("document.documentElement.scrollWidth") <= w


def test_accessibility(page: Page, app_url):
    open_app(page, app_url)
    assert page.evaluate("document.documentElement.lang") == "fi"
    assert page.locator(".st-key-map iframe").get_attribute("title") == "Kartta: metsäkuviot ja hakutulokset"
    results = Axe().run(page)
    serious = [v for v in results.response["violations"] if v["impact"] in ("serious", "critical")]
    assert not serious, results.generate_report()
