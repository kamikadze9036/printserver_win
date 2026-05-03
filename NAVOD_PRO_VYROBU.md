# HESS Plastics Print Server - návod pro výrobu

Tento návod je určený pro tým leadery, předáky a operátory ve výrobě. Popisuje
běžné používání tiskové obrazovky, přihlášení, zahájení výroby a základní
řešení problémů.

---

## 1. Otevření aplikace

Na počítači u tiskáren otevři prohlížeč a zadej:

```text
http://localhost:5000
```

Pokud je aplikace nastavena na automatické spuštění po startu Windows,
prohlížeč se po přihlášení do Windows otevře sám.

Pokud se stránka neotevře:

1. Zkontroluj, jestli je počítač zapnutý a přihlášený do Windows.
2. Zkontroluj, jestli běží okno `HESS PLASTICS - PRINT SERVER`.
3. Pokud server neběží, spusť `start.bat` ve složce `C:\PrintServer`.
4. Když problém trvá, kontaktuj správce.

---

## 2. Přihlášení

### Operátor

Operátor se běžně přihlašuje pomocí PINu.

1. Na přihlašovací obrazovce nech vybrané pole `PIN operátora`.
2. Naskenuj nebo zadej svůj PIN.
3. Po správném PINu se aplikace sama přepne na hlavní obrazovku.

Pokud se zobrazí `Nesprávný PIN`, zadej PIN znovu. Při opakovaném problému
kontaktuj tým leadera nebo správce.

### Admin / tým leader

Admin přístup je pro správu produktů, šablon, tiskáren, uživatelů a historii
výrobních příkazů.

1. Na přihlašovací obrazovce klikni na `Admin přihlášení`.
2. Zadej uživatelské jméno a heslo.
3. Klikni na `PŘIHLÁSIT SE`.

Výchozí servisní přístup po instalaci:

| Uživatel | Heslo | Role |
|---|---|---|
| admin | admin123 | Admin |
| operator1 | hess2025 | Operátor |

Doporučení: výchozí hesla po předání změnit a do výroby sdílet jen reálné
účty/PINy.

---

## 3. Zahájení výroby

Po přihlášení se zobrazí okno `VÝBĚR PRODUKTŮ PRO TISK`.

1. Do pole `Levá strana` naskenuj nebo zadej kód produktu pro levou tiskárnu.
2. Do pole `Pravá strana` naskenuj nebo zadej kód produktu pro pravou tiskárnu.
3. Pokud se tiskne jen jedna strana, druhou stranu nech prázdnou.
4. Volitelně vyplň `Číslo výrobního příkazu`.
5. Klikni na `ZAHÁJIT VÝROBU`.

Alespoň jedna strana musí mít vybraný produkt. Číslo výrobního příkazu je
volitelné.

Po zahájení se nahoře zobrazí banner aktivního výrobního příkazu:

- číslo výrobního příkazu nebo `Bez zakázky`,
- přihlášený operátor,
- čas zahájení,
- produkty pro levou a pravou stranu,
- počty vytištěných kusů pro levou, pravou a celkem.

---

## 4. Tisk etiket

Každá strana má vlastní část obrazovky:

- `STRANA L` je levá tiskárna,
- `STRANA P` je pravá tiskárna.

Tisk může proběhnout dvěma způsoby:

1. Ručně tlačítkem `TISKNOUT LEVOU` nebo `TISKNOUT PRAVOU`.
2. Automaticky pomocí vstupu ze stroje / tlačítka, pokud je zapojený trigger.

Když je vše připraveno, stav u strany svítí jako `READY`.

Po úspěšném tisku se zobrazí potvrzení a záznam se uloží do historie tisku.
V historii je vidět datum, čas, operátor, produkt, strana, šablona, způsob
spuštění a výsledek.

---

## 5. Změna produktu během práce

Pokud je potřeba změnit vybraný produkt:

1. Klikni na `ZMĚNIT`.
2. Znovu naskenuj produkt pro levou nebo pravou stranu.
3. Klikni na `ZAHÁJIT VÝROBU`.

Pozor: změnu produktu používej jen podle domluveného postupu ve výrobě. Pokud
má být předchozí výrobní příkaz korektně ukončen, nejdříve použij
`UKONČIT VÝROBU`.

---

## 6. Ukončení nebo zrušení výrobního příkazu

### UKONČIT VÝROBU

Použij pro běžné ukončení práce.

1. Klikni na `UKONČIT VÝROBU`.
2. Výrobní příkaz se uloží jako ukončený včetně počtu vytištěných kusů.
3. Aplikace nabídne výběr produktu pro další výrobu.

### ZRUŠIT VP

Použij jen když se výrobní příkaz založil špatně nebo se zasekl.

1. Klikni na `ZRUŠIT VP`.
2. Potvrď dotaz.
3. Výrobní příkaz se uloží jako zrušený.

Rozdíl:

| Tlačítko | Kdy použít | Výsledek |
|---|---|---|
| `UKONČIT VÝROBU` | normální konec výroby | uloží se jako ukončeno |
| `ZRUŠIT VP` | chyba, špatně založený příkaz, zaseknutí | uloží se jako zrušeno |

---

## 7. Nejčastější hlášky

| Hláška / stav | Co znamená | Co udělat |
|---|---|---|
| `Nesprávný PIN` | PIN neodpovídá žádnému operátorovi | Zadej PIN znovu nebo kontaktuj vedoucího |
| Produkt patří na jinou tiskárnu | Produkt je nastaven jen pro levou nebo pravou stranu | Naskenuj ho do správné strany |
| Produkt nemá přiřazenou šablonu | Produkt existuje, ale nemá tiskovou šablonu | Předej adminovi k nastavení šablony |
| `Žádný produkt nevybrán` | Pro danou stranu není vybraný produkt | Vyber produkt přes `ZMĚNIT` |
| Tlačítko tisku je šedé | Strana není připravena k tisku | Vyber produkt a zkontroluj stav tiskárny |
| `Chyba tisku` | Tiskárna neodpověděla nebo je špatně nastavená | Zkontroluj tiskárnu, kabely a materiál, potom volej správce |

---

## 8. Co může dělat admin / tým leader

V admin panelu lze spravovat:

- produkty,
- šablony etiket,
- uživatele a PINy,
- nastavení tiskáren,
- historii výrobních příkazů.

Bez konzultace se správcem neměň:

- názvy tiskáren,
- DPI,
- protokol tiskárny,
- kódování,
- šablony používané ve výrobě.

Tyto volby ovlivňují výsledný tisk.

---

## 9. Ranní kontrola

Před začátkem směny zkontroluj:

1. Počítač je zapnutý a přihlášený do Windows.
2. Webová obrazovka je otevřená.
3. Levá a pravá tiskárna jsou zapnuté.
4. V tiskárnách je správný materiál.
5. Po výběru produktu je u strany stav `READY`.
6. Proběhne zkušební tisk podle interního postupu výroby.

---

## 10. Kdy volat správce

Správce volej, pokud:

- nejde otevřít `http://localhost:5000`,
- nejde se přihlásit ani se správným PINem,
- tiskárna netiskne ani po kontrole kabelu a materiálu,
- produkt chybí v systému,
- produkt má špatnou šablonu,
- etiketa se tiskne posunutá nebo ve špatné velikosti,
- je potřeba přidat nebo upravit uživatele,
- je potřeba měnit nastavení tiskárny.

