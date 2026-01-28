import { Component, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DialogService, DialogConfig, DialogResult } from '../../../services/dialog.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-custom-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './custom-dialog.component.html',
  styleUrls: ['./custom-dialog.component.scss']
})
export class CustomDialogComponent implements OnDestroy {
  currentDialog: {config: DialogConfig, callback: (result: DialogResult) => void} | null = null;
  private dialogSubscription: Subscription;

  constructor(private dialogService: DialogService) {
    this.dialogSubscription = this.dialogService.getDialog().subscribe(dialog => {
      this.currentDialog = dialog;
    });
  }

  ngOnDestroy() {
    if (this.dialogSubscription) {
      this.dialogSubscription.unsubscribe();
    }
  }

  get dialogConfig(): DialogConfig | null {
    return this.currentDialog?.config || null;
  }

  get typeClass(): string {
    if (!this.dialogConfig) return '';
    return `dialog-${this.dialogConfig.type}`;
  }

  get icon(): string {
    switch (this.dialogConfig?.type) {
      case 'success': return '✓';
      case 'error': return '✗';
      case 'confirm': return '?';
      default: return '';
    }
  }

  confirm() {
    this.dialogService.closeDialog({ confirmed: true });
  }

  cancel() {
    this.dialogService.closeDialog({ confirmed: false });
  }

  close() {
    if (this.dialogConfig?.type === 'confirm') {
      this.cancel(); // For confirm dialogs, clicking overlay should cancel
    } else {
      this.confirm(); // For success/error, clicking overlay should confirm/close
    }
  }
}