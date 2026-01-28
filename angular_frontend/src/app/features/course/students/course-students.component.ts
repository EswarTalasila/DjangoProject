import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CourseService, StudentDTO } from '../../../../services/course.service';
import { UserService, User } from '../../../../services/user.service';
import { Student } from '../../../../services/student.service';
import { DialogService } from '../../../../services/dialog.service';

@Component({
  selector: 'app-course-students',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './course-students.component.html',
  styleUrls: ['./course-students.component.scss'],
})
export class CourseStudentsComponent implements OnInit {
  courseId: string = '';
  courseName: string = '';
  students: StudentDTO[] = [];
  isLoading: boolean = true;
  
  // For editing
  editingStudent: StudentDTO | null = null;
  editForm = {
    name: '',
    username: ''
  };

  constructor(
    private courseService: CourseService,
    private userService: UserService,
    private router: Router,
    private route: ActivatedRoute, 
    private http: HttpClient,
    private dialogService: DialogService
  ) {}

  ngOnInit(): void {
    this.courseId = this.route.snapshot.paramMap.get('courseId') || '';
    this.courseName = this.route.snapshot.queryParamMap.get('courseName') || '';
    
    if (this.courseId) {
      this.loadStudents();
    }
  }

  loadStudents(): void {
    this.isLoading = true;
    this.courseService.getStudentsInCourse(this.courseId).subscribe({
      next: (students) => {
        this.students = students;
        console.log('Students loaded:', students);
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading students:', err);
        this.dialogService.showRobustDialog(
          'Error',
          'Failed to load students',
          'error'
        );
        this.isLoading = false;
      }
    });
  }

  startEdit(student: StudentDTO): void {
    this.editingStudent = student;
    this.editForm.name = student.name;
    this.editForm.username = student.username;
  }

  cancelEdit(): void {
    this.editingStudent = null;
    this.editForm = { name: '', username: '' };
  }

  saveEdit(): void {
    if (!this.editingStudent) return;

    if (!this.editForm.name.trim() || !this.editForm.username.trim()) {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Name and email cannot be empty',
        'error'
      );
      return;
    }

    const editRequest: User = {
      firstName: '',
      lastName: '',
      name: this.editForm.name.trim(),
      username: this.editingStudent.username,
      role: 'ROLE_STUDENT'
    };

    this.userService.editUser(editRequest, this.editingStudent.id).subscribe({
      next: (message) => {
        console.log('Student updated:', message);
        this.dialogService.showRobustDialog(
          'Success',
          'Student updated successfully!',
          'success',
          () => {
            this.editingStudent = null;
            this.loadStudents(); // Refresh the list
          }
        );
      },
      error: (err) => {
        console.error('Error updating student:', err);
        this.dialogService.showRobustDialog(
          'Error',
          'Failed to update student. Please try again.',
          'error'
        );
      }
    });
  }

  deleteStudent(student: StudentDTO, event: Event): void {
    event.stopPropagation();

    this.dialogService.showRobustDialog(
      'Confirm Removal',
      `Are you sure you want to remove ${student.name} from this course? This will also delete the student's account.`,
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.courseService.removeStudent(this.courseId, student.id).subscribe({
            next: (message) => {
              console.log('Student removed:', message);
              this.dialogService.showRobustDialog(
                'Success',
                'Student removed successfully!',
                'success',
                () => {
                  this.loadStudents(); // Refresh the list
                }
              );
            },
            error: (err) => {
              console.error('Error removing student:', err);
              this.dialogService.showRobustDialog(
                'Error',
                'Failed to remove student. Please try again.',
                'error'
              );
            }
          });
        }
      }
    );
  }

  goBack(): void {
    this.router.navigate(['/courses']);
  }

  addStudents(): void {
    this.router.navigate(['/students/add', this.courseId]);
  }

  resetPassword(student: StudentDTO): void {
    this.dialogService.showRobustDialog(
      'Confirm Reset',
      `Are you sure you want to reset the password for ${student.username}?`,
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.http.put(`/api/v1/auth/reset/${student.id}`, {}, { responseType: 'text'}).subscribe({
            next: (response) => {
              console.log('Password reset response:', response);
              this.dialogService.showRobustDialog(
                'Success',
                'Password reset successfully!',
                'success'
              );
            },
            error: (err) => {
              console.error(`Failed to reset password.`, err);
              this.dialogService.showRobustDialog(
                'Error',
                'Failed to reset password',
                'error'
              );
            }
          });
        }
      }
    );
  }
}