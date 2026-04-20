# System Zarządzania Harmonogramem Ramp Załadunkowych 🚛

Kompleksowy system webowy w architekturze klient-serwer do zarządzania, planowania i wizualizacji okien czasowych na rampach magazynowych w czasie rzeczywistym.

## 🌟 Główne funkcjonalności

* **Interaktywny Harmonogram:** Wizualna oś czasu wyświetlająca awizacje na dany dzień z podziałem na rampy (kolumny) i godziny (wiersze).
* **Kolorowanie Statusów:** Dynamiczne przypisywanie kolorów kafelkom na podstawie aktualnego statusu operacji (np. *W ZAŁADUNKU*, *ZAKOŃCZONA*, *AWARIA*).
* **Automatyzacja Ekranów:** Działające w tle funkcje auto-odświeżania oraz auto-przewijania widoku, konfigurowane globalnie z poziomu serwera (idealne na duże telewizory magazynowe).
* **Bezpieczeństwo i Autoryzacja:** Dostęp do systemu chroniony logowaniem opartym o tokeny JWT. Podział ról na Pracowników (odczyt) i Administratorów (zarządzanie).
* **Zintegrowany Panel Administratora (SPA Modal):**
  * Pełna obsługa awizacji (CRUD) z rygorystyczną walidacją formularzy.
  * Błyskawiczna zmiana statusów z poziomu tabeli.
  * Zarządzanie dynamicznymi słownikami (Rampy, Przewoźnicy, Kierowcy, Towary).
  * Panel zarządzania kontami użytkowników.
  * Konfiguracja ustawień globalnych systemu.

## 🛠 Stos technologiczny

**Backend:**
* [Python 3](https://www.python.org/)
* [FastAPI](https://fastapi.tiangolo.com/) - Szybki i nowoczesny framework webowy API.
* [SQLite](https://www.sqlite.org/) - Lekka, plikowa relacyjna baza danych.
* [PyJWT](https://pyjwt.readthedocs.io/) - Obsługa tokenów uwierzytelniających.
* [Uvicorn](https://www.uvicorn.org/) - Serwer ASGI.
* [Pytest](https://docs.pytest.org/) & HTTPX - Środowisko testowe.

**Frontend:**
* [Angular](https://angular.io/) (TypeScript) - Tworzenie aplikacji SPA.
* Standalone Components & RxJS.
* Czysty HTML5 i CSS3 (Brak zewnętrznych bibliotek UI dla maksymalnej wydajności).
* [Vitest](https://vitest.dev/) - Nowoczesne i szybkie środowisko testowe.

---

## 🚀 Uruchomienie lokalne (Development)

### 1. Klonowanie repozytorium

```bash
git clone [https://github.com/jozapl/rampy.git](https://github.com/jozapl/rampy.git)
cd nazwa-repozytorium
```

### 2. Konfiguracja Backendu

```bash
# Przejdź do folderu backendu (lub głównego, jeśli pliki są razem)
cd backend

# Utwórz i aktywuj środowisko wirtualne
python3 -m venv venv
source venv/bin/activate  # na Windows: venv\Scripts\activate

# Zainstaluj zależności
pip install fastapi uvicorn pydantic pyjwt pytest httpx

# Uruchom serwer API
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*Przy pierwszym uruchomieniu plik bazy danych `rampy.db` wygeneruje się automatycznie z przykładowymi danymi.*

### 3. Konfiguracja Frontendu

```bash
# W nowym oknie terminala przejdź do folderu frontendu
cd frontend

# Zainstaluj pakiety npm
npm install

# Uruchom serwer deweloperski Angulara
ng serve
```
Aplikacja kliencka będzie dostępna pod adresem: `http://localhost:4200`

---

## 🔑 Domyślne dane logowania
Po pierwszym uruchomieniu system generuje domyślne konto głównego administratora:
* **Użytkownik:** `admin`
* **Hasło:** `admin123`

*(Pamiętaj o zmianie hasła lub wygenerowaniu nowego konta przed wdrożeniem na produkcję!)*

---

## 🧪 Testy

Projekt posiada kompleksowe pokrycie testami warstwy serwerowej i klienckiej.

**Backend (Pytest):**
```bash
pytest test_main.py -v
```
*Testy używają izolowanej bazy danych `test_rampy.db`.*

**Frontend (Vitest / Angular):**
```bash
ng test
```

---

## 🌍 Wdrożenie (Deploy na VPS)

Projekt jest przystosowany do wdrożenia na lekkich serwerach VPS (np. Alpine Linux na mikr.us).
1. **Frontend** budowany jest poleceniem `ng build` i serwowany za pomocą statycznego serwera **Nginx**.
2. **Backend** działa jako proces w tle przy użyciu narzędzia **tmux** i serwera **Uvicorn**.

---

## 📄 Licencja
Projekt udostępniany na licencji MIT.
