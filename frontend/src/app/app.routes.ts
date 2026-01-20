import { Routes } from '@angular/router';
import { LoginComponent } from './features/login/login.component';
import { AccountComponent } from './features/account/account.component';
import { AccountCreationComponent } from './features/account/creation/account.creation.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { AccountEditComponent } from './features/account/edit/account.edit.component';
import { StudentAccountsComponent } from './features/student-accounts/student-accounts.component';
import { FirstLoginComponent } from './features/first-login/first-login.component';
import { MoodMeterComponent } from './features/assessments/mood-meter/mood-meter.component';
import { AssessmentTemplateComponent } from './features/assessments/assessment-template/assessment-template.component';
import { StudentAssessmentListComponent } from './features/assessments/student-assessment-list/student-assessment-list.component';
import { StudentAssessmentOpenComponent } from './features/assessments/student-assessment-open/student-assessment-open.component';
import { TeacherAssessmentListComponent } from './features/assessments/teacher-assessment/assessment-list/teacher-assessment-list.component';
import { TeacherSelfAssessmentComponent } from './features/assessments/teacher-assessment/self-assessment/teacher-self-assessment.component';
import { TeacherSelfSubmissionComponent } from './features/assessments/teacher-assessment/self-assessment/self-submission/teacher-self-submission.component';
import { AdminAssessmentListComponent } from './features/assessments/admin-assessment-list/admin-assessment-list.component';
import { TeacherGradelistComponent } from './features/assessments/teacher-assessment/gradebook/gradelist/teacher-gradelist.component';
import { TeacherGradeComponent } from './features/assessments/teacher-assessment/gradebook/grade/teacher-grade.component';
import { CourseCreationComponent } from './features/course/creation/course.creation.component';
import { TeacherAssignmentCreateComponent } from './features/assignments/teacher-assignment/teacher-assignment-create.component';
import { CourseViewComponent } from './features/course/view/course.view.component';
import { NotFoundComponent } from './features/not-found/not-found.component';
import { RoleGuard } from './guards/role.guard';
import { CourseStudentsComponent } from './features/course/students/course-students.component';

export const routes: Routes = [
    { path: '', redirectTo: '/login', pathMatch: 'full' },
    { path: 'login', component: LoginComponent },
    { path: 'dashboard', component: DashboardComponent, canActivate: [RoleGuard], data: { roles: ['ADMIN', 'TEACHER'] }},
    { path: 'account', component: AccountComponent, canActivate: [RoleGuard], data: { roles: ['ADMIN'] }},
    { path: 'account/create', component: AccountCreationComponent, canActivate: [RoleGuard], data: { roles: ['ADMIN'] }},
    { path: 'account/edit/:username', component: AccountEditComponent, canActivate: [RoleGuard], data: { roles: ['ADMIN'] }},
    { path: 'students/add/:courseId', component: StudentAccountsComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'first-login/:userId', component: FirstLoginComponent},
    { path: 'mood-meter/:studentId', component: MoodMeterComponent, canActivate: [RoleGuard], data: { roles: ['STUDENT'] }},
    { path: 'assessments', component: AdminAssessmentListComponent, canActivate: [RoleGuard], data: { roles: ['ADMIN'] }},
    { path: 'assessment-template/create', component: AssessmentTemplateComponent, canActivate: [RoleGuard], data: { roles: ['ADMIN'] }},
    { path: 'assessment-template/:assessmentId', component: AssessmentTemplateComponent, canActivate: [RoleGuard], data: { roles: ['ADMIN'] }},
    { path: 'teacher/:teacherId/assignments/create', component: TeacherAssignmentCreateComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'teacher/:teacherId/assessments', component: TeacherAssessmentListComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'teacher/:teacherId/self', component: TeacherSelfAssessmentComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'teacher/:teacherId/self/:assessmentId', component: TeacherSelfSubmissionComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'teacher/:teacherId/self/:assessmentId/submission/:submissionId', component: TeacherSelfSubmissionComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: ':studentId/assignments', component: StudentAssessmentListComponent, canActivate: [RoleGuard], data: { roles: ['STUDENT'] }},
    { path: ':studentId/assignments/:assignmentId', component: StudentAssessmentOpenComponent, canActivate: [RoleGuard], data: { roles: ['STUDENT'] }},
    { path: 'teacher/:teacherId/:courseId/:assignmentId/gradelist', component: TeacherGradelistComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'course/create', component: CourseCreationComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'course/:courseId/students', component: CourseStudentsComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'teacher/:teacherId/:courseId/:assignmentId/:submissionId/grade', component: TeacherGradeComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: 'courses', component: CourseViewComponent, canActivate: [RoleGuard], data: { roles: ['TEACHER'] }},
    { path: '**', component: NotFoundComponent },
];
