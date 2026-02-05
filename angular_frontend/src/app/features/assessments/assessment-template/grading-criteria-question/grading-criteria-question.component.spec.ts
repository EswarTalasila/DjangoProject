import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GradingCriteriaQuestionComponent } from './grading-criteria-question.component';

describe('GradingCriteriaQuestionComponent', () => {
  let component: GradingCriteriaQuestionComponent;
  let fixture: ComponentFixture<GradingCriteriaQuestionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GradingCriteriaQuestionComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(GradingCriteriaQuestionComponent);
    component = fixture.componentInstance;
    component.data = {
      id: '1',
      maxPoints: 10,
      autoGradable: true,
      type: 'short-answer',
      prompt: 'Sample question',
    };
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
