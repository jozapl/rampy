import { TestBed, ComponentFixture } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { App } from './app';
import { ApiService } from './api';
import { vi } from 'vitest';

class MockApiService {
  getData() {
    return { subscribe: () => {} };
  }
}

describe('App', () => {
  let component: App;
  let fixture: ComponentFixture<App>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App, HttpClientTestingModule, FormsModule],
      providers: [
        { provide: ApiService, useClass: MockApiService }
      ]
    })
    .overrideComponent(App, {
      remove: { imports: [HttpClientModule] }
    })
    .compileComponents();

    localStorage.clear();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(App);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
    vi.restoreAllMocks();
  });

  it('should create the app', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize settings on init', () => {
    component.appToken = 'fake-token';
    component.pobierzUstawieniaGlobalne();

    const req = httpMock.expectOne('http://localhost:8000/api/ustawienia');
    expect(req.request.method).toBe('GET');
    req.flush({ auto_refresh: '1', refresh_min: '5', auto_scroll: '0', scroll_speed: '2' });

    expect(component.ustawieniaG.auto_refresh).toBe(true);
    expect(component.ustawieniaG.refresh_min).toBe(5);
    expect(component.ustawieniaG.auto_scroll).toBe(false);
    expect(component.ustawieniaG.scroll_speed).toBe(2);
  });

  it('should login successfully', () => {
    component.loginUser = 'admin';
    component.loginPass = 'admin123';
    
    // Zatrzymujemy wywołanie initApp, aby nie generowało dodatkowych zapytań HTTP w tym teście
    const initAppSpy = vi.spyOn(component, 'initApp').mockImplementation(() => {});

    component.login();

    const req = httpMock.expectOne('http://localhost:8000/api/auth/login');
    expect(req.request.method).toBe('POST');
    req.flush({ access_token: 'fake-jwt-token', role: 'Admin' });

    expect(initAppSpy).toHaveBeenCalled();
    expect(component.appToken).toBe('fake-jwt-token');
    expect(component.userRole).toBe('Admin');
    expect(component.isLoggedIn).toBe(true);
    expect(localStorage.getItem('app_token')).toBe('fake-jwt-token');
  });

  it('should handle login error', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    component.loginUser = 'wrong';
    component.loginPass = 'wrong';

    component.login();

    const req = httpMock.expectOne('http://localhost:8000/api/auth/login');
    req.flush('Unauthorized', { status: 400, statusText: 'Bad Request' });

    expect(component.isLoggedIn).toBe(false);
    expect(alertSpy).toHaveBeenCalledWith('Nieprawidłowy użytkownik lub hasło!');
  });

  it('should logout correctly', () => {
    component.isLoggedIn = true;
    component.appToken = 'some-token';
    component.userRole = 'Admin';
    localStorage.setItem('app_token', 'some-token');

    component.logout();

    expect(component.isLoggedIn).toBe(false);
    expect(component.appToken).toBe('');
    expect(component.userRole).toBe('');
    expect(localStorage.getItem('app_token')).toBeNull();
  });

  it('should load data and group events correctly', () => {
    component.isLoggedIn = true;
    component.appToken = 'fake-token';
    component.selectedDate = '2026-05-01';

    component.loadData();

    const req = httpMock.expectOne('http://localhost:8000/api/rampy?dzien=2026-05-01');
    expect(req.request.method).toBe('GET');

    const mockEvents = [
      { id: 1, DataOd: '2026-05-01T10:00:00', DataDo: '2026-05-01T12:00:00', rampa: 'Rampa A', status: 'NOWY' },
      { id: 2, DataOd: '2026-05-01T11:00:00', DataDo: '2026-05-01T13:00:00', rampa: 'Rampa B', status: 'ZAPLANOWANY' },
      { id: 3, DataOd: '2026-05-01T14:00:00', DataDo: '2026-05-01T15:00:00', rampa: 'Rampa A', status: 'W ZAŁADUNKU' }
    ];

    req.flush(mockEvents);

    expect(component.resources.length).toBe(2);
    expect(component.resources).toContain('Rampa A');
    expect(component.resources).toContain('Rampa B');
    expect(component.groupedEvents['Rampa A'].length).toBe(2);
    expect(component.groupedEvents['Rampa B'].length).toBe(1);
  });

  it('should map event colors correctly', () => {
    expect(component.getEventColor({ status: 'NOWY' })).toBe('#ff4d4d');
    expect(component.getEventColor({ status: 'ZAPLANOWANY' })).toBe('#f1c40f');
    expect(component.getEventColor({ status: 'W ZAŁADUNKU' })).toBe('#3498db');
    expect(component.getEventColor({ status: 'ZAKOŃCZONA' })).toBe('#2ecc71');
    expect(component.getEventColor({ status: 'AWARIA' })).toBe('#ff0000');
    expect(component.getEventColor({ status: 'NIEZNANY' })).toBe('#ffffff');
  });

  it('should format time correctly', () => {
    const formatted = component.formatTime('2026-05-01T14:30:00');
    expect(formatted).toMatch(/14:30/);
  });

  it('should change date correctly', () => {
    const loadDataSpy = vi.spyOn(component, 'loadData').mockImplementation(() => {});
    component.selectedDate = '2026-05-02';
    
    component.changeDate(-1);
    
    expect(component.selectedDate).toBe('2026-05-01');
    expect(loadDataSpy).toHaveBeenCalled();
  });

  it('should save awizacja correctly', () => {
    component.isLoggedIn = true;
    component.appToken = 'fake-token';
    component.editRampa = {
      id: null,
      data_od: '2026-05-01T10:00',
      data_do: '2026-05-01T12:00',
      dokument: 'DOK1',
      rampa: 'Rampa A',
      status: 'NOWY',
      pojazd: 'WA123',
      kierowca: 'Jan',
      wystawca: 'W1',
      przewoznik: 'P1',
      skad_nazwa: 'S1',
      skad_miasto: 'M1',
      dokad_nazwa: 'D1',
      dokad_miasto: 'M2',
      towar: 'T1',
      ilosc: 10
    };

    const loadDataSpy = vi.spyOn(component, 'loadData').mockImplementation(() => {});
    const closeAwizacjaModalSpy = vi.spyOn(component, 'closeAwizacjaModal').mockImplementation(() => {});

    component.saveAwizacja();

    const req = httpMock.expectOne('http://localhost:8000/api/rampy');
    expect(req.request.method).toBe('POST');
    req.flush({ id: 1, message: 'Utworzono' });

    expect(loadDataSpy).toHaveBeenCalled();
    expect(closeAwizacjaModalSpy).toHaveBeenCalled();
  });

  it('should reject invalid awizacja', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    component.editRampa = component.getEmptyRampa();
    
    component.saveAwizacja();
    
    expect(alertSpy).toHaveBeenCalledWith('Wypełnij wszystkie obowiązkowe pola (tylko Info jest opcjonalne).');
  });

  it('should load dictionaries correctly', () => {
    component.isLoggedIn = true;
    component.appToken = 'fake-token';
    
    component.loadSlowniki();

    const reqRamp = httpMock.expectOne('http://localhost:8000/api/slowniki/ramp');
    const reqPrzewoznik = httpMock.expectOne('http://localhost:8000/api/slowniki/przewoznikow');
    const reqKierowca = httpMock.expectOne('http://localhost:8000/api/slowniki/kierowcow');
    const reqTowar = httpMock.expectOne('http://localhost:8000/api/slowniki/towarow');

    expect(reqRamp.request.method).toBe('GET');
    
    reqRamp.flush([{ id: 1, nazwa: 'Rampa A' }]);
    reqPrzewoznik.flush([]);
    reqKierowca.flush([]);
    reqTowar.flush([]);

    expect(component.slowniki.ramp.length).toBe(1);
    expect(component.slowniki.ramp[0].nazwa).toBe('Rampa A');
  });
});