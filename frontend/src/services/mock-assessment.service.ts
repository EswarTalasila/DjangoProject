import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { AssessmentDTO } from './assessment-service';
import { MOCK_ASSESSMENTS } from './mock-assessment-data';

@Injectable({
  providedIn: 'root',
})
export class MockAssessmentService {
  getAllAssessments(): Observable<AssessmentDTO[]> {
    return of(MOCK_ASSESSMENTS);
  }

  getAssessmentById(id: number): Observable<AssessmentDTO> {
    const found = MOCK_ASSESSMENTS.find(a => a.id === id)!;
    return of(found);
  }
}
