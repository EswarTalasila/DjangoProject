import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TeacherAssessmentListComponent } from './teacher-assessment-list.component';
import { ActivatedRoute } from '@angular/router';

describe('TeacherAssessmentListComponent', () => {
  let component: TeacherAssessmentListComponent;
  let fixture: ComponentFixture<TeacherAssessmentListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TeacherAssessmentListComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => '123' } },
          },
        },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TeacherAssessmentListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
