from fastapi import FastAPI, Query, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from sqlite3 import connect, Row, IntegrityError
from os import path
from contextlib import asynccontextmanager
from uvicorn import run as uvicorn_run
import jwt

DB_FILE = "rampy.db"
SECRET_KEY = "super-tajny-klucz-jwt"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class RampaCreate(BaseModel):
    data_od: str
    data_do: str
    dokument: str
    rampa: str
    status: str
    pojazd: str
    kierowca: str
    wystawca: str
    przewoznik: str
    skad_nazwa: str
    skad_miasto: str
    dokad_nazwa: str
    dokad_miasto: str
    towar: str
    ilosc: int
    info: str = ""

class StatusUpdate(BaseModel):
    status: str

class UstawieniaUpdate(BaseModel):
    auto_refresh: bool
    refresh_min: int
    auto_scroll: bool
    scroll_speed: int

class SlownikItem(BaseModel):
    nazwa: str

class UzytkownikCreate(BaseModel):
    username: str
    password: str
    role: str

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token wygasł")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy token")

def validate_rampa(rampa: RampaCreate):
    required_fields = [
        rampa.data_od, rampa.data_do, rampa.dokument, rampa.rampa, rampa.status,
        rampa.pojazd, rampa.kierowca, rampa.wystawca, rampa.przewoznik,
        rampa.skad_nazwa, rampa.skad_miasto, rampa.dokad_nazwa, rampa.dokad_miasto, rampa.towar
    ]
    if any(not str(f).strip() for f in required_fields) or rampa.ilosc is None:
        raise HTTPException(status_code=400, detail="Wszystkie pola poza info są obowiązkowe")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not path.exists(DB_FILE):
        conn = connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE rampy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_od TEXT,
                data_do TEXT,
                dokument TEXT,
                rampa TEXT,
                status TEXT,
                pojazd TEXT,
                kierowca TEXT,
                wystawca TEXT,
                przewoznik TEXT,
                skad_nazwa TEXT,
                skad_miasto TEXT,
                dokad_nazwa TEXT,
                dokad_miasto TEXT,
                towar TEXT,
                ilosc INTEGER,
                info TEXT
            )
        """
        )
        c.execute("CREATE TABLE slownik_ramp (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT)")
        c.execute("CREATE TABLE slownik_przewoznikow (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT)")
        c.execute("CREATE TABLE slownik_kierowcow (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT)")
        c.execute("CREATE TABLE slownik_towarow (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT)")
        c.execute("CREATE TABLE ustawienia (klucz TEXT PRIMARY KEY, wartosc TEXT)")
        c.execute("CREATE TABLE uzytkownicy (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)")

        ustawienia_init = [
            ("auto_refresh", "1"), ("refresh_min", "1"), 
            ("auto_scroll", "0"), ("scroll_speed", "1")
        ]
        c.executemany("INSERT INTO ustawienia (klucz, wartosc) VALUES (?, ?)", ustawienia_init)

        c.execute("INSERT INTO uzytkownicy (username, password, role) VALUES ('admin', 'admin123', 'Admin')")

        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        example_data = []
        ramp_names = [
            "Rampa Alfa", "Rampa Beta", "Rampa Gamma", "Rampa Delta", "Rampa Epsilon",
            "Rampa Zeta", "Rampa Eta", "Rampa Theta", "Rampa Iota", "Rampa Kappa",
        ]
        statuses = [
            "NOWY", "ZAPLANOWANY", "W PRZYGOTOWANIU", "NA PLACU", "W ZAŁADUNKU",
            "W DRODZE", "OPÓŹNIONY", "ZAKOŃCZONA", "ANULOWANA", "AWARIA"
        ]
        kierowcy = [
            "Jan Kowalski", "Anna Nowak", "Piotr Zielinski", "Katarzyna Wiśniewska",
            "Marek Kaczmarek", "Anna Kowalska", "Marek Wiśniewski", "Janina Kaczmarek", "Katarzyna Nowak",
        ]
        przewoznicy = [
            "Przewoznik A", "Przewoznik B", "Przewoznik C",
            "Przewoznik D", "Przewoznik E", "Przewoznik F",
        ]
        towary = [
            "Blacha HRS", "Taśma g/w", "Profil 20x20", "Rura 42mm", "Taśma ocynk",
            "Profil 30x30", "Blacha traw.", "Taśma z/w", "Profil 40x40", "Rura 50mm",
        ]
        miasta = [
            "Miasto A", "Miasto B", "Miasto C", "Miasto D", "Miasto E",
            "Miasto F", "Miasto G", "Miasto H", "Miasto I", "Miasto J",
        ]

        c.executemany("INSERT INTO slownik_ramp (nazwa) VALUES (?)", [(r,) for r in ramp_names])
        c.executemany("INSERT INTO slownik_przewoznikow (nazwa) VALUES (?)", [(p,) for p in przewoznicy])
        c.executemany("INSERT INTO slownik_kierowcow (nazwa) VALUES (?)", [(k,) for k in kierowcy])
        c.executemany("INSERT INTO slownik_towarow (nazwa) VALUES (?)", [(t,) for t in towary])

        for i in range(50):
            start = now + timedelta(hours=i)
            end = start + timedelta(hours=(i % 5 + 1))
            example_data.append(
                (
                    start.isoformat(), end.isoformat(), f"DOK{i+100}", ramp_names[i % len(ramp_names)],
                    statuses[i % len(statuses)], f"POJ{i+100}", kierowcy[i % len(kierowcy)],
                    f"Wystawca {i+1}", przewoznicy[i % len(przewoznicy)], miasta[i % len(miasta)],
                    f"Plac {i+1}", miasta[(i + 1) % len(miasta)], miasta[(i + 1) % len(miasta)],
                    towary[i % len(towary)], (i % 20) + 1, f"Info {i+1}",
                )
            )
        c.executemany(
            """
            INSERT INTO rampy (data_od, data_do, dokument, rampa, status, pojazd, kierowca, wystawca, przewoznik,
                               skad_nazwa, skad_miasto, dokad_nazwa, dokad_miasto, towar, ilosc, info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            example_data,
        )
        conn.commit()
        conn.close()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = connect(DB_FILE)
    conn.row_factory = Row
    c = conn.cursor()
    c.execute("SELECT * FROM uzytkownicy WHERE username=? AND password=?", (form_data.username, form_data.password))
    user = c.fetchone()
    conn.close()
    
    if user:
        access_token = jwt.encode(
            {"sub": user["username"], "role": user["role"], "exp": datetime.utcnow() + timedelta(hours=8)}, 
            SECRET_KEY, algorithm=ALGORITHM
        )
        return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}
    
    raise HTTPException(status_code=400, detail="Nieprawidłowy użytkownik lub hasło")

@app.get("/api/rampy")
def get_rampy(dzien: date = Query(default=date.today()), token: dict = Depends(verify_token)):
    conn = connect(DB_FILE)
    conn.row_factory = Row
    c = conn.cursor()
    start_day = datetime.combine(dzien, datetime.min.time()).isoformat()
    end_day = (
        datetime.combine(dzien, datetime.min.time()) + timedelta(days=1)
    ).isoformat()
    c.execute(
        """
        SELECT * FROM rampy
        WHERE (data_od >= ? AND data_od < ?) OR (data_do > ? AND data_od < ?)
        ORDER BY data_od ASC
    """,
        (start_day, end_day, start_day, end_day),
    )
    rows = c.fetchall()
    results = []
    for r in rows:
        results.append(
            {
                "id": r["id"], "DataOd": r["data_od"], "DataDo": r["data_do"], "dokument": r["dokument"],
                "rampa": r["rampa"], "status": r["status"], "pojazd": r["pojazd"], "kierowca": r["kierowca"],
                "wystawca": r["wystawca"], "przewoznik": r["przewoznik"], "skad_nazwa": r["skad_nazwa"],
                "skad_miasto": r["skad_miasto"], "dokad_nazwa": r["dokad_nazwa"], "dokad_miasto": r["dokad_miasto"],
                "towar": r["towar"], "ilosc": r["ilosc"], "info": r["info"],
            }
        )
    conn.close()
    return results

@app.post("/api/rampy")
def create_rampa(rampa: RampaCreate, token: dict = Depends(verify_token)):
    validate_rampa(rampa)
    conn = connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO rampy (data_od, data_do, dokument, rampa, status, pojazd, kierowca, wystawca, przewoznik,
                           skad_nazwa, skad_miasto, dokad_nazwa, dokad_miasto, towar, ilosc, info)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (rampa.data_od, rampa.data_do, rampa.dokument, rampa.rampa, rampa.status, rampa.pojazd, rampa.kierowca,
          rampa.wystawca, rampa.przewoznik, rampa.skad_nazwa, rampa.skad_miasto, rampa.dokad_nazwa, 
          rampa.dokad_miasto, rampa.towar, rampa.ilosc, rampa.info))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return {"id": new_id, "message": "Utworzono awizację"}

@app.put("/api/rampy/{id}")
def update_rampa(id: int, rampa: RampaCreate, token: dict = Depends(verify_token)):
    validate_rampa(rampa)
    conn = connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        UPDATE rampy SET data_od=?, data_do=?, dokument=?, rampa=?, status=?, pojazd=?, kierowca=?, 
        wystawca=?, przewoznik=?, skad_nazwa=?, skad_miasto=?, dokad_nazwa=?, dokad_miasto=?, 
        towar=?, ilosc=?, info=? WHERE id=?
    """, (rampa.data_od, rampa.data_do, rampa.dokument, rampa.rampa, rampa.status, rampa.pojazd, rampa.kierowca,
          rampa.wystawca, rampa.przewoznik, rampa.skad_nazwa, rampa.skad_miasto, rampa.dokad_nazwa, 
          rampa.dokad_miasto, rampa.towar, rampa.ilosc, rampa.info, id))
    conn.commit()
    conn.close()
    return {"message": "Zaktualizowano awizację"}

@app.patch("/api/rampy/{id}/status")
def update_status(id: int, status_data: StatusUpdate, token: dict = Depends(verify_token)):
    conn = connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE rampy SET status=? WHERE id=?", (status_data.status, id))
    conn.commit()
    conn.close()
    return {"message": "Status zaktualizowany"}

@app.delete("/api/rampy/{id}")
def delete_rampa(id: int, token: dict = Depends(verify_token)):
    conn = connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM rampy WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"message": "Usunięto rekord"}

@app.get("/api/slowniki/{typ}")
def get_slownik(typ: str, token: dict = Depends(verify_token)):
    valid_types = ["ramp", "przewoznikow", "kierowcow", "towarow"]
    if typ not in valid_types:
        raise HTTPException(status_code=400, detail="Nieprawidłowy słownik")
    conn = connect(DB_FILE)
    conn.row_factory = Row
    c = conn.cursor()
    c.execute(f"SELECT * FROM slownik_{typ} ORDER BY nazwa ASC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/slowniki/{typ}")
def add_slownik(typ: str, item: SlownikItem, token: dict = Depends(verify_token)):
    valid_types = ["ramp", "przewoznikow", "kierowcow", "towarow"]
    if typ not in valid_types:
        raise HTTPException(status_code=400, detail="Nieprawidłowy słownik")
    conn = connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"INSERT INTO slownik_{typ} (nazwa) VALUES (?)", (item.nazwa,))
    conn.commit()
    conn.close()
    return {"message": "Dodano pozycję"}

@app.put("/api/slowniki/{typ}/{id}")
def update_slownik(typ: str, id: int, item: SlownikItem, token: dict = Depends(verify_token)):
    valid_types = ["ramp", "przewoznikow", "kierowcow", "towarow"]
    if typ not in valid_types:
        raise HTTPException(status_code=400, detail="Nieprawidłowy słownik")
    conn = connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"UPDATE slownik_{typ} SET nazwa=? WHERE id=?", (item.nazwa, id))
    conn.commit()
    conn.close()
    return {"message": "Zaktualizowano pozycję"}

@app.delete("/api/slowniki/{typ}/{id}")
def delete_slownik(typ: str, id: int, token: dict = Depends(verify_token)):
    valid_types = ["ramp", "przewoznikow", "kierowcow", "towarow"]
    if typ not in valid_types:
        raise HTTPException(status_code=400, detail="Nieprawidłowy słownik")
    conn = connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"DELETE FROM slownik_{typ} WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"message": "Usunięto pozycję"}

@app.get("/api/ustawienia")
def get_ustawienia(token: dict = Depends(verify_token)):
    conn = connect(DB_FILE)
    conn.row_factory = Row
    c = conn.cursor()
    c.execute("SELECT * FROM ustawienia")
    rows = c.fetchall()
    conn.close()
    return {r["klucz"]: r["wartosc"] for r in rows}

@app.put("/api/ustawienia")
def update_ustawienia(ust: UstawieniaUpdate, token: dict = Depends(verify_token)):
    if token.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Tylko administrator może zmieniać ustawienia")
    conn = connect(DB_FILE)
    c = conn.cursor()
    params = [
        ("1" if ust.auto_refresh else "0", "auto_refresh"),
        (str(ust.refresh_min), "refresh_min"),
        ("1" if ust.auto_scroll else "0", "auto_scroll"),
        (str(ust.scroll_speed), "scroll_speed")
    ]
    c.executemany("UPDATE ustawienia SET wartosc=? WHERE klucz=?", params)
    conn.commit()
    conn.close()
    return {"message": "Zaktualizowano ustawienia"}

@app.get("/api/uzytkownicy")
def get_users(token: dict = Depends(verify_token)):
    if token.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    conn = connect(DB_FILE)
    conn.row_factory = Row
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM uzytkownicy")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/uzytkownicy")
def create_user(user: UzytkownikCreate, token: dict = Depends(verify_token)):
    if token.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    conn = connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO uzytkownicy (username, password, role) VALUES (?, ?, ?)", 
                  (user.username, user.password, user.role))
        conn.commit()
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Użytkownik o takiej nazwie już istnieje")
    finally:
        conn.close()
    return {"message": "Utworzono użytkownika"}

@app.delete("/api/uzytkownicy/{id}")
def delete_user(id: int, token: dict = Depends(verify_token)):
    if token.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    conn = connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM uzytkownicy WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"message": "Usunięto użytkownika"}

if __name__ == "__main__":
    uvicorn_run(app, host="0.0.0.0", port=8000)