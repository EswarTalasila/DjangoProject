import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AssignmentService, SubmissionDTO, AssignmentDTO } from '../../../../../../services/assignment.service';
import { AssessmentService, AssessmentDTO } from '../../../../../../services/assessment-service';
import { forkJoin } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { StudentService } from '../../../../../../services/student.service';

@Component({
  selector: 'app-teacher-gradelist',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './teacher-gradelist.component.html',
  styleUrls: ['./teacher-gradelist.component.scss'],
})
export class TeacherGradelistComponent implements OnInit {
  allSubmissionsList: (SubmissionDTO & { title?: string })[] = [];
  selectedSubmission: SubmissionDTO | null = null;
  teacherId: number | null = null;
  assignmentId: number = -1;
  courseId: number = -1;
  isAuto: boolean | null = null;
  assessment?: AssessmentDTO;
  isMoodMeter: boolean = false;

  constructor(
    private assignmentService: AssignmentService,
    private assessmentService: AssessmentService,
    private router: Router,
    private route: ActivatedRoute,
    private studentService: StudentService,
  ) {}

  ngOnInit(): void {
    const teacherIdParam = this.route.snapshot.paramMap.get('teacherId');
    const assignmentIdParam = this.route.snapshot.paramMap.get('assignmentId');
    const courseIdParam = this.route.snapshot.paramMap.get('courseId');
    this.teacherId = teacherIdParam ? parseInt(teacherIdParam, 10) : null;
    this.assignmentId = assignmentIdParam ? parseInt(assignmentIdParam, 10) : -1;
    this.courseId = courseIdParam ? parseInt(courseIdParam, 10) : -1;

    this.loadAllSubmissions();
  }

  loadAllSubmissions(): void {
    if (!this.teacherId) {
      console.warn('Teacher ID is null, cannot load submissions');
      return;
    }

    if (!this.courseId) {
      console.warn('No course selected, cannot load submissions');
      return;
    }
    
    if(!this.isAuto) {
      this.assignmentService.getAssignmentById(this.assignmentId).pipe(
        switchMap(assignment => {
          return this.assessmentService.getAssessmentById(assignment.assessmentId).pipe(
            map(assessment => {
              if (assessment.gradingMode === 'AUTO') {
                this.isAuto = true;
              }
              else {
                this.isAuto = false;
              }
              return assessment;
            })
          )
        })
      ).subscribe(assessment => {
        console.log(assessment);
      }, error => {
        console.error('Error fetching assignment or assessment:', error);
      });
    }

    // First, load the assignment to get the assessment
    this.assignmentService.getAssignmentById(this.assignmentId).subscribe({
      next: (assignment) => {
        // Load the assessment to check if it's a Mood Meter
        this.assessmentService.getAssessmentById(assignment.assessmentId).subscribe({
          next: (assessment) => {
            this.assessment = assessment;
            this.isMoodMeter = assessment.gradingMode === 'MOOD_METER';
          },
          error: (err) => {
            console.error('Failed to load assessment:', err);
          }
        });
      },
      error: (err) => {
        console.error('Failed to load assignment:', err);
      }
    });

    // Fetch submissions and students in parallel
    forkJoin({
      submissions: this.assignmentService.getSubmissionByAssignment(this.assignmentId),
      students: this.studentService.getStudentsInCourse(this.courseId)
    }).subscribe({
      next: ({ submissions, students }) => {
        // Map student names onto submissions
        this.allSubmissionsList = submissions.map(sub => {
          console.log(sub.studentId);
          console.log(students);
          const student = students.find(s => s.id === sub.studentId);
          const studentName = student ? `${student.name}` : 'Unknown';
          return {
            ...sub,
            studentName
          };
        });
      },
      error: (err) => console.error('Failed to load submissions with student names', err)
    });
  }

  allSubmissions(): (SubmissionDTO & { title?: string })[] {
    return this.allSubmissionsList;
  }

  getStatusText(status: string): string {
    switch (status) {
      case 'NOT_STARTED': return 'Not Started';
      case 'IN_PROGRESS': return 'In Progress';
      case 'SUBMITTED': return 'Submitted';
      case 'GRADED': return 'Graded';
      default: return 'Unknown';
    }
  }

  onOpenGrade(submission: SubmissionDTO): void {
    if (!this.teacherId) {
      console.error('Teacher ID is missing, cannot navigate to grading page');
      return;
    }

    if (!submission || submission.id == null) {
      console.error('Submission ID is missing, cannot navigate');
      return;
    }

    this.router.navigate([
      '/teacher',
      this.teacherId,
      this.route.snapshot.paramMap.get('courseId'),
      this.route.snapshot.paramMap.get('assignmentId'),
      submission.id,
      'grade'
    ]);
  }
}
