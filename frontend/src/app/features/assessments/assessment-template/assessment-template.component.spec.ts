import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';
import { AssessmentTemplateComponent } from './assessment-template.component';
import { of } from 'rxjs';
import { AssessmentService } from '../../../../services/assessment-service';

describe('AssessmentTemplateComponent', () => {
  let component: AssessmentTemplateComponent;
  let fixture: ComponentFixture<AssessmentTemplateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssessmentTemplateComponent],
      providers: [
        {
          provide: AssessmentService,
          useValue: {
            getAllAssessments: () => of([]), // ✅ mock an empty observable
            getAssessmentById: () =>
              of({
                id: 1,
                title: 'Mock Assessment',
                gradingMode: 'MANUAL',
                questions: [],
              }),
            createAssessment: () => of({}),
            updateAssessment: () => of({}),
          },
        },
        {
          provide: ActivatedRoute,
          useValue: { params: of({}) },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AssessmentTemplateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
