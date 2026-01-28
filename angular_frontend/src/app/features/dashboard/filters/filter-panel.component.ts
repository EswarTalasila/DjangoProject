import { Component, OnInit, Output, EventEmitter, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VisualizationFilters } from '../../../../services/visualization.service';
import {
  CourseService,
  CourseSummaryDTO,
} from '../../../../services/course.service';
import {
  AssessmentService,
  AssessmentDTO,
} from '../../../../services/assessment-service';
import { StudentService, Student } from '../../../../services/student.service';
import { UserService } from '../../../../services/user.service';

@Component({
  selector: 'app-filter-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './filter-panel.component.html',
  styleUrls: ['./filter-panel.component.scss'],
})
export class FilterPanelComponent implements OnInit {
  @Input() userRole: string = '';
  @Output() filtersChanged = new EventEmitter<VisualizationFilters>();

  selectedCourseId: number | null = null;
  selectedStudentId: number | null = null;
  selectedCategory: string | null = null;
  selectedAssessmentId: number | null = null;
  selectedTeacherId: number | null = null;
  isMoodMeterOnly: boolean = false;

  courses: CourseSummaryDTO[] = [];
  students: Student[] = [];
  assessments: AssessmentDTO[] = [];
  categories: string[] = [];
  teachers: any[] = [];

  loading = false;
  userId: string | null = null;

  constructor(
    private courseService: CourseService,
    private assessmentService: AssessmentService,
    private studentService: StudentService,
    private userService: UserService
  ) {}

  ngOnInit(): void {
    this.userService.getUserId().subscribe((id) => {
      this.userId = id;
      this.loadInitialData();
    });
  }

  private loadInitialData(): void {
    this.loading = true;

    this.courseService.getCourses().subscribe({
      next: (response) => {
        this.courses = response.body || [];
        this.loading = false;
      },
      error: () => (this.loading = false),
    });

    this.assessmentService.getAllAssessments().subscribe({
      next: (assessments) => {
        this.assessments = assessments.filter((a) => a.gradingMode !== 'RUBRIC' && a.gradingMode !== 'REFLECTION');
        this.categories = [
          ...new Set(
            assessments.map((a) => (a as any).category).filter((c) => c)
          ),
        ];
      },
    });

    if (this.userRole === 'ADMIN') {
      this.userService.getTeachersAndAdmins().subscribe({
        next: (teachers) => {
          this.teachers = teachers.filter((teacher) => teacher.role === 'ROLE_TEACHER');
        },
        error: (err) => {
          console.error('Error loading teachers:', err);
          this.teachers = [];
        },
      });
    }
  }

  onCourseChange(): void {
    this.selectedStudentId = null;
    this.students = [];

    if (this.selectedCourseId && this.userRole === 'TEACHER') {
      this.studentService.getStudentsInCourse(this.selectedCourseId).subscribe({
        next: (students) => (this.students = students),
      });
    }

    this.emitFilters();
  }

  onCategoryChange(): void {
    this.emitFilters();
  }

  onAssessmentChange(): void {
    if(this.assessments.find(assessment => assessment.id === this.selectedAssessmentId)?.gradingMode === 'MOOD_METER') {
      this.isMoodMeterOnly = true;
    }
    else {
      this.isMoodMeterOnly = false;
    }
    this.emitFilters();
  }

  onStudentChange(): void {
    this.emitFilters();
  }

  onTeacherChange(): void {
    this.emitFilters();
  }

  onMoodMeterToggle(): void {
    if (this.isMoodMeterOnly) {
      this.selectedAssessmentId = 1;
    }
    else {
      this.selectedAssessmentId = null;
    }
    this.emitFilters();
  }

  resetFilters(): void {
    this.selectedCourseId = null;
    this.selectedStudentId = null;
    this.selectedCategory = null;
    this.selectedAssessmentId = null;
    this.selectedTeacherId = null;
    this.isMoodMeterOnly = false;
    this.students = [];
    this.emitFilters();
  }

  private emitFilters(): void {
    const filters: VisualizationFilters = {
      courseId: this.selectedCourseId,
      studentId: this.selectedStudentId,
      category: this.selectedCategory,
      assessmentId: this.selectedAssessmentId,
      teacherId: this.selectedTeacherId,
      isMoodMeter: this.isMoodMeterOnly,
    };

    this.filtersChanged.emit(filters);
  }

  get isTeacher(): boolean {
    return this.userRole === 'TEACHER';
  }

  get isAdmin(): boolean {
    return this.userRole === 'ADMIN';
  }

  get canSelectStudent(): boolean {
    return this.isTeacher && !!this.selectedCourseId;
  }
}
