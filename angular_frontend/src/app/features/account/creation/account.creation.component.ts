import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { trigger, transition, style, animate } from '@angular/animations';
import * as ExcelJS from 'exceljs';
import { UserService, User } from '../../../../services/user.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DialogService } from '../../../../services/dialog.service';

@Component({
  selector: 'app-account-creation',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './account.creation.component.html',
  styleUrls: ['./account.creation.component.scss'],
  animations: [
    trigger('fadeIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'scale(0.95)' }),
        animate('300ms ease-out', style({ opacity: 1, transform: 'scale(1)' }))
      ]),
      transition(':leave', [
        animate('200ms ease-in', style({ opacity: 0, transform: 'scale(0.95)' }))
      ])
    ])
  ]
})
export class AccountCreationComponent {
  // Removed useManualPassword since it's no longer needed

  //used for bulk upload
  previewData: User[] = [];
  selectedFileName = 'No file chosen';
  showInfoDialog: boolean = false;

  constructor(
    private router: Router,
    private http: HttpClient,
    private userService: UserService,
    private dialogService: DialogService
  ) {}


  ngOnInit() {
    setTimeout(() => {
      this.showInfoDialog = true;
    }, 300);
  }

  closeInfoDialog() {
    this.showInfoDialog = false;
  }

  // Removed onRadioChange since radio buttons are removed

  onSubmit(event: Event) {
    event.preventDefault();

    const form = event.target as HTMLFormElement;

    // Get values
    const roleValue = (
      form.querySelector('select[name="role"]') as HTMLSelectElement
    ).value;
    const firstName = (
      form.querySelector('input[name="fname"]') as HTMLInputElement
    ).value.trim();
    const lastName = (
      form.querySelector('input[name="lname"]') as HTMLInputElement
    ).value.trim();
    const email = (
      form.querySelector('input[name="email"]') as HTMLInputElement
    ).value.trim();
    
    // For both Admin and Teacher, always set password to null
    const password = null;

    // Create User Request
    let requestBody: User = {
      firstName: firstName,
      lastName: lastName,
      name: firstName + " " + lastName,
      username: email,
      password: password
    };

    if (roleValue.toLowerCase() === 'admin') {
      requestBody.role = 'ROLE_ADMIN';
    } else if (roleValue.toLowerCase() === 'teacher') {
      requestBody.role = 'ROLE_TEACHER';
    } else {
      // Use the new robust dialog method
      this.dialogService.showRobustDialog('Invalid Role', 'Invalid role selected', 'error');
      return;
    }

    console.log(requestBody);

    // Call the backend endpoint
    this.http
      .post('/api/v1/auth/createuser', requestBody, {
        observe: 'response',
        responseType: 'text',
      })
      .subscribe({
        next: (response) => {
          if (response.status === 200) {
            // Use the new robust dialog method
            this.dialogService.showRobustDialog(
              'Success', 
              response.body as string, 
              'success', 
              () => {
                form.reset();
                this.router.navigate(['/account']);
              }
            );
          } else {
            // Use the new robust dialog method
            this.dialogService.showRobustDialog(
              'Unexpected Response', 
              'Unexpected response status: ' + response.status, 
              'error'
            );
          }
        },
        error: (error) => {
          console.error('Error creating user:', error);
          // Use the new robust dialog method
          this.dialogService.showRobustDialog(
            'Creation Failed', 
            'Failed to create user. Please try again.', 
            'error'
          );
        },
      });
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (!file) {
      this.selectedFileName = 'No file chosen';
      return;
    }

    this.selectedFileName = file.name;

    const reader = new FileReader();
    reader.onload = async (e: any) => {
      try {
        const data = e.target.result as ArrayBuffer;
        const workbook = new ExcelJS.Workbook();
        await workbook.xlsx.load(data);
        const sheet = workbook.worksheets[0];
        if (!sheet) {
          this.dialogService.showRobustDialog(
            'Empty Spreadsheet',
            'Spreadsheet is empty or headers are incorrect',
            'error'
          );
          return;
        }

        const headers = buildHeaderMap(sheet);
        if (headers.size === 0) {
          this.dialogService.showRobustDialog(
            'Empty Spreadsheet',
            'Spreadsheet is empty or headers are incorrect',
            'error'
          );
          return;
        }

        const rows = collectRows(sheet, headers);
        if (rows.length === 0) {
          this.dialogService.showRobustDialog(
            'Empty Spreadsheet',
            'Spreadsheet is empty or headers are incorrect',
            'error'
          );
          return;
        }

        this.previewData = rows.map((row) => ({
          firstName: row['First Name'] || '',
          lastName: row['Last Name'] || '',
          username: row['Email'] || '',
          role: parseRole(row['Role']),
        }));
      } catch (error) {
        console.error('Failed to parse spreadsheet', error);
        this.dialogService.showRobustDialog(
          'Parse Error',
          'Failed to read the spreadsheet. Please verify the file format.',
          'error'
        );
      }
    };
    reader.readAsArrayBuffer(file);
  }

  onSubmitBulk() {
    if (this.previewData.length === 0) {
      // Use the new robust dialog method
      this.dialogService.showRobustDialog('No Data', 'No data uploaded', 'error');
      return;
    }

    this.previewData.forEach((user) => {
      user.name = user.firstName + " " + user.lastName;
    });

    console.log(this.previewData);

    this.userService.uploadUsers(this.previewData).subscribe({
      next: () => {
        // Use the new robust dialog method
        this.dialogService.showRobustDialog(
          'Upload Successful', 
          'Users uploaded successfully.', 
          'success', 
          () => {
            this.previewData = [];
            this.selectedFileName = 'No file chosen';
            const fileInput = document.getElementById(
              'fileInput'
            ) as HTMLInputElement;
            if (fileInput) {
              fileInput.value = '';
            }
          }
        );
      },
      error: (error) => {
        // Use the new robust dialog method
        this.dialogService.showRobustDialog(
          'Upload Failed', 
          'Failed to upload users. Please try again.', 
          'error'
        );
      }
    });
  }
}

function buildHeaderMap(sheet: ExcelJS.Worksheet): Map<string, number> {
  const headerRow = sheet.getRow(1);
  const headers = new Map<string, number>();
  headerRow.eachCell((cell, colNumber) => {
    const value = normalizeCellValue(cell.value);
    if (value) {
      headers.set(value, colNumber);
    }
  });
  return headers;
}

function collectRows(
  sheet: ExcelJS.Worksheet,
  headers: Map<string, number>
): Record<string, string>[] {
  const rows: Record<string, string>[] = [];
  sheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) {
      return;
    }
    const record: Record<string, string> = {};
    headers.forEach((col, header) => {
      record[header] = normalizeCellValue(row.getCell(col).value);
    });
    if (Object.values(record).some((value) => value)) {
      rows.push(record);
    }
  });
  return rows;
}

function normalizeCellValue(value: ExcelJS.CellValue | null | undefined): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'object') {
    if ('text' in value && typeof value.text === 'string') {
      return value.text.trim();
    }
    return String(value).trim();
  }
  return String(value).trim();
}

function parseRole(value: string): User['role'] | undefined {
  if (!value) {
    return undefined;
  }
  const normalized = value.trim().toUpperCase();
  if (normalized.startsWith('ROLE_')) {
    return normalized as User['role'];
  }
  if (normalized === 'ADMIN') {
    return 'ROLE_ADMIN';
  }
  if (normalized === 'TEACHER') {
    return 'ROLE_TEACHER';
  }
  if (normalized === 'STUDENT') {
    return 'ROLE_STUDENT';
  }
  return undefined;
}
