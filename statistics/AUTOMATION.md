# Automatyzacja statystyk: wdrozone elementy i dalszy plan

## 1. Wdrozone: publikacja z JSON albo CSV

```text
Unity SQL (recznie) -> jedna komorka JSON / eksport CSV
                  -> Run workflow / submit_stats.py
                  -> walidacja -> SVG + JSON -> commit na master -> CDN -> itch.io
```

Po pobraniu wyniku reszta jest automatyczna. Nie potrzeba klucza Unity ani zewnetrznego serwera. Skrypt `submit_stats.py` moze byc ostatnim krokiem dowolnego zaufanego eksportera, ktory w przyszlosci dostarczy zgodny JSON. To nadal nie jest automat wykonujacy SQL w Unity.

## 2. Pelna automatyzacja obecnych danych Analytics: Data Access / Snowflake

Oficjalne Unity Data Access udostepnia dane Analytics kontu Snowflake. W sprawdzonej dokumentacji nie potwierdzono publicznego API do uruchamiania zapisanych raportow SQL Data Explorer przez service account. Udokumentowane Analytics REST API sluzy przede wszystkim do wysylania eventow, nie pobierania tych raportow.

Plan do wdrozenia dopiero po akceptacji kosztow i skonfigurowaniu konta:

1. W Unity Analytics Settings skonfigurowac Data Access dla wlasnego konta Snowflake w obslugiwanym regionie. Nie zakladamy, ze konto/provisioning jest bezplatne.
2. Potwierdzic strukture udostepnionych widokow oraz wybrac projekt i srodowisko. Share obejmuje organizacje. `ACCOUNT_EVENTS` nie ma identycznego schematu jak `EVENTS` z SQL Data Explorer; nie wolno po prostu podmienic nazwy tabeli. Dostosowac pola i przetestowac wynik przeciwko recznemu raportowi.
3. Utworzyc osobnego uzytkownika technicznego, role tylko do odczytu i uwierzytelnianie kluczem. Ustawic maly warehouse z auto-suspend, limit czasu zapytania i resource monitor. Sprawdzic, jakie koszty monitor faktycznie obejmuje.
4. Dodac chronione Secrets do zaufanego workflow, nigdy do PR z obcych galezi. Konto, klucz i wyniki surowe nie moga trafiac do logow ani artefaktow.
5. Raz dziennie wykonywac jedno zagregowane zapytanie, otrzymujace tylko pola naszego schematu. Przy bledzie zachowac poprzedni raport i jego date. Bez petli ponownych pelnych zapytan.
6. Przekazac wynik do istniejacego walidatora i generatora. Publikowac tylko aggregate JSON/SVG. Harmonogram GitHub nie gwarantuje dokladnej godziny wykonania.

Koszt: standardowy runner publicznego GitHub jest darmowy w ramach regul platformy, ale Snowflake obciaza konsumenta za compute zapytan do wspoldzielonych danych. Darmowy prog MAU w Unity nie jest gwarancja darmowego Snowflake. W tym PR nie utworzono konta, nie dodano Secrets, konektora ani harmonogramu Snowflake.

## 3. Alternatywa dla celu 0 zl: osobny licznik od nowej wersji gry

Proponowana architektura (nie wdrozona):

```text
Unity -> Cloudflare Worker -> D1 (deduplikowane stany rozgrywek)
                          -> zagregowane stats.json / stats.svg z cache -> itch.io
```

Workers i D1 maja darmowe plany z limitami. Moze to wystarczyc dla malej gry; nie jest gwarancja nielimitowanego darmowego ruchu. Przekroczenie limitow planu Free moze zatrzymac aktualizacje. Odczyty panelu powinny korzystac z cache, nie uruchamiac agregacji przy kazdym wyswietleniu.

Wymagania przed implementacja:

- Zmiana builda gry: przesylanie startu i wyniku rozgrywki do nowego endpointu, a nie tylko do Analytics. Nie robic tego w trakcie blokady zmian plikow jamu.
- Idempotencja: identyfikator rozgrywki, rosnaca sekwencja i tylko jeden finalny wynik. Zapis i aktualizacja licznikow musza byc atomowe, inaczej ponowione zadania lub jednoczesne zdarzenia zawyza statystyki.
- Nigdy nie umieszczac w WebGL klucza administracyjnego, tokena GitHub ani tokena Cloudflare. Zastosowac sesje wystawiane przez serwer, ograniczanie liczby zadan i walidacje przejsc stanow. CORS nie jest uwierzytelnianiem.
- Dane przesylane przez klienta nadal mozna sfalszowac; bez autorytatywnego serwera nie ma gwarancji prawdziwosci. Nie przedstawiamy wynikow jako odpornego na oszustwa rankingu.
- Minimalizacja danych i zgodnosc ze zgodami gracza. Nie omijac rezygnacji z Analytics wysylajac te same zdarzenia drugim kanalem bez oceny zasad prywatnosci. W publicznym JSON tylko sumy, nie identyfikatory/sesje.
- Liczyc statystyki od jawnej daty lub wersji uruchomienia nowego licznika. Nie dodawac globalnej starej sumy Analytics do nowych zdarzen bez rozlaczenia kohort, bo mozna policzyc ta sama rozgrywke dwukrotnie. Nowe liczby moga roznic sie od Analytics.

Ta opcja ma sens dla kilku publicznych licznikow, gdy priorytetem jest automatyzacja w darmowym progu, a nie identycznosc z historycznymi raportami Unity. Wymaga konta Cloudflare, konfiguracji i osobnej zmiany gry. Nie zostala wdrozona ani wlaczona tym PR.

## Rekomendacja

Teraz: SVG oraz prosty import raportu, bez nowego backendu i kosztow. Dla automatycznego odczytu dokladnie tych samych danych: zweryfikowane Data Access ze swiadomie zaakceptowanym kosztem. Dla malego darmowego licznika na przyszlosc: osobny backend po jamie, z zasadami powyzej.

Nie polecam zapisywania ciasteczek sesji Unity w Actions ani odtwarzania wewnetrznych zapytan panelu. To kruche rozwiazanie, ktore wymaga utrzymywania sesji oraz ryzykuje ujawnienie szerszego dostepu niz odczyt statystyk.

## Zrodla

- Unity Data Access: https://docs.unity.com/en-us/analytics/data-access/data-access
- Widoki Data Access: https://docs.unity.com/en-us/analytics/data-access/data-access-views
- Unity Analytics REST API: https://docs.unity.com/en-us/analytics/rest-api/rest-api
- Snowflake: koszty konsumenta Secure Data Sharing: https://docs.snowflake.com/en/user-guide/data-sharing-intro
- GitHub Actions: https://docs.github.com/en/actions/concepts/billing-and-usage
- Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/
- D1 pricing: https://developers.cloudflare.com/d1/platform/pricing/
