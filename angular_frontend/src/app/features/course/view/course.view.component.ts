import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { CourseService, CourseSummaryDTO } from '../../../../services/course.service';
import { HttpClient } from '@angular/common/http';
import { DialogService } from '../../../../services/dialog.service';

@Component({
  selector: 'app-course-view',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './course.view.component.html',
  styleUrls: ['./course.view.component.scss'],
})
export class CourseViewComponent implements OnInit {
  courses: CourseSummaryDTO[] = [];
  isLoading: boolean = true;

  constructor(
    private courseService: CourseService,
    private router: Router,
    private http: HttpClient,
    private dialogService: DialogService
  ) {}

  ngOnInit(): void {
    this.loadCourses();
  }

  loadCourses(): void {
    this.isLoading = true;
    this.courseService.getCourses().subscribe({
      next: (response) => {
        if (response.status === 200) {
          console.log('200 OK:', response.body);
          this.courses = response.body ?? [];
          this.isLoading = false;
        } else {
          console.warn('Unexpected status code:', response.status);
          this.isLoading = false;
        }
      },
      error: (err) => {
        console.error('Failed to load courses', err);
        this.isLoading = false;
      }
    });
  }

  navigateToCreateCourse(): void {
    this.router.navigate(['/course/create']);
  }

  addStudents(courseId: string): void {
    // Navigate to add students page for this course
    this.router.navigate(['/students/add', courseId]);
  }

  viewStudents(course: CourseSummaryDTO): void {
    // Navigate to view students page with course info
    this.router.navigate(['/course', course.id, 'students'], {
      queryParams: { courseName: course.name }
    });
  }

  viewCourseDetails(courseId: string): void {
    // Optional: Navigate to a detailed course view
    this.router.navigate(['/course', courseId]);
  }

  deleteCourse(course: CourseSummaryDTO): void {
    this.dialogService.showRobustDialog(
      'Confirm Deletion',
      `Are you sure you want to delete the course "${course.name}"? This action cannot be undone and all associated data will be lost.`,
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.http.delete(`/api/v1/courses/${course.id}`, {
            observe: 'response'
          }).subscribe({
            next: (response) => {
              if (response.status === 204) {
                this.dialogService.showRobustDialog(
                  'Success',
                  'Course deleted successfully!',
                  'success',
                  () => {
                    // Remove the deleted course from the local array
                    this.courses = this.courses.filter(c => c.id !== course.id);
                  }
                );
              }
            },
            error: (error) => {
              console.error('Error deleting course:', error);
              if (error.status === 403) {
                this.dialogService.showRobustDialog(
                  'Permission Denied',
                  'You do not have permission to delete this course.',
                  'error'
                );
              } else if (error.status === 404) {
                this.dialogService.showRobustDialog(
                  'Course Not Found',
                  'Course not found. It may have already been deleted.',
                  'error'
                );
              } else {
                this.dialogService.showRobustDialog(
                  'Deletion Failed',
                  'Failed to delete course. Please try again.',
                  'error'
                );
              }
            }
          });
        }
      }
    );
  }
}