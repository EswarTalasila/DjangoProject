import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import {
  AssignmentService,
  AssignmentDTO,
  SubmissionDTO,
} from '../../../../services/assignment.service';
import { AssessmentService } from '../../../../services/assessment-service';
import { DialogService } from '../../../../services/dialog.service';

interface MoodWord {
  name: string;
  row: number;
  col: number;
}

interface SelectedMood {
  name: string;
  row: number;
  col: number;
}

@Component({
  selector: 'app-mood-meter',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './mood-meter.component.html',
  styleUrl: './mood-meter.component.scss',
})
export class MoodMeterComponent implements OnInit {
  selectedMoods: SelectedMood[] = [];
  assignment?: AssignmentDTO;
  submitError = '';
  submitting = false;
  studentId!: number;
  moodMeterAssignment?: AssignmentDTO;
  questionId?: number;

  constructor(
    private assignmentService: AssignmentService,
    private assessmentService: AssessmentService,
    private route: ActivatedRoute,
    private router: Router,
    private dialogService: DialogService,
  ) {}

  ngOnInit() {
    const studentIdParam = this.route.snapshot.paramMap.get('studentId');
    this.studentId = studentIdParam ? Number(studentIdParam) : 0;
    
    if (this.studentId) {
      this.loadMoodMeterAssignment();
    }
  }

  private loadMoodMeterAssignment() {
    // Get all student assignments and find the Mood Meter one
    this.assignmentService.getStudentAssignments(this.studentId).subscribe({
      next: (assignments) => {
        // Find the Mood Meter assignment
        assignments.forEach((assignment) => {
          if (assignment.assessmentId) {
            this.assessmentService.getAssessmentById(assignment.assessmentId).subscribe({
              next: (assessment) => {
                assignment.assessment = assessment;
                if (assessment.gradingMode === 'MOOD_METER') {
                  this.moodMeterAssignment = assignment;
                  // Get the question ID from the assessment
                  if (assessment.questions && assessment.questions.length > 0) {
                    this.questionId = assessment.questions[0].id || assessment.questions[0].questionId;
                  }
                }
              },
              error: (err) => {
                console.error('Error loading assessment:', err);
              }
            });
          }
        });
      },
      error: (err) => {
        console.error('Error loading assignments:', err);
        this.submitError = 'Failed to load mood meter assignment.';
      }
    });
  }

  onSubmit() {
    if (!this.moodMeterAssignment || this.selectedMoods.length === 0 || !this.questionId) {
      this.submitError = 'Please select at least one mood before submitting.';
      return;
    }

    this.submitting = true;
    this.submitError = '';

    // Create multiple MoodMeterAnswers, one for each selected mood
    const moodAnswers = this.selectedMoods.map(selectedMood => 
      AssignmentService.createMoodMeterAnswer(
        this.questionId!,
        selectedMood.row,
        selectedMood.col
      )
    );

    // Create the submission DTO with all selected moods
    // Don't include submittedAt - backend will set it automatically
    const submission: SubmissionDTO = {
      assignmentId: this.moodMeterAssignment.id,
      studentId: this.studentId,
      status: 'SUBMITTED',
      answers: moodAnswers
    };

    console.log('Submitting mood meter with', moodAnswers.length, 'mood(s):', this.selectedMoods);

    // Submit using the standard assignment service
    this.assignmentService.submitAssignment(this.moodMeterAssignment.id, submission).subscribe({
      next: (response) => {
        console.log('Mood meter submitted successfully:', response);
        this.submitting = false;
        const moodText = this.selectedMoods.length === 1 ? 'mood has' : 'moods have';
        this.dialogService.showRobustDialog(
          'Success',
          'Assessment submitted successfully!',
          'success',
          () => {
            this.router.navigate([`/${this.studentId}/assignments`]);
          }
        );
        // Navigate back to assignments list
        this.router.navigate([`/${this.studentId}/assignments`]);
      },
      error: (error) => {
        console.error('Error submitting mood meter:', error);
        this.submitting = false;
        this.submitError = 'Failed to submit mood meter. Please try again.';
      },
    });
  }

  // Rows 0-4 = High Energy, Rows 5-9 = Low Energy
  // Cols 0-4 = Low Pleasantness, Cols 5-9 = High Pleasantness
  moods = {
    highEnergyLowPleasantness: [
      { name: 'Enraged', row: 0, col: 0 },
      { name: 'Panicked', row: 0, col: 1 },
      { name: 'Stressed', row: 0, col: 2 },
      { name: 'Jittery', row: 0, col: 3 },
      { name: 'Shocked', row: 0, col: 4 },
      { name: 'Livid', row: 1, col: 0 },
      { name: 'Furious', row: 1, col: 1 },
      { name: 'Frustrated', row: 1, col: 2 },
      { name: 'Tense', row: 1, col: 3 },
      { name: 'Stunned', row: 1, col: 4 },
      { name: 'Fuming', row: 2, col: 0 },
      { name: 'Frightened', row: 2, col: 1 },
      { name: 'Angry', row: 2, col: 2 },
      { name: 'Nervous', row: 2, col: 3 },
      { name: 'Restless', row: 2, col: 4 },
      { name: 'Anxious', row: 3, col: 0 },
      { name: 'Apprehensive', row: 3, col: 1 },
      { name: 'Worried', row: 3, col: 2 },
      { name: 'Irritated', row: 3, col: 3 },
      { name: 'Annoyed', row: 3, col: 4 },
      { name: 'Repulsed', row: 4, col: 0 },
      { name: 'Troubled', row: 4, col: 1 },
      { name: 'Concerned', row: 4, col: 2 },
      { name: 'Uneasy', row: 4, col: 3 },
      { name: 'Peeved', row: 4, col: 4 },
    ],
    highEnergyHighPleasantness: [
      { name: 'Surprised', row: 0, col: 5 },
      { name: 'Upbeat', row: 0, col: 6 },
      { name: 'Festive', row: 0, col: 7 },
      { name: 'Exhilarated', row: 0, col: 8 },
      { name: 'Ecstatic', row: 0, col: 9 },
      { name: 'Hyper', row: 1, col: 5 },
      { name: 'Cheerful', row: 1, col: 6 },
      { name: 'Motivated', row: 1, col: 7 },
      { name: 'Inspired', row: 1, col: 8 },
      { name: 'Elated', row: 1, col: 9 },
      { name: 'Energized', row: 2, col: 5 },
      { name: 'Lively', row: 2, col: 6 },
      { name: 'Excited', row: 2, col: 7 },
      { name: 'Optimistic', row: 2, col: 8 },
      { name: 'Enthusiastic', row: 2, col: 9 },
      { name: 'Pleased', row: 3, col: 5 },
      { name: 'Focused', row: 3, col: 6 },
      { name: 'Happy', row: 3, col: 7 },
      { name: 'Proud', row: 3, col: 8 },
      { name: 'Thrilled', row: 3, col: 9 },
      { name: 'Pleasant', row: 4, col: 5 },
      { name: 'Joyful', row: 4, col: 6 },
      { name: 'Hopeful', row: 4, col: 7 },
      { name: 'Playful', row: 4, col: 8 },
      { name: 'Blissful', row: 4, col: 9 },
    ],
    lowEnergyLowPleasantness: [
      { name: 'Disgusted', row: 5, col: 0 },
      { name: 'Glum', row: 5, col: 1 },
      { name: 'Disappointed', row: 5, col: 2 },
      { name: 'Down', row: 5, col: 3 },
      { name: 'Apathetic', row: 5, col: 4 },
      { name: 'Pessimistic', row: 6, col: 0 },
      { name: 'Morose', row: 6, col: 1 },
      { name: 'Discouraged', row: 6, col: 2 },
      { name: 'Sad', row: 6, col: 3 },
      { name: 'Bored', row: 6, col: 4 },
      { name: 'Alienated', row: 7, col: 0 },
      { name: 'Miserable', row: 7, col: 1 },
      { name: 'Lonely', row: 7, col: 2 },
      { name: 'Disheartened', row: 7, col: 3 },
      { name: 'Tired', row: 7, col: 4 },
      { name: 'Despondent', row: 8, col: 0 },
      { name: 'Depressed', row: 8, col: 1 },
      { name: 'Sullen', row: 8, col: 2 },
      { name: 'Exhausted', row: 8, col: 3 },
      { name: 'Fatigued', row: 8, col: 4 },
      { name: 'Despairing', row: 9, col: 0 },
      { name: 'Hopeless', row: 9, col: 1 },
      { name: 'Desolate', row: 9, col: 2 },
      { name: 'Spent', row: 9, col: 3 },
      { name: 'Drained', row: 9, col: 4 },
    ],
    lowEnergyHighPleasantness: [
      { name: 'Eddied', row: 5, col: 5 },
      { name: 'Easy-Going', row: 5, col: 6 },
      { name: 'Content', row: 5, col: 7 },
      { name: 'Loving', row: 5, col: 8 },
      { name: 'Fulfilled', row: 5, col: 9 },
      { name: 'Calm', row: 6, col: 5 },
      { name: 'Secure', row: 6, col: 6 },
      { name: 'Satisfied', row: 6, col: 7 },
      { name: 'Grateful', row: 6, col: 8 },
      { name: 'Touched', row: 6, col: 9 },
      { name: 'Relaxed', row: 7, col: 5 },
      { name: 'Chill', row: 7, col: 6 },
      { name: 'Restful', row: 7, col: 7 },
      { name: 'Blessed', row: 7, col: 8 },
      { name: 'Balanced', row: 7, col: 9 },
      { name: 'Mellow', row: 8, col: 5 },
      { name: 'Thoughtful', row: 8, col: 6 },
      { name: 'Peaceful', row: 8, col: 7 },
      { name: 'Comfortable', row: 8, col: 8 },
      { name: 'Carefree', row: 8, col: 9 },
      { name: 'Sleepy', row: 9, col: 5 },
      { name: 'Complacent', row: 9, col: 6 },
      { name: 'Tranquil', row: 9, col: 7 },
      { name: 'Cozy', row: 9, col: 8 },
      { name: 'Serene', row: 9, col: 9 },
    ],
  };

  selectMood(mood: MoodWord) {
    // Check if this mood is already selected
    const index = this.selectedMoods.findIndex((m) => m.name === mood.name);
    if (index > -1) {
      // Deselect the mood
      this.selectedMoods.splice(index, 1);
    } else {
      // Add this mood to the selection (allow multiple moods)
      this.selectedMoods.push({
        name: mood.name,
        row: mood.row,
        col: mood.col
      });
    }
    console.log('Selected Moods:', this.selectedMoods);
  }

  isSelected(name: string): boolean {
    return this.selectedMoods.some((m) => m.name === name);
  }
}