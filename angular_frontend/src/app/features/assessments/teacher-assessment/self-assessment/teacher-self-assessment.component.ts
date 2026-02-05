import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import {
  AssessmentService,
  AssessmentDTO,
} from '../../../../../services/assessment-service';

@Component({
  selector: 'app-teacher-self-assessment',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './teacher-self-assessment.component.html',
  styleUrl: './teacher-self-assessment.component.scss',
})
export class TeacherSelfAssessmentComponent implements OnInit {
  // Array to store the list of assessments
  assessments: AssessmentDTO[] = [];
  teacherId: string | null = null;

  constructor(
    private assessmentService: AssessmentService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.loadAssessments();
    this.teacherId = this.route.snapshot.paramMap.get('teacherId');
  }

  /**
   * Fetch the list of assessments from the AssessmentService.
   * Filter to show only reflection assessments (gradingMode === 'REFLECTION').
   */
  loadAssessments(): void {
    this.assessmentService.getAllAssessments().subscribe({
      next: (assessments) => {
        this.assessments = assessments.filter(assessment => assessment.gradingMode === 'REFLECTION');
        console.log('Assessments loaded:', this.assessments);
      },
      error: (err) => {
        console.error('Error loading assessments:', err);
      }
    });
  }

  /**
   * This function is triggered when the 'Start' button is clicked for an assessment.
   * It navigates to the teacher's self-submission page for the given assessment.
   * @param assessmentId The ID of the assessment to start.
   */
  startAssessment(assessmentId: number | undefined): void {
    if (assessmentId === undefined) {
      console.error('Assessment ID is undefined');
      return;
    }

    this.router.navigate([`/teacher/${this.teacherId}/self/${assessmentId}`]);
  }
}