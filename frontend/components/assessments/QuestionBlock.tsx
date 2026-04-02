'use client';

import { ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type {
  QuestionInput,
  QuestionKind,
  QuestionData,
  GradingMode,
  GradingStrategy,
  QuestionGroupInput,
} from '@/lib/assessment-api';
import McqFields from './McqFields';
import ShortAnswerFields from './ShortAnswerFields';
import NumberScaleFields from './NumberScaleFields';

type QuestionBlockProps = {
  index: number;
  question: QuestionInput;
  gradingMode: GradingMode;
  groupOptions: QuestionGroupInput[];
  onChange: (updated: QuestionInput) => void;
  onRemove: () => void;
  onMoveUp: (() => void) | null;
  onMoveDown: (() => void) | null;
};

const TYPE_DEFAULTS: Record<QuestionKind, QuestionData> = {
  MULTIPLE_CHOICE: { choices: [{ prompt: '', score: 0 }], selectAll: false },
  SHORT_ANSWER: { caseSensitive: false, trim: true },
  NUMBER_SCALE: { min: 1, max: 5, target: null },
  MOOD_METER: {},
};

export default function QuestionBlock({
  index,
  question,
  gradingMode,
  groupOptions,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
}: QuestionBlockProps) {
  function handleTypeChange(type: QuestionKind) {
    onChange({ ...question, type, data: { ...TYPE_DEFAULTS[type] } });
  }

  function handleDataChange(data: QuestionData) {
    onChange({ ...question, data });
  }

  return (
    <div className="rounded-sm border border-border bg-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Question {index + 1}</h3>
        <div className="flex items-center gap-1">
          {onMoveUp && (
            <Button type="button" variant="ghost" size="icon" onClick={onMoveUp} className="h-8 w-8">
              <ChevronUp className="h-4 w-4" />
            </Button>
          )}
          {onMoveDown && (
            <Button type="button" variant="ghost" size="icon" onClick={onMoveDown} className="h-8 w-8">
              <ChevronDown className="h-4 w-4" />
            </Button>
          )}
          <Button type="button" variant="ghost" size="icon" onClick={onRemove} className="h-8 w-8 text-destructive">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label>Type</Label>
          <Select value={question.type} onValueChange={(v) => handleTypeChange(v as QuestionKind)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="MULTIPLE_CHOICE">Multiple Choice</SelectItem>
              <SelectItem value="SHORT_ANSWER">Short Answer</SelectItem>
              <SelectItem value="NUMBER_SCALE">Number Scale</SelectItem>
              <SelectItem value="MOOD_METER">Mood Meter</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="md:col-span-2 space-y-2">
          <Label>Prompt</Label>
          <Input
            placeholder="Enter question prompt..."
            value={question.prompt}
            onChange={(e) => onChange({ ...question, prompt: e.target.value })}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label>Max Points</Label>
          <Input
            type="number"
            min={0}
            value={question.maxPoints}
            onChange={(e) =>
              onChange({ ...question, maxPoints: Number(e.target.value) || 0 })
            }
          />
        </div>

        <div className="space-y-2">
          <Label>Question Group</Label>
          <Select
            value={question.groupClientKey ?? '__NONE__'}
            onValueChange={(v) =>
              onChange({
                ...question,
                groupClientKey: v === '__NONE__' ? undefined : v,
              })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="No group" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__NONE__">No group</SelectItem>
              {groupOptions.map((group) => (
                <SelectItem key={group.clientKey} value={group.clientKey}>
                  {group.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {gradingMode === 'HYBRID' && (
          <div className="space-y-2">
            <Label>Grading Strategy</Label>
            <Select
              value={question.gradingStrategy ?? 'AUTO'}
              onValueChange={(v) =>
                onChange({ ...question, gradingStrategy: v as GradingStrategy })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="AUTO">Auto</SelectItem>
                <SelectItem value="MANUAL">Manual</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {question.type === 'MULTIPLE_CHOICE' && (
        <McqFields data={question.data ?? {}} onChange={handleDataChange} />
      )}
      {question.type === 'SHORT_ANSWER' && (
        <ShortAnswerFields data={question.data ?? {}} onChange={handleDataChange} />
      )}
      {question.type === 'NUMBER_SCALE' && (
        <NumberScaleFields data={question.data ?? {}} onChange={handleDataChange} />
      )}
      {question.type === 'MOOD_METER' && (
        <div className="rounded-md border border-border bg-muted/20 p-4">
          <p className="text-sm text-muted-foreground">
            Students will see the Yale RULER Mood Meter — a 4-quadrant grid of 20 emotions
            organized by energy level and pleasantness. No additional configuration needed.
          </p>
        </div>
      )}
    </div>
  );
}
