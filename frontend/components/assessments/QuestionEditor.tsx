'use client';

import { type QuestionInput, type QuestionGroupInput } from '@/lib/assessment-api';
import { type Rubric } from '@/lib/rubric-api';
import { HelpTip } from '@/components/ui/help-tip';
import QuestionBlock from './QuestionBlock';

type BuilderGradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';

export type QuestionEditorProps = {
  selectedQuestionIndex: number;
  selectedQuestion: QuestionInput | undefined;
  questions: QuestionInput[];
  gradingMode: BuilderGradingMode;
  questionGroups: QuestionGroupInput[];
  selectedEffectiveRubricName: string | null;
  selectedGroupName: string | null;
  rubricSource: 'Question' | 'Group' | 'N/A';
  onQuestionChange: (index: number, updated: QuestionInput) => void;
  onQuestionRemove: (index: number) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
};

export default function QuestionEditor({
  selectedQuestionIndex,
  selectedQuestion,
  questions,
  gradingMode,
  questionGroups,
  selectedEffectiveRubricName,
  selectedGroupName,
  rubricSource,
  onQuestionChange,
  onQuestionRemove,
  onMoveUp,
  onMoveDown,
}: QuestionEditorProps) {
  if (!selectedQuestion) {
    return (
      <section className="space-y-4 min-w-0">
        <div className="rounded-sm border border-border bg-card p-6 text-sm text-muted-foreground">
          Select a question to edit.
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4 min-w-0">
      <div className="space-y-3">
        <div className="rounded-sm border border-border bg-muted/30 p-3">
          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
            <div>
              <dt className="text-muted-foreground">Rubric</dt>
              <dd className="font-medium text-foreground">
                {selectedEffectiveRubricName ?? 'None'}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Group</dt>
              <dd className="font-medium text-foreground">
                {selectedGroupName ?? 'None'}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground flex items-center gap-1.5">
                Rubric Source
                <HelpTip
                  text={
                    'Question: this question has its own rubric.\nGroup: this question uses the rubric from its assigned group.\nN/A: no rubric is attached.'
                  }
                />
              </dt>
              <dd className="font-medium text-foreground">{rubricSource}</dd>
            </div>
          </dl>
        </div>
        <QuestionBlock
          index={selectedQuestionIndex}
          question={selectedQuestion}
          gradingMode={gradingMode}
          groupOptions={questionGroups}
          onChange={(updated) => onQuestionChange(selectedQuestionIndex, updated)}
          onRemove={() => onQuestionRemove(selectedQuestionIndex)}
          onMoveUp={selectedQuestionIndex === 0 ? null : () => onMoveUp(selectedQuestionIndex)}
          onMoveDown={
            selectedQuestionIndex === questions.length - 1
              ? null
              : () => onMoveDown(selectedQuestionIndex)
          }
        />
      </div>
    </section>
  );
}
