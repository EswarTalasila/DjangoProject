import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import {
  AssignmentService,
  SubmissionDTO,
  AssignmentDTO,
} from '../../../../../services/assignment.service';
import { AssessmentService, AssessmentDTO } from '../../../../../services/assessment-service';
import { CourseService, CourseSummaryDTO } from '../../../../../services/course.service';
import { forkJoin } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { DialogService } from '../../../../../services/dialog.service';

@Component({
  selector: 'app-teacher-assessment-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './teacher-assessment-list.component.html',
  styleUrl: './teacher-assessment-list.component.scss',
})
export class TeacherAssessmentListComponent implements OnInit {
  selfAssignments: (SubmissionDTO & { title?: string })[] = [];
  studentAssessments: any[] = [];
  courses: any[] = [];
  filteredStudents: any[] = [];

  selectedCourse: string | null = null;
  selectedStudent: string | null = null;

  selectedSelfAssignment: (SubmissionDTO & { title?: string }) | null = null;
  selectedStudentAssessment: any = null;

  teacherId: number | null = null;

  constructor(
    private assignmentService: AssignmentService,
    private assessmentService: AssessmentService,
    private courseService: CourseService,
    private router: Router,
    private route: ActivatedRoute,
    private dialogService: DialogService
  ) {}

  ngOnInit(): void {
    const teacherIdParam = this.route.snapshot.paramMap.get('teacherId');
    this.teacherId = teacherIdParam ? parseInt(teacherIdParam, 10) : null;

    this.loadSelfAssignments();
    this.loadCourses();
  }

  loadSelfAssignments(): void {
  if (!this.teacherId) {
    console.warn('Teacher ID is null, cannot load self assignments');
    return;
  }

  this.assignmentService.getTeacherSelfSubmissions(this.teacherId).pipe(
    switchMap((submissions) => {
      if (!submissions.length) {
        return ([]);
      }

      // For each submission, get its assignment and then its assessment
      const assignmentWithAssessment$ = submissions.map((submission) =>
        this.assignmentService.getAssignmentById(submission.assignmentId).pipe(
          switchMap((assignment: AssignmentDTO) =>
            this.assessmentService.getAssessmentById(assignment.assessmentId).pipe(
              map((assessment: AssessmentDTO) => ({
                ...assignment,
                assessment, // attach assessment
              }))
            )
          ),
          map((assignmentWithAssessment) => ({
            ...submission,
            title: assignmentWithAssessment.assessment.title,
            assignment: assignmentWithAssessment
          }))
        )
      );

      return forkJoin(assignmentWithAssessment$);
    })
    ).subscribe({
      next: (submissionsWithTitles) => {
        this.selfAssignments = submissionsWithTitles;
      },
      error: (err) => {
        console.error('Failed to load self assignments', err);
      }
    });
  }

  deleteAssignment(assessment: AssignmentDTO, event: Event) {
    // Stop the row click event from firing
    event.stopPropagation();

    this.dialogService.showRobustDialog(
      'Confirm Deletion',
      `Are you sure you want to delete the assignment "${assessment.assessmentName}"? This action cannot be undone.`,
      'confirm',
      (confirmed) => {
        if (confirmed) {
          // Call the delete service
          this.assignmentService.deleteAssignment(assessment.id).subscribe({
            next: (message) => {
              console.log('Assignment deleted:', message);
              this.dialogService.showRobustDialog(
                'Success',
                'Assignment deleted successfully!',
                'success',
                () => {
                  // Refresh the assignments list for the selected course
                  if (this.selectedCourse) {
                    this.onCourseChange();
                  }
                }
              );
            },
            error: (err) => {
              console.error('Error deleting assignment:', err);
              this.dialogService.showRobustDialog(
                'Error',
                'Failed to delete assignment. Please try again.',
                'error'
              );
            }
          });
        }
      }
    );
  }

  loadCourses(): void {
    this.courseService.getCourses().subscribe({
      next: (response) => {
        if (response.status === 200) {
          console.log('200 OK:', response.body);
          this.courses = response.body ?? [];
          this.selectedCourse = 'all';
          this.onCourseChange();
        } else {
          console.warn('Unexpected status code:', response.status);
        }
      },
      error: (err) => console.error('Failed to load courses', err)
    });
  }

  /**
   * Called whenever the user selects a new course
   */
  onCourseChange(): void {
    if (!this.selectedCourse) return;

    // Check if "All Courses" is selected
    if (this.selectedCourse === 'all') {
      // Fetch assignments for all courses and combine them
      if (this.courses.length === 0) {
        this.studentAssessments = [];
        return;
      }

      const assignmentRequests = this.courses.map(course =>
        this.assignmentService.getAssignmentsByCourse(String(course.id))
      );

      forkJoin(assignmentRequests).subscribe({
        next: (allAssignments) => {
          // Flatten the array of arrays into a single array
          this.studentAssessments = allAssignments.flat();
          console.log('All assignments loaded:', this.studentAssessments);
        },
        error: (err) => console.error('Failed to load assignments for all courses', err)
      });
    } else {
      // Fetch assignments for the selected course only
      this.assignmentService.getAssignmentsByCourse(this.selectedCourse).subscribe({
        next: (assignments) => {
          console.log(assignments);
          this.studentAssessments = assignments;
        },
        error: (err) => console.error('Failed to load assignments for course', err)
      });
    }
  }

  getStatusText(assessment: AssignmentDTO): string {
    console.log(assessment.dueAt);
    if(assessment.dueAt) {
      return this.getDueStatus(assessment.dueAt);
    }
    return 'No Due Date';
  }

  getDueStatus(dueDateStr: string): string {
    const now = new Date();
    const dueDate = new Date(dueDateStr);

    // Remove time component for day-level comparison
    const diffTime = dueDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays > 0) {
      return `due in ${diffDays} day${diffDays > 1 ? 's' : ''}`;
    } else {
      return 'past due';
    }
  }

  editSubmission(assignment: SubmissionDTO & { title?: string; assignment?: any }) {
    if (!this.teacherId) {
      console.warn('Teacher ID is not set, cannot navigate to edit submission');
      return;
    }
  
    if (!assignment.id) {
      this.dialogService.showRobustDialog(
        'Error',
        'Cannot edit: Submission ID is missing',
        'error'
      );
      return;
    }
  
    // Get the assessmentId from the nested assignment object
    const assessmentId = assignment.assignment?.assessmentId;
    
    if (!assessmentId) {
      console.error('Assessment ID is missing from assignment:', assignment);
      this.dialogService.showRobustDialog(
        'Error',
        'Cannot edit: Assessment ID is missing',
        'error'
      );
      return;
    }
  
    // Navigate to the edit route with assessmentId (not assignmentId) and submissionId
    this.router.navigate([
      'teacher',
      this.teacherId,
      'self',
      assessmentId, // This is the assessmentId from the assignment
      'submission',
      assignment.id // This is the submissionId
    ]);
  }

  viewSubmissions(assessment: AssignmentDTO) {
    if (!this.teacherId) {
      console.warn('Teacher ID is not set, cannot navigate to submissions');
      return;
    }

    // If "All Courses" is selected, use the assignment's courseId
    // Otherwise, use the selected course
    const courseId = this.selectedCourse === 'all' ? assessment.courseId : this.selectedCourse;

    if (!courseId) {
      console.warn('No course ID available, cannot navigate to submissions');
      return;
    }

    this.router.navigate([
      'teacher',
      this.teacherId,
      courseId, // pass course ID
      assessment.id, // assignmentId
      'gradelist'
    ]);
  }

}