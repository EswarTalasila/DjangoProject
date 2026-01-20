import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TeacherSelfSubmissionComponent } from './teacher-self-submission.component';
import { of } from 'rxjs';

describe('TeacherSelfSubmissionComponent', () => {
  let component: TeacherSelfSubmissionComponent;
  let fixture: ComponentFixture<TeacherSelfSubmissionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TeacherSelfSubmissionComponent],
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

    fixture = TestBed.createComponent(TeacherSelfSubmissionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
