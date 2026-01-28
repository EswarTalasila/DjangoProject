import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ShortAnswerQuestionComponent } from './short-answer-question.component';

describe('ShortAnswerQuestionComponent', () => {
  let component: ShortAnswerQuestionComponent;
  let fixture: ComponentFixture<ShortAnswerQuestionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ShortAnswerQuestionComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ShortAnswerQuestionComponent);
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
