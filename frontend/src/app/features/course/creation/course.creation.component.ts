import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DialogService } from '../../../../services/dialog.service';

@Component({
  selector: 'app-course-creation',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './course.creation.component.html',
  styleUrls: ['./course.creation.component.scss'],
})
export class CourseCreationComponent {
  courseName: string = '';

  constructor(
    private router: Router,
    private http: HttpClient,
    private dialogService: DialogService
  ) {}

  onSubmit(event: Event) {
    event.preventDefault();

    // Validate course name
    if (!this.courseName || this.courseName.trim() === '') {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Please enter a course name',
        'error'
      );
      return;
    }

    // Prepare the CourseDto payload (backend expects name only).
    const courseDto = {
      name: this.courseName.trim(),
    };

    console.log('Creating course:', courseDto);

    // Call the backend endpoint
    this.http
      .post('/api/v1/courses/', courseDto, {
        observe: 'response',
      })
      .subscribe({
        next: (response) => {
          if (response.status === 200) {
            this.dialogService.showRobustDialog(
              'Success',
              'Course created successfully!',
              'success',
              () => {
                const createdCourse = response.body;
                console.log('Created course:', createdCourse);
                
                // Navigate to teacher's course list or dashboard
                this.router.navigate(['/courses']);
              }
            );
          } else {
            this.dialogService.showRobustDialog(
              'Unexpected Response',
              'Unexpected response status: ' + response.status,
              'error'
            );
          }
        },
        error: (error) => {
          console.error('Error creating course:', error);
          if (error.status === 403) {
            this.dialogService.showRobustDialog(
              'Permission Denied',
              'You do not have permission to create courses.',
              'error'
            );
          } else {
            this.dialogService.showRobustDialog(
              'Creation Failed',
              'Failed to create course. Please try again.',
              'error'
            );
          }
        },
      });
  }

  onCancel() {
    // Navigate back to dashboard or course list
    this.router.navigate(['/courses']);
  }
}
