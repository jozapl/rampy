import { Component, ChangeDetectorRef, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders, HttpClientModule } from '@angular/common/http';
import { ApiService, RampaEvent } from './api';

@Component({
  selector: 'app-root', standalone: true, imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './app.html', styleUrls: ['./app.css']
})
export class App implements OnInit, OnDestroy {
  isLoggedIn = false;
  appToken = '';
  userRole = '';
  loginUser = '';
  loginPass = '';

  selectedDate = new Date().toISOString().split('T')[0];
  autoRefreshEnabled = true;
  autoRefreshMinutes = 1;
  autoScrollEnabled = false;
  autoScrollSpeed = 1;
  showSettings = false;
  selectedEvent: any = null;
  pixelsPerHour = 100;
  rowIndices: number[] = [];
  markerHours: number[] = [];
  resources: string[] = [];
  groupedEvents: { [key: string]: any[] } = {};
  
  private refreshId: any;
  private scrollId: any;
  private scrollDir = 1;
  private startDateTime: Date = new Date();

  isAdminView = false;
  adminTab = 'awizacje';
  adminAwizacje: any[] = [];
  adminUsers: any[] = [];
  slowniki: any = { ramp: [], przewoznikow: [], kierowcow: [], towarow: [] };
  wybranySlownikTyp = 'ramp';
  ustawieniaG: any = { auto_refresh: false, refresh_min: 1, auto_scroll: false, scroll_speed: 1 };
  
  showAwizacjaModal = false;
  showSlownikModal = false;
  showUserModal = false;
  
  editRampa: any = this.getEmptyRampa();
  editSlownikItem: any = { id: null, nazwa: '' };
  newUser: any = { username: '', password: '', role: 'Pracownik' };

  private apiUrl = 'http://localhost:8000/api';

  constructor(private api: ApiService, private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    const savedToken = localStorage.getItem('app_token');
    if (savedToken) {
      this.appToken = savedToken;
      try {
        const payload = JSON.parse(atob(this.appToken.split('.')[1]));
        this.userRole = payload.role;
        this.loginUser = payload.sub;
        this.isLoggedIn = true;
        this.initApp();
      } catch (e) {
        this.logout();
      }
    }
  }

  getHeaders() { 
    return new HttpHeaders().set('Authorization', `Bearer ${this.appToken}`); 
  }

  login() {
    const formData = new URLSearchParams();
    formData.set('username', this.loginUser);
    formData.set('password', this.loginPass);

    this.http.post<{access_token: string, role: string}>(`${this.apiUrl}/auth/login`, formData.toString(), {
      headers: new HttpHeaders().set('Content-Type', 'application/x-www-form-urlencoded')
    }).subscribe({
      next: (res) => {
        this.appToken = res.access_token;
        this.userRole = res.role;
        localStorage.setItem('app_token', this.appToken);
        this.isLoggedIn = true;
        this.initApp();
      },
      error: () => alert('Nieprawidłowy użytkownik lub hasło!')
    });
  }

  logout() {
    this.isLoggedIn = false;
    this.appToken = '';
    this.userRole = '';
    this.loginPass = '';
    this.isAdminView = false;
    clearInterval(this.refreshId);
    clearInterval(this.scrollId);
    localStorage.removeItem('app_token');
  }

  initApp() {
    this.pobierzUstawieniaGlobalne();
    this.loadData();
    this.toggleAutoRefresh();
  }

  pobierzUstawieniaGlobalne() {
    this.http.get<any>(`${this.apiUrl}/ustawienia`, { headers: this.getHeaders() }).subscribe({
      next: (d) => {
        this.ustawieniaG.auto_refresh = d.auto_refresh === '1';
        this.ustawieniaG.refresh_min = parseInt(d.refresh_min);
        this.ustawieniaG.auto_scroll = d.auto_scroll === '1';
        this.ustawieniaG.scroll_speed = parseInt(d.scroll_speed);
        
        this.autoRefreshEnabled = this.ustawieniaG.auto_refresh;
        this.autoRefreshMinutes = this.ustawieniaG.refresh_min;
        this.autoScrollEnabled = this.ustawieniaG.auto_scroll;
        this.autoScrollSpeed = this.ustawieniaG.scroll_speed;
        
        this.toggleAutoRefresh();
        this.toggleAutoScroll();
      },
      error: () => this.logout()
    });
  }

  loadData() {
    this.http.get<any[]>(`${this.apiUrl}/rampy?dzien=${this.selectedDate}`, { headers: this.getHeaders() })
    .subscribe({
      next: (data) => {
        const evs = (data || []).filter(e => e.rampa);
        if (this.isAdminView) this.adminAwizacje = evs;
        if (!evs.length) {
          this.rowIndices = [];
          this.markerHours = [];
          this.resources = [];
          this.groupedEvents = {};
          this.cdr.detectChanges();
          return;
        }

        const minDate = new Date(Math.min(...evs.map(e => new Date(e.DataOd).getTime())));
        const maxDate = new Date(Math.max(...evs.map(e => new Date(e.DataDo).getTime())));

        const start = new Date(minDate.getTime());
        start.setHours(start.getHours() - 1);
        this.startDateTime = start;

        const totalHours = Math.ceil((maxDate.getTime() - start.getTime()) / 3600000) + 1;

        this.rowIndices = Array.from({ length: totalHours }, (_, i) => i);
        this.markerHours = Array.from({ length: totalHours }, (_, i) => {
          const h = new Date(start.getTime() + i * 3600000).getHours();
          return h;
        });

        this.groupedEvents = {};
        const resSet = new Set<string>();
        evs.forEach(e => {
          resSet.add(e.rampa);
          if (!this.groupedEvents[e.rampa]) this.groupedEvents[e.rampa] = [];
          this.groupedEvents[e.rampa].push(e);
        });
        this.resources = Array.from(resSet).sort();
        this.cdr.detectChanges();
        if (this.autoScrollEnabled) this.toggleAutoScroll();
      },
      error: () => this.logout()
    });
  }

  openDetails(e: any, event: MouseEvent) { event.stopPropagation(); this.selectedEvent = e; }
  closeDetails() { this.selectedEvent = null; }

  getEventColor(e: any): string {
    const s = (e.status || '').toUpperCase();
    if (s.includes('NOWY')) return '#ff4d4d';           
    if (s.includes('ZAPLANOWANY')) return '#f1c40f';    
    if (s.includes('W PRZYGOTOWANIU')) return '#ffa500'; 
    if (s.includes('NA PLACU')) return '#d199ff';        
    if (s.includes('W ZAŁADUNKU')) return '#3498db';     
    if (s.includes('W DRODZE')) return '#1abc9c';       
    if (s.includes('OPÓŹNIONY')) return '#e74c3c';      
    if (s.includes('ZAKOŃCZONA')) return '#2ecc71';     
    if (s.includes('ANULOWANA')) return '#7f8c8d';      
    if (s.includes('AWARIA')) return '#ff0000';         
    return '#ffffff';
  }

  getEventStyle(e: any) {
    const s = new Date(e.DataOd), en = new Date(e.DataDo);
    const top = (s.getTime() - this.startDateTime.getTime()) / 3600000 * this.pixelsPerHour;
    const h = (en.getTime() - s.getTime()) / 3600000 * this.pixelsPerHour;
    return { top: top + 'px', height: h + 'px', background: this.getEventColor(e) };
  }

  changeDate(d: number) {
    const date = new Date(this.selectedDate);
    date.setDate(date.getDate() + d);
    this.selectedDate = date.toISOString().split('T')[0];
    this.loadData();
  }

  onDateChange() { this.loadData(); }

  toggleAutoRefresh() {
    if (this.refreshId) clearInterval(this.refreshId);
    if (this.autoRefreshEnabled) this.refreshId = setInterval(() => this.loadData(), this.autoRefreshMinutes * 60000);
  }

  toggleAutoScroll() {
    if (this.scrollId) clearInterval(this.scrollId);
    if (this.autoScrollEnabled) {
      this.scrollId = setInterval(() => {
        const cur = window.scrollY, max = document.documentElement.scrollHeight - window.innerHeight;
        if (this.scrollDir === 1 && cur >= max) this.scrollDir = -1;
        else if (this.scrollDir === -1 && cur <= 0) this.scrollDir = 1;
        window.scrollBy(0, this.autoScrollSpeed * this.scrollDir);
      }, 30);
    }
  }

  formatTime(iso: string) { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
  ngOnDestroy() { clearInterval(this.refreshId); clearInterval(this.scrollId); }

  openAdminPanel() {
    this.isAdminView = true;
    this.loadData();
    this.loadSlowniki();
    this.loadUsers();
  }

  setAdminTab(t: string) { this.adminTab = t; }

  getEmptyRampa() {
    return { id: null, data_od: '', data_do: '', dokument: '', rampa: '', status: 'NOWY', pojazd: '', kierowca: '', wystawca: '', przewoznik: '', skad_nazwa: '', skad_miasto: '', dokad_nazwa: '', dokad_miasto: '', towar: '', ilosc: 1, info: '' };
  }

  copyEvent(e: any) {
    return {
      id: e.id, 
      data_od: e.DataOd ? e.DataOd.slice(0, 16) : '', 
      data_do: e.DataDo ? e.DataDo.slice(0, 16) : '', 
      dokument: e.dokument, rampa: e.rampa, status: e.status,
      pojazd: e.pojazd, kierowca: e.kierowca, wystawca: e.wystawca, przewoznik: e.przewoznik,
      skad_nazwa: e.skad_nazwa, skad_miasto: e.skad_miasto, dokad_nazwa: e.dokad_nazwa, dokad_miasto: e.dokad_miasto,
      towar: e.towar, ilosc: e.ilosc, info: e.info
    };
  }

  openAddAwizacja() { this.editRampa = this.getEmptyRampa(); this.showAwizacjaModal = true; }
  openEditAwizacja(a: any) { this.editRampa = this.copyEvent(a); this.showAwizacjaModal = true; }
  closeAwizacjaModal() { this.showAwizacjaModal = false; }

  saveAwizacja() {
    const r = this.editRampa;
    if (!r.data_od || !r.data_do || !r.dokument || !r.rampa || !r.status || !r.pojazd || !r.kierowca || !r.wystawca || !r.przewoznik || !r.skad_nazwa || !r.skad_miasto || !r.dokad_nazwa || !r.dokad_miasto || !r.towar || r.ilosc === null || r.ilosc === undefined || r.ilosc === '') {
      alert('Wypełnij wszystkie obowiązkowe pola (tylko Info jest opcjonalne).');
      return;
    }
    const isUpdate = r.id != null;
    const req = isUpdate ? this.http.put(`${this.apiUrl}/rampy/${r.id}`, r, { headers: this.getHeaders() })
                         : this.http.post(`${this.apiUrl}/rampy`, r, { headers: this.getHeaders() });
    req.subscribe({
      next: () => { this.loadData(); this.closeAwizacjaModal(); },
      error: () => alert('Błąd walidacji danych')
    });
  }

  updateStatus(id: number, status: string) {
    this.http.patch(`${this.apiUrl}/rampy/${id}/status`, { status }, { headers: this.getHeaders() }).subscribe(() => this.loadData());
  }

  deleteAwizacja(id: number) {
    if (confirm('Usunąć awizację?')) {
      this.http.delete(`${this.apiUrl}/rampy/${id}`, { headers: this.getHeaders() }).subscribe(() => this.loadData());
    }
  }

  loadSlowniki() {
    ['ramp', 'przewoznikow', 'kierowcow', 'towarow'].forEach(typ => {
      this.http.get<any[]>(`${this.apiUrl}/slowniki/${typ}`, { headers: this.getHeaders() }).subscribe(d => this.slowniki[typ] = d);
    });
  }

  openAddSlownik() { this.editSlownikItem = { id: null, nazwa: '' }; this.showSlownikModal = true; }
  openEditSlownik(item: any) { this.editSlownikItem = { id: item.id, nazwa: item.nazwa }; this.showSlownikModal = true; }
  closeSlownikModal() { this.showSlownikModal = false; }

  saveSlownik() {
    if (!this.editSlownikItem.nazwa.trim()) {
      alert('Nazwa jest obowiązkowa.');
      return;
    }
    if (this.editSlownikItem.id) {
      this.http.put(`${this.apiUrl}/slowniki/${this.wybranySlownikTyp}/${this.editSlownikItem.id}`, { nazwa: this.editSlownikItem.nazwa }, { headers: this.getHeaders() })
        .subscribe(() => { this.loadSlowniki(); this.closeSlownikModal(); });
    } else {
      this.http.post(`${this.apiUrl}/slowniki/${this.wybranySlownikTyp}`, { nazwa: this.editSlownikItem.nazwa }, { headers: this.getHeaders() })
        .subscribe(() => { this.loadSlowniki(); this.closeSlownikModal(); });
    }
  }

  deleteSlownik(id: number) {
    if (confirm('Usunąć pozycję ze słownika?')) {
      this.http.delete(`${this.apiUrl}/slowniki/${this.wybranySlownikTyp}/${id}`, { headers: this.getHeaders() }).subscribe(() => this.loadSlowniki());
    }
  }

  zapiszUstawieniaGlobalne() {
    this.http.put(`${this.apiUrl}/ustawienia`, this.ustawieniaG, { headers: this.getHeaders() })
      .subscribe(() => { alert('Zapisano ustawienia globalne'); this.pobierzUstawieniaGlobalne(); });
  }

  loadUsers() {
    if (this.userRole !== 'Admin') return;
    this.http.get<any[]>(`${this.apiUrl}/uzytkownicy`, { headers: this.getHeaders() }).subscribe(d => this.adminUsers = d);
  }

  openAddUser() { this.newUser = { username: '', password: '', role: 'Pracownik' }; this.showUserModal = true; }
  closeUserModal() { this.showUserModal = false; }

  saveUser() {
    if (!this.newUser.username || !this.newUser.password || !this.newUser.role) {
      alert('Wszystkie pola są obowiązkowe.');
      return;
    }
    this.http.post(`${this.apiUrl}/uzytkownicy`, this.newUser, { headers: this.getHeaders() })
      .subscribe({
        next: () => { this.loadUsers(); this.closeUserModal(); alert('Dodano pracownika'); },
        error: (e) => alert(e.error.detail || 'Błąd podczas tworzenia')
      });
  }

  deleteUser(id: number) {
    if (confirm('Trwale usunąć tego użytkownika?')) {
      this.http.delete(`${this.apiUrl}/uzytkownicy/${id}`, { headers: this.getHeaders() }).subscribe(() => this.loadUsers());
    }
  }
}