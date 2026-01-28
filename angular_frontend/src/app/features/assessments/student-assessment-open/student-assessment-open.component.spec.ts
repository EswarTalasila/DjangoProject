import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { StudentAssessmentOpenComponent } from './student-assessment-open.component';
import { of } from 'rxjs';

describe('StudentAssessmentOpenComponent', () => {
  let component: StudentAssessmentOpenComponent;
  let fixture: ComponentFixture<StudentAssessmentOpenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StudentAssessmentOpenComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => '123' } },
            params: of({ assignmentId: '456' }),
          },
        },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StudentAssessmentOpenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
