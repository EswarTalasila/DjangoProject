import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface DialogConfig {
  title: string;
  message: string;
  type: 'success' | 'error' | 'confirm';
}

export interface DialogResult {
  confirmed: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class DialogService {
  private dialogSubject = new BehaviorSubject<{config: DialogConfig, callback: (result: DialogResult) => void} | null>(null);

  constructor(private ngZone: NgZone) {}

  showDialog(config: DialogConfig): Observable<DialogResult> {
    return new Observable<DialogResult>(observer => {
      this.ngZone.run(() => {
        this.dialogSubject.next({
          config,
          callback: (result) => {
            observer.next(result);
            observer.complete();
          }
        });
      });
    });
  }

  // New robust method that components can use directly
  showRobustDialog(title: string, message: string, type: 'success' | 'error' | 'confirm', callback?: (confirmed: boolean) => void): void {
    try {
      const dialog$ = this.showDialog({
        title: title,
        message: message,
        type: type
      });

      dialog$.subscribe(result => {
        if (callback) {
          callback(result.confirmed);
        }
      });
    } catch (dialogError) {
      console.error('Dialog service error:', dialogError);
      // Fallback to regular alert
      if (type === 'confirm') {
        const confirmed = confirm(`${title}: ${message}`);
        if (callback) {
          callback(confirmed);
        }
      } else {
        alert(`${title}: ${message}`);
        if (callback) {
          callback(true); // For non-confirm dialogs, assume confirmed/closed
        }
      }
    }
  }

  getDialog() {
    return this.dialogSubject.asObservable();
  }

  closeDialog(result: DialogResult) {
    this.ngZone.run(() => {
      const current = this.dialogSubject.value;
      if (current) {
        current.callback(result);
      }
      this.dialogSubject.next(null);
    });
  }
}