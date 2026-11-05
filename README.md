<div align="center">

# 🌲 JalaForest AI – Metsäkuviohaku

**Suomenkielinen keskusteluhaku metsäkuvioille ja niiden Natura 2000 -päällekkäisyydelle kartalla.**

[![CI](https://github.com/jussipalanen/jala-forest-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/jussipalanen/jala-forest-ai/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/jussipalanen/jala-forest-ai?color=3f9d5a)](https://github.com/jussipalanen/jala-forest-ai/releases)

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-17%20%2F%203.5-336791?logo=postgresql&logoColor=white)
![GeoPandas](https://img.shields.io/badge/GeoPandas-1.2-139C5A?logo=pandas&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.66-FF4B4B?logo=streamlit&logoColor=white)
![Folium](https://img.shields.io/badge/Folium%20%2F%20Leaflet-0.20-199900?logo=leaflet&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-3.1%20Flash--Lite-8E75B2?logo=googlegemini&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2-E92063?logo=pydantic&logoColor=white)
![Docker](https://img.shields.io/badge/Docker%20Compose-2496ED?logo=docker&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?logo=uv&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-D7FF64?logo=ruff&logoColor=black)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?logo=playwright&logoColor=white)
![pgAdmin](https://img.shields.io/badge/pgAdmin-9.19-336791?logo=postgresql&logoColor=white)
![Cloud Run](https://img.shields.io/badge/Cloud%20Run-europe--north1-4285F4?logo=googlecloud&logoColor=white)
![Caddy](https://img.shields.io/badge/Caddy-2.11-1F88C0?logo=caddy&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-Postgres%2018-00E599?logo=postgresql&logoColor=white)

</div>

Sovellus hakee Metsäkeskuksen metsävarakuviot ja Syken Natura 2000 -alueet WFS-rajapinnoista, laskee
PostGISissä kunkin kuvion Natura-osuuden ja näyttää tuloksen koko näytön kartalla. Haku kirjoitetaan
suomeksi alareunan hakukenttään. Gemini muuttaa sen tarkaksi hakuehdoksi tai kysyy tarkennusta, ja
sovellus suodattaa kuviot sekä muodostaa yhteenvedon haun omista luvuista. Toteutussuunnitelma on
tiedostossa [PLAN.md](PLAN.md) ja muutokset tiedostossa [CHANGELOG.md](CHANGELOG.md).

## 🚀 Pikaopas (Docker)

```bash
cp .env.example .env     # lisää GEMINI_API_KEY (tai aseta AI_ENABLED=false)
./dev up                 # rakentaa ja käynnistää PostGISin ja kartan, odottaa valmiutta
uv sync && ./dev run     # tuonti WFS:stä -> PostGIS-analyysi -> GeoParquet
```

Avaa **http://localhost:8501** ja kirjoita esimerkiksi *”Etsi isot metsäkuviot, jotka osuvat Natura
2000 -alueelle”*. Sovellus kysyy, mitä ”isot” tarkoittaa; vastaa *”Yli kaksi hehtaaria”*.

Vaatimukset: Docker ja Docker Compose (testattu Docker Desktop 29.7.2 / WSL2) sekä
[uv](https://docs.astral.sh/uv/) (testattu 0.13.7) tuontia ja testejä varten.

<details>
<summary><b>🛠️ <code>./dev</code>-komennot</b></summary>

| Komento | Toiminto |
|---|---|
| `./dev up` | Rakentaa ja käynnistää PostGISin (`localhost:5433`), kartan (`localhost:8501`) ja pgAdminin (`localhost:5050`), odottaa valmiutta |
| `./dev restart [postgis\|app\|pgadmin]` | Pakottaa kontit uusiksi: poistaa vanhat ja luo uudet (myös imagen uudelleenrakennus), tietokantavolyymi säilyy |
| `./dev down` | Pysäyttää ja poistaa kontit, tietokantavolyymi säilyy |
| `./dev build` | Rakentaa sovelluksen imagen uudelleen |
| `./dev logs [postgis\|app\|pgadmin] [-f]` | Näyttää lokit |
| `./dev ps` | Konttien tila |
| `./dev psql` | psql PostGIS-kontissa |
| `./dev dbui` | Käynnistää pgAdminin ja avaa sen selaimeen |
| `./dev reset` | Poistaa kontit **ja** tietokantavolyymin (kysyy vahvistuksen) |
| `./dev run [--neon]` | Tuonti → analyysi → GeoParquet-vienti (paikallinen PostGIS; `--neon` käyttää `.env`:n `DATABASE_URL`ia) |
| `./dev app` | Käynnistää kartan isäntäkoneella Dockerin sijaan (lukee `.env`:n) |
| `./dev lint` / `test` / `e2e` | Ruff, yksikkö- ja integraatiotestit, Playwright-selaintestit |
| `./dev smoke` | Rakentaa imagen ja testaa kirjautumisen, `robots.txt`:n ja `/health`-tarkistuksen |
| `./dev deploy` / `password` | Julkaisee Cloud Runiin / näyttää kirjautumissalasanan |

Portit voi vaihtaa muuttujilla `POSTGIS_PORT`, `APP_PORT` ja `PGADMIN_PORT`.

</details>

<details>
<summary><b>🗄️ Tietokannan selain (pgAdmin)</b></summary>

**http://localhost:5050** (tai `./dev dbui`). pgAdmin on paikallista kehitystä varten: se kuuntelee vain
`localhost`-osoitetta, ei vaadi kirjautumista ja on valmiiksi yhdistetty tietokantaan
(*Local → JalaForest PostGIS*). Tietokannan salasana luetaan kontin sisällä luotavasta pgpass-tiedostosta.

- Taulut: *Databases → jalaforest → Schemas → public → Tables* (`forest_stands`, `natura_sites`,
  `stand_natura_overlap`, `import_runs`). Hiiren oikealla: *View/Edit Data → All Rows*.
- Geometriat kartalla: avaa *Query Tool*, aja esimerkiksi alla oleva kysely ja paina tulostaulukon
  `geom`-sarakkeen otsikon karttakuvaketta (*Geometry Viewer*).

```sql
SELECT s.stand_id, round(o.natura_overlap_ha::numeric, 4) AS natura_ha, s.geom
FROM stand_natura_overlap o JOIN forest_stands s USING (stand_id)
WHERE o.natura_overlap_ha > 0
UNION ALL
SELECT NULL, NULL, n.geom FROM natura_sites n;
```

</details>

<details>
<summary><b>🐘 Pilvitietokanta (Neon)</b></summary>

Tuonnin ja PostGIS-analyysin voi ajaa paikallisen tietokannan sijaan [Neonissa](https://neon.com)
(projekti `jala-forest-ai`, haara `production`, tietokanta `jalaforest`; PostgreSQL 18, PostGIS 3.6.4,
AWS London). Ympäristö on haaran nimessä, tietokannan nimi on sama kuin paikallisesti: testihaarat
(`dev`, `test-import`) saavat oman kopion samannimisestä tietokannasta. Kartta ei käytä tietokantaa
kummassakaan tapauksessa, vaan lukee viedyn GeoParquet-tiedoston.

1. Neonin konsolissa *Connect* → poista *Connection pooling* (suora osoite ilman `-pooler`) ja lisää
   yhteysosoite `.env`-tiedostoon sellaisenaan:
   `DATABASE_URL=postgresql://neondb_owner:…@ep-….eu-west-2.aws.neon.tech/jalaforest?sslmode=require`
   (`postgresql://` muunnetaan automaattisesti psycopg 3 -muotoon).
2. `./dev run --neon` ajaa tuonnin, analyysin ja viennin Neoniin; ensimmäinen ajo luo PostGIS-laajennuksen
   ja taulut. Komento tulostaa, mihin tietokantaan se kirjoittaa. Pelkkä `./dev run` käyttää aina paikallista.
3. Tarkistus: `uv run --env-file .env jalaforest crosscheck`.

- Testit kieltäytyvät ajamasta muuta kuin paikallista tietokantaa vastaan, koska ne luovat ja poistavat
  kokonaisen testitietokannan.
- Neon sammuttaa laskennan 5 minuutin käyttämättömyyden jälkeen; älä pidä sitä hereillä pingaamalla, koska
  ilmaistason 100 CU-tuntia loppuisi. Tuonti kestää noin 8 s.
- Varmennettu 5.11.2026: sama tulos kuin paikallisesti (333 kuviota, 81 Natura-alueella, 44,3131 ha), ja
  Shapely-vertailussa ei poikkeamia. Laskentatulosten erot ovat enintään 1,8e-15 ha (Neonin GEOS 3.12 vs.
  paikallinen 3.14), eli ne katoavat viennin 4 desimaalin pyöristyksessä.

</details>

<details>
<summary><b>⚙️ Ympäristömuuttujat ja tekoälyhaun kytkin</b></summary>

Asetukset luetaan `.env`-tiedostosta (git-ignoroitu, malli: [.env.example](.env.example)). Docker
Compose lukee sen sovelluskonttiin, ja `./dev app` / `./dev e2e` lataavat sen uv:llä.

| Muuttuja | Oletus | Kuvaus |
|---|---|---|
| `AI_ENABLED` | `true` | Tekoälyhaun kytkin: `true`/`false` (myös `1`/`0`, `yes`/`no`, `on`/`off`). Kun `false`, Geminiä ei kutsuta ja hakukenttä on pois käytöstä; suodattimet toimivat. |
| `GEMINI_API_KEY` | – | Palvelinpuolen Gemini-avain. Ei koskaan selaimeen eikä versionhallintaan. |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Edullisin uusille avaimille saatavilla oleva malli (ilmaistaso; maksullinen $0,25 / $1,50 per 1M tokenia). `gemini-2.5-flash-lite` palauttaa uusille avaimille 404. |
| `GEMINI_FALLBACK_MODEL` | `gemini-3.5-flash-lite` | Seuraavaksi edullisin malli, jota käytetään vain, jos oletusmalli on ruuhkautunut (503) tai pyyntöraja täynnä (429). |
| `DATA_PATH` | `data/export/stand_natura_overlap.parquet` | Sovelluksen lukema GeoParquet. |
| `DATABASE_URL` | `postgresql+psycopg://jalaforest:jalaforest@localhost:5433/jalaforest` | Tuonnin ja analyysin tietokanta; `.env`:ssä Neonin osoite, jota `./dev run --neon` käyttää. |

Ilmaistasolla Google voi käyttää kehotteita tuotteidensa kehittämiseen; hakukenttään ei pidä
kirjoittaa henkilötietoja.

</details>

## 🗺️ Käyttöliittymä

- **Yläpalkki** logolla ja sovelluksen nimellä sekä **Suodattimet**-painike (pinta-ala, Natura 2000 -ehto,
  Natura-osuus ja aineiston lähdetiedot). Keskusteluhaun tulos päivittää samat suodattimet.
- **Aineisto**-painike avaa taulukon kaikista kuvioista: PostGISin laskema pinta-ala, Metsäkeskuksen
  ilmoittama pinta-ala, Natura-päällekkäisyys hehtaareina ja prosentteina, Natura-alue ja osuuko kuvio
  hakuun. Taulukon voi lajitella ja ladata CSV:nä, ja rivin valinta näyttää kuvion laskennan vaihe
  vaiheelta (m² → ha, osuus, 0,01 ha:n osumaraja, vertailu lähteeseen).
- **Kartta täyttää koko näkymän** yläpalkin alla (Folium / Leaflet, OpenStreetMap-pohjakartta). Hakuun
  osuvat kuviot korostetaan vihreällä, muut näkyvät harmaina. Kuviota napsauttamalla aukeaa tietolaatikko:
  pinta-ala, Natura-osuus hehtaareina ja prosentteina, Natura-alue, keski-ikä ja tilavuus.
- **Hakutulos-kortti** kartan päällä: tila (kaikki kuviot / haku käytössä), tarkentava kysymys, kolme
  tunnuslukua (kuviot, hehtaarit, Natura-hehtaarit), yhteenveto, haku ja ehdot sekä kuviot listana.
- **Hakukenttä alareunassa.** Haun aikana näkyy tilaviesti. Jos Gemini on ruuhkautunut, haku päättyy
  enintään noin 20 sekunnissa selkeään virheilmoitukseen.
- **Puhelin ja tabletti:** matalampi yläpalkki, kuvakepainike suodattimille, tiivis kortti ja koko
  levyinen hakukenttä. Ei vaakavieritystä 390 px leveydellä.
- Natura-osumaksi lasketaan vähintään **0,01 ha** päällekkäisyys. Pienemmät osuudet ovat rajojen
  digitointieroista syntyviä suikaleita; tarkka luku näkyy silti tietolaatikossa.

<details>
<summary><b>♿ Saavutettavuus</b></summary>

- Sivun kieli on `fi`, kartta-iframella on kuvaava nimi ja otsikot muodostavat rakenteen (h1 yläpalkissa,
  h2 Hakutulos-kortissa).
- Hakutulos on luettavissa myös taulukkona (”Näytä kuviot listana”), joten tiedot eivät ole vain kartalla.
- Painikkeilla on näkyvä fokus ja vähintään 44 px korkeus; puhelimen kuvakepainikkeella säilyy
  ruudunlukijalle luettava nimi.
- Playwright-testi ajaa axe-core-tarkistuksen: ei vakavia (serious/critical) rikkeitä.
- Tunnettu puute: Streamlitin omat ”Skip to main content”- ja ”Send message”-tekstit ovat englanniksi,
  eikä karttapolygoneja voi valita näppäimistöllä (sama tieto on listassa).

</details>

<details>
<summary><b>🤖 Keskusteluhaun toiminta</b></summary>

1. Gemini saa käyttäjän viestit ja palauttaa rakenteisen JSON-vastauksen (`response_json_schema`):
   joko `search` + hakuehdot tai `clarify` + suomenkielinen kysymys.
2. Vastaus validoidaan Pydanticilla (`AssistantReply`, `SearchFilters`): tuntemattomat kentät,
   negatiiviset pinta-alat, yli 100 % osuudet ja käänteiset välit hylätään.
3. Epämääräiset ehdot (”iso”, ”pieni”, ”suuri osa”) johtavat tarkentavaan kysymykseen; malli ei keksi
   raja-arvoja. Keskeneräinen haku säilyy Streamlitin istunnossa.
4. Sovelluskoodi suodattaa kuviot, ja yhteenveto muodostetaan haun tuloksen luvuista (ei mallin tekstistä).
5. Pyynnöllä on 20 s aikaraja ja enintään kaksi yritystä. Ruuhkassa (503/429) kokeillaan kerran
   varamallia (`GEMINI_FALLBACK_MODEL`).

</details>

## 🌳 Aineisto ja laskenta

| | |
|---|---|
| Alue | Joensuu, Noljakka – bbox EPSG:3067 `636500, 6944800, 639500, 6947200` (n. 3 × 2,4 km) |
| Metsävarakuviot | `https://avoin.metsakeskus.fi/rajapinnat/v2/stand/ows`, taso `v2:stand` |
| Natura 2000 | `https://paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs`, tasot `inspire_ps:PS.ProtectedSitesSpecialAreaOfConservation` (SAC), `…SpecialProtectionArea` (SPA), `…ProposedSiteOfCommunityImportance` (SCI) |

<details>
<summary><b>📥 Tuonti, lähde ja virhetilanteet</b></summary>

- Tasot ja koordinaatistot on tarkistettu palveluiden GetCapabilities-vastauksista 5.11.2026: kaikkien
  tasojen DefaultCRS on EPSG:3067 ja molemmat palvelut tukevat sivutusta (`ImplementsResultPaging=TRUE`).
  Haku rajataan bboxilla; mukaan tulevat kaikki bboxia leikkaavat kohteet kokonaisina.
- Sivutus etenee `startIndex`/`count`-parametreilla vakaassa `sortBy`-järjestyksessä. Tuonti on
  epäonnistunut, jos kohdemäärä poikkeaa `resultType=hits`-määrästä, tunnisteet toistuvat tai
  vastauksen koordinaatisto ei ole EPSG:3067.
- Jokainen tuonti kirjataan `import_runs`-tauluun (lähde, pyyntö-URL, bbox, hakuaika, kohdemäärät,
  SHA-256). Näkymä `current_source_versions` kertoo voimassa olevan version.
- Lähde vaihdetaan yhdessä transaktiossa. Epäonnistunut tuonti säilyttää edellisen onnistuneen
  version, kirjaa `failed`-rivin ja `run` päättyy virhekoodiin 1 päivittämättä analyysiä tai vientiä.
- Nollatulos on onnistunut haku (SPA- ja SCI-tasoilla ei ole kohteita tällä alueella).
- GeoParquetissa jokaisella rivillä on `stand_source` ja `stand_fetched_at`; kaikkien lähteiden
  versiot ovat tiedoston metatiedoissa (`jalaforest:sources`).

Vaiheet erikseen:

```bash
uv run jalaforest import       # WFS -> PostGIS
uv run jalaforest analyze      # Natura-osuus kuvioittain
uv run jalaforest export       # GeoParquet (EPSG:4326)
```

</details>

<details>
<summary><b>📐 Pinta-alalaskenta</b></summary>

- Pinta-alat lasketaan PostGISissä EPSG:3067-koordinaatistossa (`ST_Area` metreinä / 10 000).
- Natura-polygoni lasketaan mukaan vain, jos sen ja kuvion sisäosat leikkaavat kaksiulotteisesti
  (DE-9IM `2********`). Pelkkä reunan tai kulman kosketus ei kerrytä pinta-alaa.
- Kuviota leikkaavat Natura-polygonit yhdistetään (`ST_Union`) ennen leikkausta, joten päällekkäiset
  alueet (esim. sama alue sekä SAC- että SPA-tasolla) lasketaan vain kerran.
- Tulos rakennetaan uuteen tauluun ja vaihdetaan valmiina paikalleen (`stand_natura_overlap`).

</details>

## ☁️ Julkaisu (Cloud Run)

Julkaistu demo: **https://jalaforest-4ittj6eczq-lz.a.run.app** (projekti `client-jussialanen`,
alue `europe-north1`, palvelu `jalaforest`). Sovellus vaatii käyttäjätunnuksen ja salasanan, eikä se
käytä tietokantaa: kontti lukee siihen rakennetun GeoParquet-viennin.

```bash
./dev deploy                 # rakentaa, pushaa ja julkaisee (deploy/cloudrun.sh, toistettava)
./dev deploy --new-password  # sama + uusi kirjautumissalasana
./dev password               # näyttää salasanan Secret Managerista (käyttäjä: jalaforest)
./dev smoke                  # testaa imagen paikallisesti: kirjautuminen, robots.txt ja /health
```

Ennen julkaisua `./dev run` päivittää vietävän aineiston; julkaisu vaatii kirjautuneen `gcloud`-komennon.

<details>
<summary><b>🔒 Kirjautuminen, robotit ja terveystarkistus</b></summary>

- Kontissa Caddy-välityspalvelin on Streamlitin edessä. Kaikki sisältö, myös sovelluksen
  WebSocket-yhteys, vaatii HTTP Basic -kirjautumisen. Salasana on vain bcrypt-tiivisteenä palvelulla
  (`jalaforest-basic-auth-hash`), selväkielisenä Secret Managerissa (`jalaforest-basic-auth-password`).
- Hakukoneet ja tekoälyrobotit estetään: `robots.txt` kieltää kaiken (myös GPTBot, ClaudeBot,
  Google-Extended, PerplexityBot, CCBot ym.), ja jokaisessa vastauksessa on
  `X-Robots-Tag: noindex, nofollow, noarchive, nosnippet, noimageindex, noai, noimageai`.
- **`/health`** vastaa ilman kirjautumista `ok`, kun Streamlit on käynnissä. UptimeRobotiin:
  HTTP(s)- tai Keyword-monitori osoitteeseen `https://jalaforest-4ittj6eczq-lz.a.run.app/health`,
  avainsana `ok`, väli 5 min. Ping maksaa käytännössä ei mitään, mutta Cloud Run voi silti sammuttaa
  instanssin, jolloin ensimmäinen käynti odottaa noin 5 s käynnistystä.
- `/healthz` ei toimi Cloud Runissa: Googlen etupalvelin varaa z-kirjaimeen päättyvät polut.

</details>

<details>
<summary><b>💶 Kustannukset</b></summary>

| Asetus | Arvo | Miksi |
|---|---|---|
| Instanssit | min 0, max 1 | Ei kulua tyhjäkäynnillä; enimmäiskulu rajattu |
| CPU / muisti | 1 vCPU, 1 GiB, ei käynnistysboostia | Sovellus käyttää ~180 MB |
| Laskutus | pyyntöpohjainen (CPU vain pyyntöjen aikana) | Ilmaiskiintiö: 180 000 vCPU-s, 360 000 GiB-s, 2 M pyyntöä / kk |
| Image | n. 436 MB, rekisteri säilyttää 2 uusinta | Artifact Registryn ilmaiskiintiö 0,5 GB |
| Salaisuudet | 3 Secret Manager -salaisuutta | Ilmaiskiintiö 6 versiota |
| Budjetti | 1 / kk, hälytys 50 % ja 100 % (resurssit `app=jalaforest`) | Varoittaa ajoissa |

Streamlit pitää avoimen välilehden yhteyden auki, ja se lasketaan pyynnön kestoksi: ilmaiskiintiö riittää
noin 50 tuntiin avoimia istuntoja kuukaudessa. Ilmaiskiintiöt ovat laskutustilikohtaisia, joten saman
tilin muut palvelut kuluttavat samaa kiintiötä. `europe-north1`:stä ulos lähtevä liikenne maksaa
muutamia senttejä; karttatiilet tulevat OpenStreetMapin palvelimilta.

</details>

<details>
<summary><b>📄 Käyttöehdot (jaettu demo)</b></summary>

- Demo on tarkoitettu työnäytteeksi kirjautumistiedot saaneille. Tunnuksia ei jaeta eteenpäin.
- Hakukenttään ei kirjoiteta henkilötietoja. Keskusteluhaku käyttää Gemini API:n ilmaistasoa, jolloin
  Google voi käyttää kehotteita tuotteidensa kehittämiseen
  ([Gemini API:n ehdot](https://aistudio.google.com/docs/terms#use-restrictions)).
- Gemini-avain on vain palvelimella (`GEMINI_API_KEY` Secret Managerista); selain ei näe sitä.
  Tekoälyhaun voi kytkeä pois muuttujalla `AI_ENABLED=false`.
- Aineisto: Metsäkeskuksen metsävarakuviot ja Syken Natura 2000 -alueet avoimista rajapinnoista;
  hakuajankohta näkyy Suodattimet-paneelissa.

</details>

## ✅ Tarkistukset

```bash
./dev lint      # ruff
./dev test      # 46 yksikkö- ja integraatiotestiä (PostGIS käynnissä)
./dev e2e       # 10 Playwright-selaintestiä; Gemini-testi ajetaan vain, jos GEMINI_API_KEY on asetettu
uv run jalaforest fingerprint   # taulujen sisällön tiiviste; sama ennen ja jälkeen uudelleenajon
uv run jalaforest crosscheck    # laskee osuudet uudelleen Shapelyllä ja vertaa PostGISiin
```

Ensimmäisellä kerralla selain asennetaan komennolla `uv run playwright install chromium`.

<details>
<summary><b>🧪 Mitä testit kattavat</b></summary>

- **Leikkauslaskenta** (synteettinen aineisto PostGISissä): kaksi päällekkäistä Natura-aluetta
  (0,75 ha, ei 1,0 ha), reunan ja kulman kosketus (0 ha), sama alue kahdella tasolla (100 %, ei 200 %)
  ja kuvio ilman Natura-aluetta. Tietokantatestit ajetaan omassa `jalaforest_test`-tietokannassaan, joten
  ne eivät voi koskea oikeaan aineistoon.
- **Tuonti**: epäonnistunut tuonti säilyttää edellisen version, saman aineiston uudelleentuonti ei muuta
  tilaa, nollatulos on onnistunut tuonti. WFS-sivutus, vajaa tulos, toistuvat tunnisteet ja väärä CRS.
- **Haku**: Pydantic-validointi, suodattimet, Natura-kynnys, suomenkielinen yhteenveto ja nollatulos.
- **Aineistotaulukko**: kaikki kuviot suuruusjärjestyksessä, laskennan vaiheet ja suikaleen osumaraja;
  selaintesti valitsee rivin ja tarkistaa vaiheet.
- **Gemini-kytkentä** valeasiakkaalla: tarkennus → haku, keskusteluhistoria, virheelliset vastaukset,
  API-virhe, ruuhka ja varamalli, puuttuva avain ja `AI_ENABLED`-kytkin.
- **Streamlit** (AppTest) ja **Playwright**: yläpalkki, kortti ja kartta työpöydällä, tabletilla ja
  puhelimessa (kartta yläpalkista alareunaan ilman valkoista kaistaa), hakukenttä alareunassa, ei
  vaakavieritystä, suodatinpaneeli ja nollatulos, `AI_ENABLED=false`, axe-saavutettavuustarkistus sekä oikea
  Gemini-haku.

</details>

<details>
<summary><b>📊 Oikeilla rajapinnoilla varmennettu (5.11.2026)</b></summary>

- 333 kuviota ja 1 Natura-alue (FI0700107 Noljakanmäen alue, 50,15 ha); 81 kuviota osuu Natura-alueelle,
  yhteensä 44,3131 ha. Esim. kuvio 26516700: 5,8877 ha, josta 5,7631 ha (97,88 %) Naturaa.
- Shapely-vertailu: suurin ero PostGISiin 4,4e-16 ha. Laskettu pinta-ala poikkeaa Metsäkeskuksen
  `area`-kentästä enintään 0,0005 ha.
- Uudelleenajo ja tyhjästä tietokannasta ajettu tuonti tuottivat identtiset taulutiivisteet.
- Hyväksymisesimerkki Docker-kontissa oikealla Geminillä: ”Etsi isot metsäkuviot…” → tarkentava kysymys
  → ”Yli kaksi hehtaaria” → 5 kuviota, 16,63 ha, josta Natura-alueella 12,75 ha.

</details>

<details>
<summary><b>🔁 CI ja riippuvuudet</b></summary>

- GitHub Actions ([ci.yml](.github/workflows/ci.yml)): `lint` (ruff), `test` (pytest + PostGIS-palvelu),
  `e2e` (Playwright Chromium) ja `docker` (imagen rakennus). Gemini-selaintesti ajetaan vain, jos
  repositorion salaisuus `GEMINI_API_KEY` on asetettu.
- Dependabot ([dependabot.yml](.github/dependabot.yml)) päivittää viikoittain Python-riippuvuudet (uv),
  GitHub Actionsit, Dockerfile-pohjakuvan ja Compose-tiedoston PostGIS-imagen.

</details>

## ⚠️ Tunnetut rajoitukset

- Tällä alueella ei ole todellisia päällekkäisiä Natura-alueita eikä pelkkiä reunakosketuksia, joten ne on
  varmennettu vain synteettisellä aineistolla.
- Natura-alueen rajaa ei piirretä omana tasonaan; kuvioiden väri ja tietolaatikko kertovat osuuden.
- Playwrightin Chromium jää jumiin, jos se vastaa Basic-kirjautumishaasteeseen HTTP/2:n yli
  (`http_credentials`). Firefox ja valmiiksi lähetetty `Authorization`-otsake toimivat; tavallinen selain näyttää
  oman kirjautumisikkunansa.
