import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { forkJoin } from 'rxjs';

import { CourseService, CourseSummaryDTO } from '../../../../services/course.service';
import { AssessmentService, AssessmentDTO } from '../../../../services/assessment-service';

@Component({
  selector: 'app-teacher-assignment-create',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './teacher-assignment-create.component.html',
  styleUrl: './teacher-assignment-create.component.scss',
})
export class TeacherAssignmentCreateComponent implements OnInit {
    private http = inject(HttpClient);

    teacherId: string | null = null;

    courses: CourseSummaryDTO[] = [];
    assessments: AssessmentDTO[] = [];

    selectedCourseIds: Set<string> = new Set();
    selectedAssessmentIds: Set<number> = new Set();
    openAt: string | null = null;
    dueAt: string | null = null;

    creating = false;
    feedback: { message: string; type: 'success' | 'error' } | null = null;

    constructor(
        private route: ActivatedRoute,
        private courseService: CourseService,
        private assessmentService: AssessmentService
    ) {}

    ngOnInit(): void {
        this.teacherId = this.route.snapshot.paramMap.get('teacherId');
        this.loadCourses();
        this.loadAssessments();
    }

    loadCourses(): void {
        this.courseService.getCourses().subscribe({
        next: (response) => {
            if (response.status === 200) {
            console.log('200 OK:', response.body);
            this.courses = response.body ?? [];
            } else {
            console.warn('Unexpected status code:', response.status);
            }
        },
        error: (err) => console.error('Failed to load courses', err)
        });
    }

    loadAssessments(): void {
        this.assessmentService.getAllAssessments().subscribe({
            next: (xs) => {
            this.assessments = xs.filter(assessment => assessment.gradingMode !== 'RUBRIC' && assessment.gradingMode !== 'REFLECTION') ?? [];
            },
            error: (err) => console.error('Failed to get assessments', err),
        });
    }

    toggleCourse(courseId: string): void {
        if (this.selectedCourseIds.has(courseId)) {
            this.selectedCourseIds.delete(courseId);
        } else {
            this.selectedCourseIds.add(courseId);
        }
    }

    toggleAssessment(assessmentId: number | undefined): void {
        if (!assessmentId) return;
        if (this.selectedAssessmentIds.has(assessmentId)) {
            this.selectedAssessmentIds.delete(assessmentId);
        } else {
            this.selectedAssessmentIds.add(assessmentId);
        }
    }

    isCourseSelected(courseId: string): boolean {
        return this.selectedCourseIds.has(courseId);
    }

    isAssessmentSelected(assessmentId: number | undefined): boolean {
        return assessmentId ? this.selectedAssessmentIds.has(assessmentId) : false;
    }

    canCreate(): boolean {
        return this.selectedCourseIds.size > 0 && 
               this.selectedAssessmentIds.size > 0 && 
               !this.creating;
    }

    createAssignments(): void {
        if (!this.canCreate()) return;

        this.creating = true;
        this.feedback = null;

        const openAtIso = this.toIsoOrNull(this.openAt) ?? new Date().toISOString();
        const dueAtIso = this.toIsoOrNull(this.dueAt);

        const requests = [];

        for (const courseId of this.selectedCourseIds) {
            for (const assessmentId of this.selectedAssessmentIds) {
                const payload = {
                    assessmentId,
                    audienceType: 'COURSE' as const,
                    courseId: this.toNumericId(courseId),
                    openAt: openAtIso,
                    ...(dueAtIso ? { dueAt: dueAtIso } : {} )
                };

                requests.push(
                    this.http.post('/api/v1/assignments', payload, { withCredentials: true })
                );
            }
        }

        forkJoin(requests).subscribe({
            next: (results: any[]) => {
                const totalCreated = results.length;
                console.log(`Successfully created ${totalCreated} assignments`);
                this.feedback = {
                    message: `Successfully created ${totalCreated} assignment${totalCreated !== 1 ? 's' : ''}`,
                    type: 'success'
                };
                this.selectedCourseIds.clear();
                this.selectedAssessmentIds.clear();
                this.openAt = null;
                this.dueAt = null;
            },
            error: (err: any) => {
                console.error('Failed to create assignments', err);
                this.feedback = {
                    message: 'Failed to create some or all assignments',
                    type: 'error'
                };
            },
            complete: () => (this.creating = false),
        });
    }

    private toIsoOrNull(local: string | null): string | null {
        if (!local) return null;
        const dt = new Date(local);
        return isNaN(dt.getTime()) ? null : dt.toISOString();
    }

    private toNumericId(id: string | null): number | undefined {
        if (!id) return undefined;
        const n = Number(id);
        return Number.isNaN(n) ? undefined : n;
    }

    private unwrapError(e: any): string {
        return e?.error ?? e?.message ?? 'Request failed';
    }
}