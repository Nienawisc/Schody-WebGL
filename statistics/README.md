# Publiczne statystyki Lucky Roomber

Panel jest obrazkiem PNG osadzanym w opisie itch.io. Publiczny JSON zawiera te same liczniki. Oba pliki powstaja z jednego zagregowanego raportu Unity Analytics.

## Dlaczego tak

- Nie zmieniamy builda gry ani ustawien GitHub Pages. Gra pozostaje na `gh-pages`.
- Dane i generator sa na `master`. Publikacja gry, ktora zastepuje zawartosc `gh-pages`, nie usuwa statystyk.
- Odwiedzajacy pobiera tylko statyczny obrazek. Nie wykonuje SQL ani kodu JavaScript i nie otrzymuje klucza Unity.
- Obrazek jest pobierany przez HTTPS bezposrednio z publicznego pliku GitHub. Zewnetrzne ramki iframe na itch.io wymagaja klikniecia, dlatego nie sa domyslnym rozwiazaniem.
- Brak automatycznego pobierania raportow z Unity. Nie uzywamy nieudokumentowanych endpointow, ciasteczek ani sesji przegladarki. GitHub automatyzuje generowanie i publikacje po aktualizacji raportu, nie samo SQL.

## Pierwsze uruchomienie

1. Scal PR z tymi plikami do `master`.
2. Otworz `Actions` w tym repozytorium i sprawdz workflow **Update public statistics**. Uruchomi testy, utworzy PNG/JSON i zapisze je na `master`.
3. Gdy Actions sa wylaczone, wlacz je dla repozytorium. Workflow nie potrzebuje zadnych Secrets ani osobistego tokenu. Jesli polityka konta lub ochrona `master` zabrania zapisu przez `GITHUB_TOKEN`, publikacja zostanie odrzucona; nie wylaczaj ochron bez zastanowienia. Alternatywa to pobranie artefaktu `public-statistics` i dodanie obu plikow przez zwykly PR.
4. Z pustym `snapshot.json` panel pokazuje **AWAITING FIRST REPORT** i kreski. To nie sa zerowe wyniki.
5. Pobierz pierwszy prawdziwy raport wedlug instrukcji ponizej.

## Aktualizacja danych, np. raz dziennie

1. Otworz wlasciwy projekt i srodowisko w Unity Analytics, nastepnie **SQL Data Explorer**.
2. Wklej zawartosc `export-public-stats.sql` i uruchom zapytanie. Zapisz je jako raport do ponownego wykorzystania.
3. Zapytanie zwraca jedna komorke **PUBLIC_STATS_JSON**. Skopiuj sam obiekt od `{` do `}`. Nie kopiuj naglowka tabeli, calego CSV ani zewnetrznych cudzyslowow/escapowania CSV.
4. Edytuj `statistics/snapshot.json` na GitHubie i zastap cala zawartosc tym obiektem. Zapisz zmiane na `master` albo przez PR.
5. Workflow automatycznie waliduje dane i odswieza `statistics/public/stats.png` oraz `stats.json`.
6. Nie zmieniaj `updatedAt` tylko po to, by raport wygladal na nowy. To czas wykonania SQL, nie generowania obrazka.

Pliki wynikowe pojawia sie po udanej publikacji:

- PNG: https://raw.githubusercontent.com/Nienawisc/Schody-WebGL/master/statistics/public/stats.png
- JSON: https://raw.githubusercontent.com/Nienawisc/Schody-WebGL/master/statistics/public/stats.json

To sa adresy publicznych plikow, nie nowa strona GitHub Pages. Nie zmieniaj obecnego zrodla Pages na `master`.

## Osadzenie na itch.io

W edycji opisu gry przelacz edytor na HTML i wklej zawartosc `itch-embed.html`. Mozna tez wstawic obraz z powyzszego adresu, jesli edytor udostepnia taka opcje.

**Uzyj zewnetrznego adresu PNG, a nie ponownego uploadu obrazka do itch.io.** Upload zapisze niezalezna kopie i kolejne aktualizacje pliku na GitHubie jej nie zmienia.

Sprawdz zapisany opis i podglad na telefonie. Ten PR nie edytuje Twojego konta itch.io, wiec osadzenie na rzeczywistej stronie trzeba jeszcze zweryfikowac. Jezeli itch.io odrzuci kod lub zastapi adres kopia na swoim CDN, uzyj zwyklego uploadu jako recznego wariantu awaryjnego.

GitHub, przegladarka lub posrednik moga buforowac obraz. Aktualizacja nie jest gwarantowana natychmiast i nie zmieni juz otwartej strony sama z siebie. Data na obrazku pozwala rozpoznac stary raport. Doraznie mozna zmienic koncowke adresu w opisie na `stats.png?v=20261114-1`, zmieniajac wersje przy kolejnym raporcie; nie jest to system odswiezania na zywo.

## Co liczymy

| Pole | Znaczenie |
| --- | --- |
| Recorded deaths | Ostatni raport rozgrywki ma `sc_report_kind = 'death'`. W aktualnej implementacji jedna rozgrywka moze zakonczyc sie jedna smiercia. |
| Completed runs | Ostatni raport ma `sc_report_kind = 'completed'`. Samo `sc_target_reached = true` nie wystarcza. |
| Escape rate | `completedRuns / (completedRuns + deaths) * 100`. Rozgrywki bez potwierdzonego wyniku nie trafiaja do mianownika. Przy braku wynikow pokazujemy kreske, nie 0%. |
| Recorded runs | Liczba rozgrywek po deduplikacji, nie liczba ludzi i nie MAU. |

SQL wybiera najnowsza migawke dla `(UNITY_ENVIRONMENT_NAME, USER_ID, sc_run_id)`, wedlug `sc_sequence`, `sc_active_seconds`, czasu zdarzenia i `EVENT_ID`. Nie sumuje wszystkich checkpointow.

Raport obejmuje dostepne dane `schody_run` w wybranym srodowisku. Nie gwarantuje historii od premiery: retencja, utracone raporty, brak zgody, pozne doslanie danych i usuniecia danych wplywaja na wynik. Nie nalezy dodawac do siebie kolejnych eksportow, bo te same rozgrywki pojawiaja sie w wielu raportach. Nie przedstawiaj tego jako liczby wszystkich graczy swiata.

SQL nie odroznia automatycznie testerow od graczy publicznych. Wybierz prawidlowe srodowisko, a po ustaleniu wersji produkcyjnych dodaj filtr `CLIENT_VERSION` lub `EVENT_JSON:sc_build_version::STRING` w sekcji `WHERE`, przed deduplikacja. Nie wymyslamy numeru produkcyjnej wersji. Zakres dat na panelu pokazuje najwczesniejsza i najpozniejsza date dostepnego zdarzenia w raporcie, nie gwarantuje pelnej kompletnosci tego okresu.

## Bezpieczenstwo

Repozytorium, `snapshot.json`, wygenerowany JSON, PNG, historia commitow oraz logi Actions sa publiczne. Nigdy nie wklejaj kluczy Unity, ciasteczek, `USER_ID`, `sc_run_id`, rekordow graczy ani eksportu surowych zdarzen. Publikujemy tylko laczne liczniki i daty.

Walidator odrzuca nieznane pola, niewlasciwe typy, powtorzone klucze, nieprawidlowe daty, ujemne liczniki i sprzeczne sumy. Nie oznacza to ochrony przed ujawnieniem zlego pliku juz dodanego do publicznego repozytorium. Przed commitem sprawdz zawartosc.

Nie ma klucza Unity po stronie klienta ani po stronie Actions. Uprawnienie zapisu do repozytorium dostaje tylko job `publish` po testach, tylko dla `master`, nigdy przy PR. Publikacja zapisuje tylko PNG i JSON oraz nie stosuje force push. Przy bledzie zachowuje poprzednie publiczne wyniki. Przy jednoczesnej zmianie `master` push moze zostac odrzucony; uruchom workflow ponownie dla najnowszej wersji.

## Koszty i aktualnosc

Ten workflow korzysta ze standardowego GitHub-hosted runnera w publicznym repozytorium. Takie minuty Actions sa bezplatne zgodnie z dokumentacja GitHub; usluga nadal ma limity i zasady uzycia. Artefakt PNG/JSON jest maly i ma retencje jednego dnia. Nie wlaczamy zadnej platnej uslugi, domeny, duzego runnera ani cyklicznego zadania SQL.

Generowanie PNG i odczyty publicznych plikow nie wykonuja SQL. Koszty i limity recznego zapytania w Unity pozostaja zgodne z Twoim planem Unity Analytics. GitHub Actions nie omija tych zasad.

Do pelnej automatyzacji pobierania z Unity potrzebny jest osobno zweryfikowany, wspierany sposob odczytu. Oficjalnie opisane Data Access korzysta z konta Snowflake; nie zakladamy, ze jest to wariant bez dodatkowego kosztu. Tego PR nie nalezy opisywac jako automatycznej integracji z Unity.

## Testowanie lokalnie

Wymagany Python 3.12 lub nowszy:

```sh
python -m pip install -r statistics/requirements.txt
python -m unittest discover -s statistics -p 'test_*.py' -v
python statistics/build_stats.py
```

Dane testowe w `test_stats.py` sa syntetyczne. Do publicznego panelu trafia wylacznie `snapshot.json`. SQL przygotowano na podstawie nazw i semantyki pol obecnej implementacji gry; nie uruchomiono go na prywatnym koncie Unity w ramach tego PR.

## Zrodla platform

- itch.io, zewnetrzne iframe wymagaja klikniecia: https://itch.io/t/2864176/click-to-activate-iframes-and-outbound-link-highlighting-on-project-pages
- itch.io, HTTPS dla zewnetrznych obrazow: https://itch.io/updates/https-now-forced-everywhere
- GitHub, rozliczanie standardowych Actions w repozytoriach publicznych: https://docs.github.com/en/actions/concepts/billing-and-usage
- Unity, SQL Data Explorer: https://docs.unity.com/en-us/analytics/sql-data-explorer/run-sql-data-explorer-query
- Unity, dostepne kolumny EVENTS: https://docs.unity.com/en-us/analytics/sql-data-explorer/sql-data-explorer-tables
- Unity, Data Access: https://docs.unity.com/en-us/analytics/data-access/set-up-data-access
