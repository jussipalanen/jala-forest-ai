# Forest Stand Search AI

Lue [PLAN.md](PLAN.md) ennen toteutusta. Tee vain pyydetty työvaihe. Aloita toimivasta paikallisesta aineiston tuonnista ja PostGIS-analyysistä. Käsittele Iceberg, Glue ja Athena erillisinä jatkokokeiluina.

## Arkkitehtuuri

- Käytä Pythonia ja GeoPandasia WFS-aineistojen tuontiin sekä PostgreSQL/PostGISiä leikkauslaskentaan. Paikallinen tietokanta käynnistyy Docker Composella.
- Pidä aineiston tuonti, laskenta ja Streamlit-käyttöliittymä erillään. Julkaistava Streamlit/Folium-sovellus lukee GeoParquet-viennin omasta Cloud Run -kontistaan.
- Käytä Geminin rakenteista vastausta hakuehdoille tai tarkentavalle kysymykselle. Validoi vastaus Pydanticilla. Suodata aineisto sovelluskoodilla ja muodosta lopputiivistelmä haun palauttamista luvuista.
- Käytä lähdekoodeissa englanninkielisiä nimiä ja käyttöliittymässä suomea.

## Paikkatiedon oikeellisuus

- Varmista tasotunnisteet ja lähdekoordinaatistot palveluiden metatiedoista. Hae vain sovittu alue ja käsittele WFS-sivutus.
- Laske hehtaarit metreihin perustuvassa EPSG:3067-koordinaatistossa. Vie kartalle geometriat WGS84-muodossa. Tarkista pinta-alat myös, kun Natura-alueet ovat keskenään päällekkäisiä tai vain koskettavat metsäkuvion rajaa.
- Säilytä lähde ja hakuajankohta. Jos jommankumman lähteen tuonti epäonnistuu tai jää vajaaksi, säilytä viimeinen onnistunut aineistoversio ja näytä selkeä virhe. Nollatulos tarkoittaa onnistunutta hakua ilman osumia.

## Kehitystapa

- Tee pienin toimiva kokonaisuus ja hyödynnä olemassa olevaa koodia. Pidä Gemini-avain palvelinpuolen ympäristömuuttujassa `GEMINI_API_KEY`. Käytä julkaisuun tarkoitettua pilviprojektia vasta, kun julkaisu on pyydetty.
- Lisää pieni synteettinen tarkistusaineisto leikkauslaskennalle. Tarkista oikeilla rajapinnoilla lisäksi, että tuonti ja yksi todellinen leikkaus toimivat.
- Päivitä README:hen käytännössä varmennetut käynnistys-, tuonti- ja tarkistusohjeet. Raportoi tehdyt tarkistukset ja mahdolliset puutteet.
- Kirjaa jokainen muutos `CHANGELOG.md`-tiedostoon Keep a Changelog -muodossa ja semanttisella versioinnilla (`MAJOR.MINOR.PATCH`). Pidä `pyproject.toml`-tiedoston versio samana kuin viimeisin julkaistu versio.
