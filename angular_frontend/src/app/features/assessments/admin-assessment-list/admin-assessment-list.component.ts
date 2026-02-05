import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import {
  AssessmentDTO,
  AssessmentService,
} from '../../../../services/assessment-service';
import { DialogService } from '../../../../services/dialog.service';

@Component({
  selector: 'app-admin-assessment-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-assessment-list.component.html',
  styleUrl: './admin-assessment-list.component.scss',
})
export class AdminAssessmentListComponent implements OnInit {
  error = '';
  assessments: AssessmentDTO[] = [];
  adminId!: number;

  constructor(
    private assessmentService: AssessmentService,
    private router: Router,
    private dialogService: DialogService
  ) {}

  ngOnInit(): void {
    this.loadAssessments();
  }

  loadAssessments() {
    this.error = '';

    this.assessmentService.getAllAssessments().subscribe({
      next: (assessments) => {
        this.assessments = assessments;
      },
      error: (err) => {
        console.error('Error loading assessments:', err);
        this.dialogService.showRobustDialog(
          'Error',
          'Failed to load assessments. Please try again.',
          'error'
        );
      },
    });
  }

  createAssessment() {
    this.router.navigate(['/assessment-template/create']);
  }

  openAssessment(assessment: AssessmentDTO) {
    if (assessment.id) {
      // Redirect to the assessment template in edit mode
      this.router.navigate(['/assessment-template', assessment.id]);
    } else {
      console.error('No assessment ID provided');
      this.dialogService.showRobustDialog(
        'Error',
        'No assessment ID provided',
        'error'
      );
      // Redirect back to admin's assessment list
      this.router.navigate(['/assessments']);
    }
  }

  deleteAssessment(assessment: AssessmentDTO) {
    if (!assessment.id) {
      console.error('Cannot delete assessment without ID');
      this.dialogService.showRobustDialog(
        'Error',
        'Cannot delete assessment without ID',
        'error'
      );
      return;
    }

    this.dialogService.showRobustDialog(
      'Confirm Deletion',
      `Are you sure you want to delete "${assessment.title}"?`,
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.assessmentService.deleteAssessment(assessment.id!).subscribe({
            next: () => {
              console.log('Assessment deleted successfully');
              this.dialogService.showRobustDialog(
                'Success',
                'Assessment deleted successfully!',
                'success',
                () => {
                  // Reload the assessments list to reflect the deletion
                  this.loadAssessments();
                }
              );
            },
            error: (err) => {
              console.error('Error deleting assessment:', err);
              this.dialogService.showRobustDialog(
                'Error',
                'Failed to delete assessment. Please try again.',
                'error'
              );
            },
          });
        }
      }
    );
  }
}