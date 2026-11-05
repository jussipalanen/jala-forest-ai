# Forest Stand Search AI

Pieni paikkatietodemo, jossa käyttäjä hakee metsäkuvioita suomeksi ja näkee tulokset kartalla. Työnäyte kattaa aineiston tuonnin, PostGIS-analyysin ja keskustelullisen haun.

## MVP:n rajaus

- Yksi ennalta rajattu alue Joensuun seudulla. Alue valitaan, kun lähdeaineistosta on löydetty vähintään yksi todellinen päällekkäisyys.
- Kaksi aineistoa: Metsäkeskuksen metsävarakuviot ja Syken Natura 2000 -alueet.
- Yksi analyysi: kuinka monta hehtaaria ja prosenttia kustakin metsäkuviosta osuu Natura 2000 -alueelle.
- Yksi keskustelupolku: suomenkielinen haku, tarvittaessa tarkentava kysymys, haun tilaviesti, tulosyhteenveto ja korostetut kuviot. Kuvion tietolaatikko näyttää pinta-alan ja Natura-osuuden.

## Toteutusjärjestys

### 1. Aineiston tuonti ja PostGIS-analyysi

- [x] Tarkista WFS-palveluiden tasojen tunnisteet, koordinaatistot ja sivutus. Hae kummastakin lähteestä pieni oikea aineisto samalta alueelta.
- [x] Aja PostgreSQL/PostGIS Docker Composella. Tuo aineistot Pythoniin ja tietokantaan GeoPandasilla. Tallenna lähde ja hakuajankohta. Saman aineiston uudelleentuonti tuottaa saman lopputilan.
- [x] Laske pinta-alat PostGISissä EPSG:3067-koordinaatistossa. Laske Natura-alueiden yhteinen peitto niin, että päällekkäiset Natura-geometriat kerryttävät pinta-alaa vain kerran.
- [x] Tarkista yksi tunnettu leikkaus ja tapaus, jossa alueet ainoastaan koskettavat toisiaan. Vie julkaisukartalle tarvittavat geometriat ja luvut yhteen GeoParquet-tiedostoon.

### 2. Kartta ja keskusteluhaku

- [x] Näytä kuviot Streamlitissä Foliumilla. Lisää pinta-alan ja Natura-osuuden suodattimet, tulosmäärä ja kuviokohtainen tietolaatikko.
- [x] Lisää Gemini API Pythonin `google-genai`-kirjastolla. Malli palauttaa rakenteisen hakuehdon tai tarkentavan kysymyksen. Validoi hakuehdot Pydanticilla ja säilytä keskeneräinen haku Streamlitin istunnossa.
- [x] Näytä tilaviesti haun aikana. Kun haku valmistuu, korosta samat kuviot, joista tekstiyhteenveto muodostetaan. Käytä yhteenvedossa haun tarkkoja lukuja.

### 3. Julkaisu Cloud Runissa

- [ ] Pakkaa Streamlit-sovellus ja lukuvalmis GeoParquet-tiedosto samaan konttiin. Docker Compose dokumentoi paikallisen PostGIS-laskennan, ja julkaistu kartta lukee siitä viedyn aineiston.
- [ ] Varmista käynnistys Cloud Runin `PORT`-asetuksella ja testaa kartta, tarkentava kysymys sekä tulosyhteenveto. Dokumentoi Gemini-avaimen palvelinpuolen asetukset ja jaetun demon käyttöehdot.

## Hyväksymisesimerkki

Käyttäjä kirjoittaa ”Etsi isot metsäkuviot, jotka osuvat Natura 2000 -alueelle”. Sovellus kysyy, mitä käyttäjä tarkoittaa isoilla kuvioilla. Vastauksesta ”Yli kaksi hehtaaria” muodostuu tarkka hakuehto. Kartta korostaa löydetyt kuviot, yhteenveto kertoo niiden määrän ja tietolaatikosta näkee kunkin kuvion päällekkäisyyden hehtaareina ja prosentteina. Tyhjä haku näyttää nollatuloksen.

## Erillinen jatkokokeilu

- **Paikallinen Iceberg.** Vie valmiista tuloksista yhteen Iceberg-tauluun kuvion tunniste, pinta-ala ja Natura-osuus. Kokeile PyIcebergillä kahta tauluversiota paikallisilla tiedostoilla ja SQLite-luettelolla.
- **Iceberg Google Cloudissa.** Pysyvässä toteutuksessa Cloud Runin Python-sovellus voi käyttää PyIcebergiä, Cloud Storagea ja Iceberg REST -luetteloa. BigQuery voi kysellä taulua.
- **AWS Lakehouse.** PyIceberg voi kirjoittaa Iceberg v2 -taulun S3:een ja rekisteröidä sen Glue Data Catalogiin. Athena voi kysellä samaa taulua. Cloud Run voi kutsua AWS:n rajapintoja AWS-käyttöoikeuksilla. Tämä on erillinen pilvi-integraatio, jonka toteutus ja kustannukset arvioidaan omassa GitHub-issuessaan.

## Lähteet

- [Metsäkeskuksen avoimet paikkatietorajapinnat](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/aineistot-paikkatieto-ohjelmille/rajapinnat)
- [Syken suojeltujen alueiden WFS](https://paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs?request=GetCapabilities)
- [Cloud Runin konttivaatimukset](https://docs.cloud.google.com/run/docs/container-contract)
- [Gemini API:n käyttöehdot](https://aistudio.google.com/docs/terms#use-restrictions)
- [Iceberg REST -luettelo Google Cloudissa](https://docs.cloud.google.com/lakehouse/docs/set-up-lakehouse-iceberg-rest-catalog)
- [PyIcebergin Glue-kytkentä](https://py.iceberg.apache.org/configuration/#glue-catalog) ja [Iceberg-taulujen käyttö Athenassa](https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg.html)
