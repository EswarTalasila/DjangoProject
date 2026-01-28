import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TeacherGradelistComponent } from './teacher-gradelist.component';
import { ActivatedRoute } from '@angular/router';

describe('TeacherGradelistComponent', () => {
  let component: TeacherGradelistComponent;
  let fixture: ComponentFixture<TeacherGradelistComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TeacherGradelistComponent],
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

    fixture = TestBed.createComponent(TeacherGradelistComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
