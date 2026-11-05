# JalaForest AI – Forest Stand Search

Paikkatietodemo, joka hakee Metsäkeskuksen metsävarakuviot ja Syken Natura 2000 -alueet
WFS-rajapinnoista, laskee PostGISissä kunkin kuvion Natura-osuuden ja vie tuloksen
GeoParquet-tiedostoon. Tämä README kattaa vaiheen 1 (tuonti ja analyysi), ks. [PLAN.md](PLAN.md).

## Alue ja lähteet

| | |
|---|---|
| Alue | Joensuu, Noljakka – bbox EPSG:3067 `636500, 6944800, 639500, 6947200` (n. 3 × 2,4 km) |
| Metsävarakuviot | `https://avoin.metsakeskus.fi/rajapinnat/v2/stand/ows`, taso `v2:stand` |
| Natura 2000 | `https://paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs`, tasot `inspire_ps:PS.ProtectedSitesSpecialAreaOfConservation` (SAC), `…SpecialProtectionArea` (SPA), `…ProposedSiteOfCommunityImportance` (SCI) |

Tasot ja koordinaatistot on tarkistettu palveluiden GetCapabilities-vastauksista 5.11.2026:
kaikkien tasojen DefaultCRS on EPSG:3067 ja molemmat palvelut tukevat sivutusta
(`ImplementsResultPaging=TRUE`). Haku rajataan bboxilla; mukaan tulevat kaikki bboxia leikkaavat
kohteet kokonaisina.

## Vaatimukset

- Docker ja Docker Compose (testattu Docker Desktop 29.7.2 / WSL2)
- [uv](https://docs.astral.sh/uv/) (testattu 0.13.7); se asentaa Python-riippuvuudet `.venv`-hakemistoon

## Käynnistys ja tuonti

```bash
./dev up          # käynnistää PostGISin (localhost:5433) ja odottaa, että se on valmis
uv sync           # asentaa riippuvuudet
./dev run         # = uv run jalaforest run: tuonti -> analyysi -> GeoParquet-vienti
```

Tulos: `data/export/stand_natura_overlap.parquet` (GeoParquet 1.1, EPSG:4326).

Vaiheet voi ajaa myös erikseen:

```bash
uv run jalaforest import       # WFS -> PostGIS
uv run jalaforest analyze      # Natura-osuus kuvioittain
uv run jalaforest export       # GeoParquet
```

`./dev`-komennot: `up`, `down`, `restart`, `logs [-f]`, `ps`, `psql`, `reset` (poistaa myös
tietokantavolyymin, kysyy vahvistuksen), `run`, `test`. Portin voi vaihtaa ympäristömuuttujalla
`POSTGIS_PORT`, tietokantayhteyden `DATABASE_URL`:lla.

## Laskenta

- Pinta-alat lasketaan PostGISissä EPSG:3067-koordinaatistossa (`ST_Area` metreinä, jaettuna 10 000:lla).
- Natura-polygoni lasketaan mukaan vain, jos sen ja kuvion sisäosat leikkaavat kaksiulotteisesti
  (DE-9IM `2********`). Pelkkä reunan tai kulman kosketus ei kerrytä pinta-alaa.
- Kuviota leikkaavat Natura-polygonit yhdistetään (`ST_Union`) ennen leikkausta, joten päällekkäiset
  alueet (esim. sama alue sekä SAC- että SPA-tasolla) lasketaan vain kerran.
- Tulos rakennetaan uuteen tauluun ja vaihdetaan valmiina paikalleen (`stand_natura_overlap`).

## Lähde, hakuajankohta ja virhetilanteet

- Jokainen tuonti kirjataan `import_runs`-tauluun: lähde, pyyntö-URL, bbox, hakuaika, odotettu ja
  saatu kohdemäärä sekä aineiston SHA-256. Näkymä `current_source_versions` kertoo voimassa olevan version.
- Sivutus etenee `startIndex`/`count`-parametreilla vakaassa `sortBy`-järjestyksessä. Tuonti katsotaan
  epäonnistuneeksi, jos kohdemäärä poikkeaa palvelun `resultType=hits`-määrästä, tunnisteet toistuvat
  tai vastauksen koordinaatisto ei ole EPSG:3067.
- Lähde vaihdetaan tietokannassa yhdessä transaktiossa. Epäonnistunut tuonti säilyttää edellisen
  onnistuneen version, kirjaa `failed`-rivin ja `run` päättyy virhekoodiin 1 päivittämättä analyysiä
  tai vientiä.
- Nollatulos (0 kohdetta) on onnistunut haku. Esim. SPA- ja SCI-tasoilla ei ole kohteita tällä alueella.
- GeoParquetissa jokaisella rivillä on `stand_source` ja `stand_fetched_at`; kaikkien lähteiden
  versiotiedot ovat tiedoston metatiedoissa (`jalaforest:sources`).

## Tarkistukset

```bash
./dev test                         # 14 testiä: synteettinen leikkausaineisto, virhetilanteet, sivutus
uv run jalaforest fingerprint      # taulujen sisällön tiiviste; sama ennen ja jälkeen uudelleenajon
uv run jalaforest crosscheck       # laskee osuudet uudelleen Shapelyllä ja vertaa PostGISiin
```

Synteettinen aineisto (`tests/test_overlap_synthetic.py`) kattaa kaksi päällekkäistä Natura-aluetta
(0,75 ha, ei 1,0 ha), reunan ja kulman kosketuksen (0 ha), saman alueen kahdella tasolla (100 %, ei
200 %) ja kuvion ilman Natura-aluetta. Tietokantatestit ajetaan erillisessä, poistettavassa skeemassa.

Todellisilla rajapinnoilla varmennettu 5.11.2026:

- 333 kuviota ja 1 Natura-alue (FI0700107 Noljakanmäen alue, 50,15 ha), joista 81 kuviota osuu
  Natura-alueelle, yhteensä 44,3131 ha. Esim. kuvio 26516700: 5,8877 ha, josta 5,7631 ha (97,88 %) Naturaa.
- Shapely-vertailu: suurin ero PostGISiin 4,4e-16 ha kaikilla 333 kuviolla.
- Laskettu pinta-ala poikkeaa Metsäkeskuksen `area`-kentästä enintään 0,0005 ha.
- Uudelleenajo ja tyhjästä tietokannasta (`./dev reset` + `./dev run`) ajettu tuonti tuottivat
  identtiset taulutiivisteet.

## Tunnetut rajoitukset

- Aineistosta löytyy rajojen digitointieroista johtuvia pieniä leikkauksia (pienin 1,18 m², 0,008 %).
  Ne raportoidaan sellaisinaan; mahdollinen kynnysarvo päätetään hakulogiikan yhteydessä.
- Tällä alueella ei ole todellisia päällekkäisiä Natura-alueita eikä pelkkiä reunakosketuksia, joten
  ne on varmennettu vain synteettisellä aineistolla.
