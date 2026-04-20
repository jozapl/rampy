import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RampaEvent {
  DataOd: string;
  DataDo: string;
  dokument: string;
  rampa: string;
  status: string;
  pojazd: string;
  kierowca: string;
  wystawca: string;
  przewoznik: string;
  skad_nazwa: string;
  skad_miasto: string;
  dokad_nazwa: string;
  dokad_miasto: string;
  towar: string;
  ilosc: number;
  info: string;
  [key: string]: any;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private apiUrl = 'http://localhost:8000/api/rampy';
  constructor(private http: HttpClient) {}
  getData(date: string): Observable<RampaEvent[]> {
    return this.http.get<RampaEvent[]>(`${this.apiUrl}?dzien=${date}`);
  }
}