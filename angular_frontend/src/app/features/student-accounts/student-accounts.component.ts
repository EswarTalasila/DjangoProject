import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { trigger, transition, style, animate } from '@angular/animations';
import * as ExcelJS from 'exceljs';
import { StudentService, Student } from '../../../services/student.service';
import { DialogService } from '../../../services/dialog.service';

@Component({
  selector: 'app-student-accounts',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './student-accounts.component.html',
  styleUrl: './student-accounts.component.scss',
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
export class StudentAccountsComponent implements OnInit {
  courseId!: number;
  previewData: Student[] = [];
  selectedFileName = 'No file chosen';
  studentConsent: boolean = true; // Default to true (student has consent)
  showInfoDialog: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private studentService: StudentService,
    private dialogService: DialogService
  ) {}

  ngOnInit() {
    const courseIdParam = this.route.snapshot.paramMap.get('courseId');
    this.courseId = courseIdParam ? Number(courseIdParam) : 1;
    
    // Show info dialog on page load with a slight delay for fade-in effect
    setTimeout(() => {
      this.showInfoDialog = true;
    }, 300);
  }

  closeInfoDialog() {
    this.showInfoDialog = false;
  }

  onSubmit(event: Event) {
    event.preventDefault();

    const firstName = (
      document.getElementById('fname') as HTMLInputElement
    ).value.trim();
    const lastName = (
      document.getElementById('lname') as HTMLInputElement
    ).value.trim();
    const username = (
      document.getElementById('email') as HTMLInputElement
    ).value.trim();

    if (!firstName || !lastName || !username) {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Please fill in all fields',
        'error'
      );
      return;
    }

    const newStudent: Student = {
      firstName,
      lastName,
      username,
      consent: this.studentConsent,
      courseId: this.courseId,
      name: firstName + " " + lastName
    };

    console.log(newStudent);

    this.studentService.addStudent(newStudent).subscribe({
      next: (res) => {
        console.log('Student added successfully:', res);
        this.dialogService.showRobustDialog(
          'Success',
          'Student added successfully',
          'success',
          () => {
            // Redirect to view students page for this course
            this.router.navigate(['/course', this.courseId, 'students']);
            (document.getElementById('fname') as HTMLInputElement).value = '';
            (document.getElementById('lname') as HTMLInputElement).value = '';
            (document.getElementById('email') as HTMLInputElement).value = '';
            this.studentConsent = true; // Reset to default after submission
          }
        );
      },
      error: (err) => {
        console.error('Error adding student:', err);
        this.dialogService.showRobustDialog(
          'Error',
          'Failed to add student. Please try again.',
          'error'
        );
      }
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
            'Error',
            'Spreadsheet is empty or headers are incorrect',
            'error'
          );
          return;
        }

        const headers = buildHeaderMap(sheet);
        if (headers.size === 0) {
          this.dialogService.showRobustDialog(
            'Error',
            'Spreadsheet is empty or headers are incorrect',
            'error'
          );
          return;
        }

        const rows = collectRows(sheet, headers);
        if (rows.length === 0) {
          this.dialogService.showRobustDialog(
            'Error',
            'Spreadsheet is empty or headers are incorrect',
            'error'
          );
          return;
        }

        this.previewData = rows.map((row) => ({
          firstName: row['First Name'] || '',
          lastName: row['Last Name'] || '',
          username: row['Email'] || '',
          consent: parseConsent(row['Consent']),
          courseId: this.courseId,
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
      this.dialogService.showRobustDialog(
        'Error',
        'No data uploaded',
        'error'
      );
      return;
    }

    this.previewData.forEach((student) => {
      student.name = student.firstName + " " + student.lastName;
    });

    this.studentService.uploadStudents(this.previewData).subscribe({
      next: () => {
        this.dialogService.showRobustDialog(
          'Success',
          'Students uploaded successfully.',
          'success',
          () => {
            // Redirect to view students page for this course
            this.router.navigate(['/course', this.courseId, 'students']);
          }
        );
      },
      error: (err) => {
        console.error('Error uploading students:', err);
        this.dialogService.showRobustDialog(
          'Error',
          'Failed to upload students. Please try again.',
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

function parseConsent(value: string): boolean {
  if (!value) {
    return true;
  }
  const normalized = value.toLowerCase();
  return normalized === 'true' || normalized === 'yes' || normalized === '1';
}
