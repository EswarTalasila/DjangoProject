import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { AnswerDTO, AssignmentDTO, SubmissionDTO } from './assignment.service';
import { MOCK_ASSIGNMENTS } from './mock-assessment-data';

@Injectable({
  providedIn: 'root',
})
export class MockAssignmentService {
  getStudentAssignments(studentId: number): Observable<AssignmentDTO[]> {
    return of(MOCK_ASSIGNMENTS);
  }

  getAssignmentById(assignmentId: number): Observable<AssignmentDTO> {
    const assignment = MOCK_ASSIGNMENTS.find(a => a.id === assignmentId)!;
    return of(assignment);
  }

  getStudentSubmission(
    studentId: number,
    assignmentId: number
  ): Observable<SubmissionDTO | null> {
    return of(null);
  }

  submitAssignment(
    studentId: number,
    submission: SubmissionDTO
  ): Observable<SubmissionDTO> {
    console.log('Mock submission received:', submission);
    submission.status = 'SUBMITTED';
    submission.id = Math.floor(Math.random() * 10000);
    submission.submittedAt = new Date().toISOString();
    return of(submission);
  }

    saveDraft(
    studentId: number,
    assignmentId: number,
    answers: AnswerDTO[]
  ): Observable<any> {
    console.log(`Mock saveDraft for student ${studentId}, assignment ${assignmentId}`, answers);
    return of({ success: true, savedAt: new Date().toISOString() });
  }
}
