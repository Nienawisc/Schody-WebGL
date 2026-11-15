# Publiczne statystyki Lucky Roomber

Panel to statyczny SVG osadzany jako obraz w opisie itch.io. Publiczny JSON zawiera te same liczniki. Generator korzysta tylko z biblioteki standardowej Pythona: bez Pillow, instalacji fontow i renderowania bitmapy.

## Pierwsze uruchomienie

1. Scal PR do `master`. Nie zmieniaj ustawien GitHub Pages ani galezi `gh-pages`.
2. Otworz `Actions > Update public statistics` i sprawdz wynik. PR uruchamia testy, ale nie publikuje na `master`.
3. Otworz `statistics/itch-embed.html` i wklej jego zawartosc w trybie HTML opisu gry na itch.io.
4. Sprawdz zapisany opis, podglad mobilny oraz adres obrazka. Ten PR nie edytuje konta itch.io i nie jest potwierdzeniem osadzenia na stronie gry.
5. Do pierwszego raportu panel pokazuje `AWAITING FIRST REPORT` i kreski. To nie sa zerowe wyniki.

Workflow zapisuje tylko `statistics/snapshot.json`, `statistics/public/stats.svg` oraz `statistics/public/stats.json`. Obecny mechanizm publikowania gry moze nadpisywac `gh-pages`; dlatego statystyki pozostaja na `master`.

## Najprostsza aktualizacja bez edytowania plikow

1. W odpowiednim projekcie i srodowisku Unity Analytics uruchom uzgodnione zapytanie eksportujace w SQL Data Explorer. Zapytanie jest przekazywane poza publicznym repozytorium; zapisz je w swoim panelu Unity.
2. Skopiuj jedna komorke `PUBLIC_STATS_JSON`, od `{` do `}`. Bez naglowka i bez zewnetrznego escapowania CSV.
3. Otworz `Actions > Update public statistics > Run workflow`, wybierz `master` i wklej wynik w `snapshot_json`.
4. Uruchom workflow. Walidacja, generowanie SVG/JSON i commit raportu wykonuja sie automatycznie. Sprawdz zielony wynik joba `publish`.

Przycisk `Run workflow` bedzie dostepny po scaleniu definicji workflow do domyslnej galezi. Puste pole odtwarza panel z zapisanego raportu, nie pobiera nowych danych. Nie zmieniamy daty raportu na date renderowania.

Przeslane raporty starsze od zapisanego sa odrzucane. Te same dane z ta sama data sa dozwolone; rozne dane z ta sama data nie. Nowszy raport moze miec nizsze liczniki, np. po usunieciu danych Analytics. Ochrona przed cofaniem dotyczy wejscia `snapshot_json`; bezposrednia edycja pliku pozostaje swiadoma operacja opiekuna repozytorium.

## Aktualizacja z wyeksportowanego CSV lub JSON

Jednorazowo zainstaluj Python 3.12+ oraz GitHub CLI i zaloguj sie przez `gh auth login`. Konto musi miec uprawnienie uruchamiania Actions w tym repozytorium. W lokalnej kopii repozytorium:

```sh
python statistics/submit_stats.py "raport-z-unity.csv"
```

Albo:

```sh
python statistics/submit_stats.py "raport-z-unity.json"
```

CSV musi zawierac dokladnie kolumne `PUBLIC_STATS_JSON` i jeden wiersz z obiektem. Skrypt obsluguje escapowanie cudzyslowow CSV oraz BOM UTF-8. Nietypowy format eksportu zostanie odrzucony: wtedy skopiuj sama komorke do pola workflow.

Skrypt najpierw waliduje dane, a nastepnie wywoluje `gh workflow run` z JSON na standardowym wejsciu, bez uruchamiania go jako polecenia powloki. Nie przechowuje tokena w repozytorium. Potwierdzenie przyjecia zgloszenia nie oznacza jeszcze udanej publikacji; sprawdz wynik Actions. Mozna nadal recznie aktualizowac `snapshot.json` zamiast korzystac z tych wejsc.

## Adres SVG i buforowanie

Adres do `<img>`:

```text
https://cdn.jsdelivr.net/gh/Nienawisc/Schody-WebGL@master/statistics/public/stats.svg
```

Publiczny JSON:

```text
https://cdn.jsdelivr.net/gh/Nienawisc/Schody-WebGL@master/statistics/public/stats.json
```

Uzywamy jsDelivr jako warstwy serwujacej pliki z publicznej galezi GitHub. Nie traktujemy adresu `raw.githubusercontent.com` jako niezawodnego hostingu SVG w `<img>`: dla SVG znaczenie ma poprawny naglowek `Content-Type: image/svg+xml`. Nie kopiuj bezposrednio kodu `<svg>` do opisu itch.io, nie uzywaj `<object>` i nie przesylaj pliku jako nowego zalacznika do itch.io, bo powstalaby niezalezna kopia.

jsDelivr dokumentuje 12-godzinny cache adresow galezi. Przegladarka lub itch.io moga miec dodatkowy cache. To nie jest licznik na zywo ani gwarancja natychmiastowej aktualizacji. Do rutynowego osadzenia uzywaj `@master`, nie SHA commita (adres SHA jest niezmienny). Data na panelu pokazuje wiek danych. Opcjonalnie mozna skorzystac z narzedzia jsDelivr Purge cache; nie zakladamy, ze usunie ono kopie w przegladarce gracza.

Po wdrozeniu zweryfikuj:

```sh
curl -I "https://cdn.jsdelivr.net/gh/Nienawisc/Schody-WebGL@master/statistics/public/stats.svg"
```

Oczekiwane: HTTP 200 i typ `image/svg+xml` (ewentualnie z charset). Otworz tez strone gry po zapisaniu opisu i sprawdz, czy itch.io zachowalo adres. Watek na forum itch.io opisuje SVG w `<img>`, ale nie zastepuje testu konkretnej strony. Gdy CDN lub osadzenie nie zadziala, mozna przeniesc te same pliki na osobny hosting statyczny z poprawnym MIME, bez zmieniania generatora. Nie przestawiaj istniejacego Pages z `gh-pages` na `master`, bo jest tam gra.

## Co liczymy

| Pole | Znaczenie |
| --- | --- |
| Recorded deaths | Rozgrywka ma potwierdzony raport `sc_report_kind = 'death'`. |
| Completed runs | Rozgrywka ma potwierdzony raport `sc_report_kind = 'completed'`; samo `sc_target_reached = true` nie wystarcza. |
| Escape rate | `completedRuns / (completedRuns + deaths) * 100`; nierozstrzygniete rozgrywki nie trafiaja do mianownika. Bez wynikow pokazujemy kreske. |
| Recorded runs | Rozgrywki po deduplikacji, nie liczba ludzi i nie MAU. |

Eksport liczy kazda rozgrywke `(UNITY_ENVIRONMENT_NAME, USER_ID, sc_run_id)` raz. Wynik wybiera sposrod raportow koncowych death/completed, aby inne migawki nie przeslonily potwierdzonego zakonczenia. Nie sumuje checkpointow ani kolejnych eksportow. Zakres dat oznacza dostepne zdarzenia, nie kompletna historie od premiery. Retencja, brak zgody, utracone/poznione raporty i usuniecia danych wplywaja na wynik.

Wybierz produkcyjne srodowisko. Uzgodniony eksport obejmuje CLIENT_VERSION 1.0.0 i 1.0; sam filtr wersji nie odroznia testerow. Escape rate nie oznacza odsetka unikalnych graczy, ktorzy ukonczyli gre.

## Bezpieczenstwo i koszty

Repozytorium, historia commitow, artefakty i dane wejsciowe workflow nie sa sejfem. Nigdy nie podawaj tokenow, ciasteczek, identyfikatorow graczy ani surowych eventow. Publikujemy tylko zbiorcze liczniki i daty. Walidator odrzuca nieznane pola, duplikaty kluczy, bledne daty/liczniki i zbyt duzy JSON; nie cofnie wycieku danych juz dodanych do historii repozytorium.

SVG zawiera tylko lokalne elementy tekstowe i geometryczne: bez JavaScriptu, `foreignObject`, zewnetrznych obrazow i fontow. Dane wchodza do XML przez bezpieczny serializer, nie konkatenacje niezaufanego HTML. Wejscie workflow przechodzi przez zmienna srodowiskowa, nie jest wklejane do skryptu powloki.

Tylko job `publish` na `master` dostaje `contents: write`, po testach. PR nie dostaje uprawnien zapisu. Nie ma force push. Blad walidacji lub konflikt z nowym commitem nie podmienia opublikowanego raportu; uruchom ponownie dla najnowszego `master`. Ochrona galezi moze blokowac publikacje: wtedy uzyj artefaktu przez zwykly PR zamiast wylaczac ochrone bez analizy.

Standardowe runnery GitHub Actions w publicznym repozytorium sa bezplatne w ramach zasad platformy. Artefakt ma retencje jednego dnia. Nie wlaczamy zadnej platnej uslugi, subskrypcji Snowflake ani cyklicznych zapytan SQL. Odczyt SVG nie wykonuje SQL. Koszty i limity zapytania w Unity pozostaja zgodne z Twoim planem.

## Automatyzacja odczytu danych

Przygotowane wejscia automatyzuja droge **zagregowany raport -> SVG/JSON -> publikacja**. Nie pobieraja danych z Unity. Plan pelnej automatyzacji, jej koszty i alternatywa bez Snowflake sa w [AUTOMATION.md](AUTOMATION.md). Nie dodajemy harmonogramu, ktory tylko odmalowywalby stare dane.

## Testowanie

```sh
python -m unittest discover -s statistics -p 'test_*.py' -v
python statistics/build_stats.py
```

Nie trzeba instalowac zaleznosci pip. Testy uzywaja danych syntetycznych; publiczny panel korzysta z `snapshot.json`. SQL nie zostal uruchomiony na prywatnym koncie Unity, a wyswietlanie SVG na rzeczywistej stronie itch.io wymaga jeszcze testu po osadzeniu.

## Zrodla

- SVG na forum itch.io: https://itch.io/t/2848567/embeding-svg-in-project-page
- Dokumentacja jsDelivr, GitHub i cache: https://www.jsdelivr.com/documentation
- GitHub workflow_dispatch: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
- GitHub Actions billing: https://docs.github.com/en/actions/concepts/billing-and-usage
- Unity SQL: https://docs.unity.com/en-us/analytics/sql-data-explorer/run-sql-data-explorer-query
- Unity Data Access: https://docs.unity.com/en-us/analytics/data-access/data-access
