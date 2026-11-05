"""Metsäkuviohaku: full-screen map of forest stands with a conversational search bar.

Run: uv run --env-file .env streamlit run app/streamlit_app.py
Reads only the GeoParquet export (DATA_PATH); it never touches PostGIS.
"""

from __future__ import annotations

import base64
import html
import json
import os
from pathlib import Path

import folium
import geopandas as gpd
import pyarrow.parquet as pq
import streamlit as st
from streamlit_folium import st_folium

from jalaforest.assistant import Assistant, AssistantError, ai_enabled
from jalaforest.search import (
    NATURA_HIT_MIN_HA,
    SearchFilters,
    apply_filters,
    fmt_num,
    summarize,
    summary_text_fi,
)

APP_DIR = Path(__file__).parent
DATA_PATH = os.environ.get("DATA_PATH", "data/export/stand_natura_overlap.parquet")

NATURA_LABELS = {
    "any": "Kaikki kuviot",
    "overlaps": "Osuu Natura 2000 -alueelle",
    "outside": "Ei osu Natura 2000 -alueelle",
}

# Inline logo: emoji fonts are not available everywhere (e.g. minimal containers).
_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
    '<circle cx="20" cy="20" r="20" fill="#e3eedb"/>'
    '<path d="M20 7 12 18h4l-5 7h7v7h4v-7h7l-5-7h4z" fill="#1f5c33"/></svg>'
)
# An <img> data URI survives Streamlit's HTML sanitiser (inline <svg> does not).
LOGO = (f'<img class="logo" alt="" src="data:image/svg+xml;base64,'
        f'{base64.b64encode(_LOGO_SVG.encode()).decode()}">')

# Page language and an accessible name for the map iframe (Streamlit sets neither).
A11Y_SCRIPT = """<script>
document.documentElement.lang = "fi";
const nameFrames = () => document.querySelectorAll("iframe").forEach((f) => {
  if (!f.title || f.title.startsWith("streamlit_folium")) f.title = "Kartta: metsäkuviot ja hakutulokset";
});
nameFrames();
new MutationObserver(nameFrames).observe(document.body, {childList: true, subtree: true});
</script>"""

HIT_STYLE = {"color": "#1f5c33", "weight": 1.5, "fillColor": "#3f9d5a", "fillOpacity": 0.55}
OTHER_STYLE = {"color": "#7c8a7f", "weight": 0.8, "fillColor": "#c9d3cb", "fillOpacity": 0.25}


st.set_page_config(
    page_title="Metsäkuviohaku",
    page_icon="🌲",
    layout="wide",
)
st.html(f"<style>{(APP_DIR / 'theme.css').read_text(encoding='utf-8')}</style>")


@st.cache_data(show_spinner=False)
def load_stands(path: str, mtime: float) -> tuple[gpd.GeoDataFrame, list[dict]]:
    # mtime is part of the cache key, so a new export (./dev run) is picked up on reload.
    gdf = gpd.read_parquet(path)
    meta = pq.read_schema(path).metadata or {}
    sources = json.loads(meta.get(b"jalaforest:sources", b"[]"))
    return gdf, sources


# --- state -----------------------------------------------------------------

def init_state() -> None:
    ss = st.session_state
    ss.setdefault("filters", SearchFilters())
    ss.setdefault("history", [])          # turns of the unfinished conversation
    ss.setdefault("question", None)       # pending clarifying question
    ss.setdefault("last_query", None)     # query text of the completed search
    ss.setdefault("error", None)
    if "assistant" not in ss:
        ss.assistant = Assistant()
    sync_widgets(ss.filters)


def sync_widgets(f: SearchFilters) -> None:
    """Copy filters into widget state; only called before the widgets are created."""
    ss = st.session_state
    if ss.get("_synced") == f:
        return
    ss.w_min_area = f.min_area_ha
    ss.w_max_area = f.max_area_ha
    ss.w_natura = f.natura
    ss.w_pct = (f.min_natura_pct or 0.0, 100.0 if f.max_natura_pct is None else f.max_natura_pct)
    ss._synced = f


def filters_from_widgets() -> None:
    ss = st.session_state
    lo, hi = ss.w_pct
    try:
        f = SearchFilters(
            min_area_ha=ss.w_min_area,
            max_area_ha=ss.w_max_area,
            natura=ss.w_natura,
            min_natura_pct=lo if lo > 0 else None,
            max_natura_pct=hi if hi < 100 else None,
        )
    except ValueError:
        ss.error = "Pienin pinta-ala ei voi olla suurempi kuin suurin pinta-ala."
        return
    ss.filters, ss._synced, ss.error = f, f, None
    ss.last_query, ss.question, ss.history = None, None, []


def clear_search() -> None:
    ss = st.session_state
    ss.filters, ss.history, ss.question, ss.last_query, ss.error = SearchFilters(), [], None, None, None


def run_conversation(prompt: str, status_box) -> None:
    """Ask the assistant; the status message is shown only while the search runs."""
    ss = st.session_state
    history = ss.history + [{"role": "user", "text": prompt}]
    with status_box.status("Tulkitaan hakua…", expanded=False) as status:
        try:
            reply = ss.assistant.reply(history)
        except AssistantError as exc:
            reply = None
            ss.error = str(exc)
        if reply is not None and reply.action == "search":
            status.update(label="Suodatetaan kuvioita…")
    status_box.empty()
    if reply is None:
        return
    if reply.action == "clarify":
        ss.history = history + [{"role": "model", "text": reply.question}]
        ss.question, ss.error = reply.question, None
        return
    first_query = history[0]["text"]
    ss.filters, ss.history, ss.question, ss.error = reply.filters, [], None, None
    ss.last_query = first_query if len(history) == 1 else f"{first_query} → {prompt}"


# --- page --------------------------------------------------------------------

init_state()
ss = st.session_state
st.html(A11Y_SCRIPT, unsafe_allow_javascript=True)

if not Path(DATA_PATH).exists():
    st.error(f"Aineistoa ei löydy: {DATA_PATH}. Aja ensin tuonti ja vienti: ./dev run")
    st.stop()
stands, sources = load_stands(DATA_PATH, Path(DATA_PATH).stat().st_mtime)

config_error = None
try:
    ai_on = ai_enabled()
except ValueError as exc:
    config_error = f"Virheellinen AI_ENABLED-asetus, keskusteluhaku on pois käytöstä: {exc}"
    ai_on = False
prompt = st.chat_input(
    "Kirjoita haku, esim. ”Etsi isot metsäkuviot, jotka osuvat Natura 2000 -alueelle”"
    if ai_on else "Keskusteluhaku on poistettu käytöstä (AI_ENABLED=false)",
    disabled=not ai_on,
    key="chat",
)

# Header first so it is the first landmark for keyboard and screen-reader users.
appbar = st.container(key="appbar", horizontal=True, vertical_alignment="center")
with appbar:
    st.html(
        f'<div class="brand">{LOGO}<div><h1>Metsäkuviohaku</h1>'
        '<p>JalaForest AI · Joensuu, Noljakka</p></div></div>',
        width="content",
    )

card = st.container(key="card")
status_box = card.empty()
if prompt and ai_on:
    run_conversation(prompt.strip(), status_box)
sync_widgets(ss.filters)

with appbar, st.popover("Suodattimet", icon=":material/tune:", key="filters"):
    st.markdown("#### Suodattimet")
    st.number_input("Pinta-ala vähintään (ha)", min_value=0.0, step=0.5, key="w_min_area",
                    on_change=filters_from_widgets)
    st.number_input("Pinta-ala enintään (ha)", min_value=0.0, step=0.5, key="w_max_area",
                    on_change=filters_from_widgets)
    st.radio("Natura 2000", options=list(NATURA_LABELS), format_func=NATURA_LABELS.get,
             key="w_natura", on_change=filters_from_widgets)
    st.slider("Natura-osuus kuvion pinta-alasta (%)", 0.0, 100.0, step=1.0, key="w_pct",
              on_change=filters_from_widgets)
    st.button("Tyhjennä haku", on_click=clear_search, width="stretch", icon=":material/restart_alt:")
    st.caption(f"Natura-osumaksi lasketaan vähintään {fmt_num(NATURA_HIT_MIN_HA)} ha:n päällekkäisyys.")
    st.divider()
    st.markdown("##### Aineisto")
    for src in sources:
        fetched = src["fetched_at"][:16].replace("T", " ")
        st.caption(f"{src['source']}: {src['feature_count']} kohdetta, haettu {fetched} UTC")
    if ai_on:
        st.caption(f"Keskusteluhaku: Gemini ({ss.assistant.model})")
    else:
        st.caption("Keskusteluhaku: pois käytöstä (AI_ENABLED=false)")

result = apply_filters(stands, ss.filters)
summary = summarize(result)
hit_ids = set(result["stand_id"])

def stat(value: str, label: str) -> str:
    return f'<div class="stat"><span class="stat-value">{value}</span><span class="stat-label">{label}</span></div>'


def render_card() -> None:
    active = not ss.filters.is_empty()
    shown = summary if active else summarize(stands)
    chip = ('<span class="chip chip-active">Haku käytössä</span>' if active
            else '<span class="chip">Kaikki kuviot</span>')
    parts = [f'<div class="result-head"><h2 class="card-title">Hakutulos</h2>{chip}</div>']
    if ss.question:
        parts.append(
            '<div class="question" role="status"><span class="question-label">Tarkentava kysymys</span>'
            f"<p>{html.escape(ss.question)}</p></div>"
        )
    parts.append(
        '<div class="stats">'
        + stat(str(shown.count), "kuvio" if shown.count == 1 else "kuviota")
        + stat(fmt_num(shown.area_ha), "ha yhteensä")
        + stat(fmt_num(shown.natura_overlap_ha), "ha Natura 2000")
        + "</div>"
    )
    if active:
        parts.append(f'<p class="summary">{html.escape(summary_text_fi(summary))}</p>')
    else:
        parts.append('<p class="hint">Kirjoita haku alareunaan tai rajaa kuvioita Suodattimet-painikkeella.</p>')
    meta = []
    if ss.last_query:
        meta.append(f"<dt>Haku</dt><dd>{html.escape(ss.last_query)}</dd>")
    if active:
        chips = "".join(f'<span class="chip">{html.escape(c)}</span>' for c in ss.filters.describe_fi().split(", "))
        meta.append(f'<dt>Ehdot</dt><dd class="chips">{chips}</dd>')
    if meta:
        parts.append(f'<dl class="meta">{"".join(meta)}</dl>')
    parts.append(
        '<div class="legend"><span><span class="swatch hit" aria-hidden="true"></span>Hakuun osuva kuvio</span>'
        '<span><span class="swatch other" aria-hidden="true"></span>Muu kuvio</span></div>'
    )
    st.html('<section class="result" aria-label="Hakutulos">' + "".join(parts) + "</section>")

    if active and summary.count:
        with st.expander(f"Näytä kuviot listana ({summary.count})", icon=":material/list:"):
            listing = result.sort_values("stand_area_ha", ascending=False)
            st.table({
                "Kuvio": listing["stand_number"].fillna("–").tolist(),
                "Pinta-ala (ha)": [fmt_num(v) for v in listing["stand_area_ha"]],
                "Natura (ha)": [fmt_num(v, 4) for v in listing["natura_overlap_ha"]],
                "Natura (%)": [fmt_num(v) for v in listing["natura_overlap_pct"]],
            })


with card:
    for message in (config_error, ss.error):
        if message:
            st.error(message)
    render_card()


def popup_frame(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gpd.GeoDataFrame(geometry=gdf.geometry, crs=gdf.crs)
    out["hit"] = gdf["stand_id"].isin(hit_ids)
    out["Kuvio"] = gdf["stand_number"].fillna("–") + gdf["stand_number_extension"].map(
        lambda e: f".{e}" if isinstance(e, str) and e else "")
    out["Pinta-ala"] = gdf["stand_area_ha"].map(lambda v: f"{fmt_num(v)} ha")
    out["Natura-osuus"] = [f"{fmt_num(ha, 4)} ha ({fmt_num(pct)} %)"
                           for ha, pct in zip(gdf["natura_overlap_ha"], gdf["natura_overlap_pct"], strict=True)]
    out["Natura-alue"] = gdf["natura_site_names"].where(gdf["natura_site_names"] != "", "–")
    out["Keski-ikä"] = gdf["mean_age"].map(lambda v: "–" if v != v else f"{v:.0f} v")
    out["Tilavuus"] = gdf["volume_m3_per_ha"].map(lambda v: "–" if v != v else f"{fmt_num(v, 0)} m³/ha")
    return out


fields = ["Kuvio", "Pinta-ala", "Natura-osuus", "Natura-alue", "Keski-ikä", "Tilavuus"]
minx, miny, maxx, maxy = stands.total_bounds
# OpenStreetMap needs no API key (CartoDB basemaps now do). The tiles are toned down
# inside the map iframe so the stand polygons stand out against them.
fmap = folium.Map(tiles="OpenStreetMap", zoom_control="topright", control_scale=True)
fmap.get_root().header.add_child(folium.Element(
    "<style>.leaflet-tile-pane{filter:saturate(0.45) brightness(1.06) contrast(0.92);}"
    ".leaflet-popup-content-wrapper{border-radius:12px;}"
    ".leaflet-popup-content{font-family:system-ui,sans-serif;font-size:13px;}"
    # Fill the iframe whatever its height; st_folium otherwise fixes the map to `height` px.
    "html,body{height:100%;margin:0;}"
    ".folium-map,.leaflet-container{height:100vh!important;width:100%!important;}</style>"
))
fmap.fit_bounds([[miny, minx], [maxy, maxx]], padding=(20, 20))
folium.GeoJson(
    popup_frame(stands).to_json(),
    name="Metsäkuviot",
    style_function=lambda feat: HIT_STYLE if feat["properties"]["hit"] else OTHER_STYLE,
    highlight_function=lambda feat: {"weight": 3, "color": "#14421f"},
    tooltip=folium.GeoJsonTooltip(fields=["Kuvio", "Pinta-ala"], aliases=["Kuvio", "Pinta-ala"]),
    popup=folium.GeoJsonPopup(fields=fields, aliases=fields, max_width=320),
).add_to(fmap)

with st.container(key="map"):
    st_folium(fmap, height=600, use_container_width=True, returned_objects=[], key="stand_map")
