import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import {
  AssignmentService,
  AssignmentDTO,
  SubmissionDTO,
} from '../../../../services/assignment.service';
import { AssessmentService, AssessmentDTO } from '../../../../services/assessment-service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-student-assessment-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './student-assessment-list.component.html',
  styleUrl: './student-assessment-list.component.scss',
})
export class StudentAssessmentListComponent implements OnInit {
  assignments: AssignmentDTO[] = [];
  assessments: AssessmentDTO[] = [];
  error = '';
  studentId!: number;
  submissions: SubmissionDTO[] = [];
  submissionsMap: Map<number, SubmissionDTO> = new Map();

  constructor(
    private assignmentService: AssignmentService,
    private assessmentService: AssessmentService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    const studentIdParam = this.route.snapshot.paramMap.get('studentId');
    this.studentId = studentIdParam ? Number(studentIdParam) : 1;
    this.loadAssignments();
    this.loadSubmissions();
  }

  loadAssignments() {
    this.error = '';

    this.assignmentService.getStudentAssignments(this.studentId).subscribe({
      next: (assignments) => {
        assignments.forEach((assignment) => {
          if (assignment.assessmentId) {
            this.assessmentService
              .getAssessmentById(assignment.assessmentId)
              .subscribe({
                next: (assessment) => {
                  assignment.assessment = assessment;
                },
                error: (err) => {
                  console.error('Error loading assessment details:', err);
                },
              });
          }
        });
        this.assignments = assignments;
      },
      error: (err) => {
        console.error('Error loading assignments:', err);
        this.error = 'Failed to load assignments. Please try again.';
      },
    });
  }

  loadSubmissions() {
    this.assignmentService.getSubmissionByStudentId(this.studentId).subscribe({
      next: (submissions) => {
        this.submissions = submissions;
        submissions.forEach((sub) => {
          if (sub.assignmentId) {
            this.submissionsMap.set(sub.assignmentId, sub);
          }
        });

        console.log('Loaded submissions:', submissions);
        console.log('Submissions map:', this.submissionsMap);
      },
      error: (err) => {
        console.error('Error loading submissions:', err);
      },
    });
  }

  getSubmissionForAssignment(assignmentId: number): SubmissionDTO | undefined {
    return this.submissionsMap.get(assignmentId);
  }

  openAssignment(assignment: AssignmentDTO) {
    console.log(assignment);

    // Check if this is a Mood Meter assignment
    if (assignment.assessment?.gradingMode === 'MOOD_METER') {
      this.router.navigate(['/mood-meter', this.studentId]);
    } else {
      this.router.navigate([`/${this.studentId}/assignments`, assignment.id]);
    }
  }

  getStatusClass(status?: string): string {
    console.log(status);
    switch (status) {
      case 'NOT_STARTED':
        return 'status-not-started';
      case 'IN_PROGRESS':
        return 'status-in-progress';
      case 'SUBMITTED':
        return 'status-submitted';
      case 'GRADED':
        return 'status-graded';
      default:
        return 'NOT_STARTED';
    }
  }

  getStatusText(status?: string): string {
    switch (status) {
      case 'NOT_STARTED':
        return 'Not Started';
      case 'IN_PROGRESS':
        return 'In Progress';
      case 'SUBMITTED':
        return 'Submitted';
      case 'GRADED':
        return 'Graded';
      default:
        return 'Not Started';
    }
  }

  getDaysRemaining(dueAt?: string): number | null {
    if (!dueAt) return null;
    const due = new Date(dueAt);
    const now = new Date();
    const diff = due.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  formatDueDate(dueAt?: string): string {
    if (!dueAt) return 'No due date';
    const due = new Date(dueAt);
    return due.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  isOverdue(dueAt?: string): boolean {
    if (!dueAt) return false;
    return new Date(dueAt) < new Date();
  }

  getAbs(value: number | null | undefined): number {
    return Math.abs(value ?? 0);
  }
}
