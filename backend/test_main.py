import pytest
from fastapi.testclient import TestClient
import os
import main  # Importuje Twój plik main.py

# Podmieniamy nazwę pliku bazy danych na testową PRZED inicjalizacją klienta
TEST_DB = "test_rampy.db"
main.DB_FILE = TEST_DB

from main import app

# Fixture (przygotowanie środowiska) dla TestClienta
@pytest.fixture(scope="module")
def client():
    # Usunięcie testowej bazy przed startem, jeśli została z poprzedniej sesji
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    # TestClient w bloku 'with' uruchamia funkcję lifespan (tworzy bazę i tabele)
    with TestClient(app) as c:
        yield c
        
    # Czyszczenie: usunięcie testowej bazy danych po zakończeniu wszystkich testów
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

# Fixture logujący administratora i zwracający token
@pytest.fixture(scope="module")
def admin_token(client):
    response = client.post(
        "/api/auth/login", 
        data={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

# ==================== TESTY AUTORYZACJI ====================

def test_login_success(client):
    response = client.post(
        "/api/auth/login", 
        data={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "Admin"

def test_login_failure(client):
    response = client.post(
        "/api/auth/login", 
        data={"username": "admin", "password": "zle_haslo"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Nieprawidłowy użytkownik lub hasło"

# ==================== TESTY HARMONOGRAMU (AWIZACJI) ====================

def test_get_rampy_unauthorized(client):
    response = client.get("/api/rampy")
    assert response.status_code == 401 # Brak tokena

def test_get_rampy_authorized(client, admin_token):
    response = client.get("/api/rampy", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_and_delete_rampa(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "data_od": "2026-05-01T10:00",
        "data_do": "2026-05-01T12:00",
        "dokument": "TEST-DOK-001",
        "rampa": "Rampa Alfa",
        "status": "NOWY",
        "pojazd": "WA12345",
        "kierowca": "Jan Testowy",
        "wystawca": "Firma Testowa",
        "przewoznik": "Trans-Test",
        "skad_nazwa": "Magazyn A",
        "skad_miasto": "Warszawa",
        "dokad_nazwa": "Magazyn B",
        "dokad_miasto": "Kraków",
        "towar": "Palety",
        "ilosc": 10,
        "info": "Dostawa testowa"
    }
    
    # 1. Tworzenie awizacji
    create_resp = client.post("/api/rampy", json=payload, headers=headers)
    assert create_resp.status_code == 200
    rampa_id = create_resp.json()["id"]
    assert rampa_id is not None
    
    # 2. Szybka zmiana statusu
    patch_resp = client.patch(f"/api/rampy/{rampa_id}/status", json={"status": "ZAKOŃCZONA"}, headers=headers)
    assert patch_resp.status_code == 200
    
    # 3. Usunięcie awizacji
    delete_resp = client.delete(f"/api/rampy/{rampa_id}", headers=headers)
    assert delete_resp.status_code == 200

def test_create_rampa_missing_fields(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Brakuje np. pola 'towar' i 'ilosc'
    payload = {
        "data_od": "2026-05-01T10:00",
        "dokument": "TEST"
    }
    response = client.post("/api/rampy", json=payload, headers=headers)
    # FastAPI Pydantic rzuci 422 Unprocessable Entity
    assert response.status_code == 422 

# ==================== TESTY SŁOWNIKÓW ====================

def test_slowniki_crud(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Dodanie nowej rampy
    add_resp = client.post("/api/slowniki/ramp", json={"nazwa": "Rampa Testowa"}, headers=headers)
    assert add_resp.status_code == 200
    
    # 2. Pobranie listy i weryfikacja
    get_resp = client.get("/api/slowniki/ramp", headers=headers)
    assert get_resp.status_code == 200
    rampy = get_resp.json()
    assert any(r["nazwa"] == "Rampa Testowa" for r in rampy)
    
    # Wyciągniecie ID testowej rampy
    rampa_id = next(r["id"] for r in rampy if r["nazwa"] == "Rampa Testowa")
    
    # 3. Usunięcie rampy
    del_resp = client.delete(f"/api/slowniki/ramp/{rampa_id}", headers=headers)
    assert del_resp.status_code == 200

def test_slowniki_invalid_type(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/slowniki/nieistniejacy", headers=headers)
    assert response.status_code == 400

# ==================== TESTY RÓL I UŻYTKOWNIKÓW ====================

def test_create_user_and_permissions(client, admin_token):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Admin tworzy zwykłego pracownika
    new_user = {
        "username": "pracownik1",
        "password": "haslo123",
        "role": "Pracownik"
    }
    resp_create = client.post("/api/uzytkownicy", json=new_user, headers=headers_admin)
    assert resp_create.status_code == 200
    
    # 2. Logowanie pracownika
    resp_login = client.post("/api/auth/login", data={"username": "pracownik1", "password": "haslo123"})
    assert resp_login.status_code == 200
    pracownik_token = resp_login.json()["access_token"]
    headers_pracownik = {"Authorization": f"Bearer {pracownik_token}"}
    
    # 3. Pracownik pobiera harmonogram (dozwolone)
    resp_get = client.get("/api/rampy", headers=headers_pracownik)
    assert resp_get.status_code == 200
    
    # 4. Pracownik próbuje zmienić ustawienia globalne (zabronione - tylko dla Admina)
    new_settings = {
        "auto_refresh": True, "refresh_min": 5, "auto_scroll": False, "scroll_speed": 1
    }
    resp_settings = client.put("/api/ustawienia", json=new_settings, headers=headers_pracownik)
    assert resp_settings.status_code == 403
    assert resp_settings.json()["detail"] == "Tylko administrator może zmieniać ustawienia"
    
    # 5. Pracownik próbuje pobrać listę użytkowników (zabronione)
    resp_users = client.get("/api/uzytkownicy", headers=headers_pracownik)
    assert resp_users.status_code == 403