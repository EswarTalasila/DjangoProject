'use client';

import {
  Copy,
  Trash2,
  ChevronUp,
  ChevronDown,
  Plus,
} from 'lucide-react';
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
import { HelpTip } from '@/components/ui/help-tip';
import type {
  QuestionInput,
  QuestionKind,
  QuestionData,
  QuestionGroupInput,
  GradingStrategy,
} from '@/lib/assessment-api';
import { cn } from '@/lib/utils';
import ImagePicker from '@/components/media/ImagePicker';
import QuestionTypeConfig from './QuestionTypeConfig';

type BuilderGradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';

const TYPE_DEFAULTS: Record<QuestionKind, QuestionData> = {
  MULTIPLE_CHOICE: { choices: [{ prompt: '', score: 0 }], selectAll: false },
  SHORT_ANSWER: { caseSensitive: false, trim: true },
  NUMBER_SCALE: { min: 1, max: 5, target: null },
  MOOD_METER: {},
  FILE_UPLOAD: {},
};

type QuestionStudioProps = {
  question: QuestionInput | undefined;
  questionIndex: number;
  questionsCount: number;
  gradingMode: BuilderGradingMode;
  questionGroups: QuestionGroupInput[];
  selectedEffectiveRubricName: string | null;
  selectedGroupName: string | null;
  rubricSource: 'Question' | 'Group' | 'N/A';
  onChange: (updated: QuestionInput) => void;
  onRemove: () => void;
  onDuplicate: () => void;
  onMoveUp: (() => void) | null;
  onMoveDown: (() => void) | null;
  onAddQuestion: () => void;
};

export default function QuestionStudio({
  question,
  questionIndex,
  questionsCount,
  gradingMode,
  questionGroups,
  selectedEffectiveRubricName,
  selectedGroupName,
  rubricSource,
  onChange,
  onRemove,
  onDuplicate,
  onMoveUp,
  onMoveDown,
  onAddQuestion,
}: QuestionStudioProps) {
  if (!question) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-20 h-20 bg-muted rounded-2xl flex items-center justify-center mb-6 text-muted-foreground">
          <Plus className="h-10 w-10" />
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Ready to start?
        </h2>
        <p className="text-base text-muted-foreground max-w-sm mb-8">
          Add your first question to begin building this assessment.
        </p>
        <Button type="button" size="lg" onClick={onAddQuestion} className="gap-2">
          <Plus className="h-5 w-5" />
          Add First Question
        </Button>
      </div>
    );
  }

  function handleTypeChange(type: QuestionKind) {
    onChange({ ...question!, type, data: { ...TYPE_DEFAULTS[type] } });
  }

  function handleDataChange(data: QuestionData) {
    onChange({ ...question!, data });
  }

  return (
    <div className="space-y-6 pb-16">
      {/* Header section */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground">
              Question {questionIndex + 1}
            </h1>
            {selectedGroupName && (
              <span className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                {selectedGroupName}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium">
            Assessment Studio
          </p>
        </div>

        <div className="flex items-center gap-1">
          {onMoveUp && (
            <Button type="button" variant="ghost" size="icon" onClick={onMoveUp}>
              <ChevronUp className="h-5 w-5" />
            </Button>
          )}
          {onMoveDown && (
            <Button type="button" variant="ghost" size="icon" onClick={onMoveDown}>
              <ChevronDown className="h-5 w-5" />
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onDuplicate}
            className="text-muted-foreground hover:text-foreground"
          >
            <Copy className="h-4 w-4 mr-2" />
            Duplicate
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onRemove}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Rubric context bar */}
      <div className="rounded-lg border border-border bg-muted/30 p-4">
        <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <div>
            <dt className="text-muted-foreground text-xs mb-0.5">Rubric</dt>
            <dd className="font-medium text-foreground">
              {selectedEffectiveRubricName ?? 'None'}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs mb-0.5">Group</dt>
            <dd className="font-medium text-foreground">
              {selectedGroupName ?? 'None'}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs mb-0.5 flex items-center gap-1.5">
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

      {/* Main content card */}
      <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
        <div className="p-6 space-y-8">
          {/* Response format selector */}
          <div className="space-y-3">
            <Label className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
              Response Format
            </Label>
            <div className="flex flex-wrap gap-1.5 p-1.5 bg-muted rounded-lg border border-border w-fit">
              {(
                [
                  { value: 'MULTIPLE_CHOICE', label: 'Multiple Choice' },
                  { value: 'SHORT_ANSWER', label: 'Short Answer' },
                  { value: 'NUMBER_SCALE', label: 'Number Scale' },
                  { value: 'MOOD_METER', label: 'Mood Meter' },
                  { value: 'FILE_UPLOAD', label: 'File Upload' },
                ] as { value: QuestionKind; label: string }[]
              ).map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => handleTypeChange(value)}
                  className={cn(
                    'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                    question.type === value
                      ? 'bg-card text-foreground shadow-sm border border-border'
                      : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Question prompt */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                Question Prompt
              </Label>
              <span className="text-xs text-muted-foreground font-medium uppercase">
                Required
              </span>
            </div>
            <textarea
              value={question.prompt}
              onChange={(e) => onChange({ ...question, prompt: e.target.value })}
              placeholder="Enter the question text here..."
              className="w-full min-h-[140px] p-4 bg-muted/30 border border-border rounded-lg text-base text-foreground placeholder:text-muted-foreground resize-none leading-relaxed focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>
      </div>

      {/* Response configuration */}
      <div className="bg-card border border-border rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-border bg-muted/20">
          <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Response Configuration
          </h3>
        </div>
        <div className="p-6">
          <QuestionTypeConfig
            type={question.type}
            data={question.data ?? {}}
            onChange={handleDataChange}
          />
        </div>
      </div>

      {/* Supporting figure / image */}
      <div className="bg-card border border-border rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-border bg-muted/20">
          <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Supporting Figure
          </h3>
        </div>
        <div className="p-6">
          <ImagePicker
            image={null}
            onSelect={() => {
              // TODO: wire to question image API once QuestionImage endpoints exist
            }}
            onRemove={() => {
              // TODO: wire to question image API
            }}
          />
        </div>
      </div>

      {/* Grading & metadata */}
      <div className="bg-card border border-border rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-border bg-muted/20">
          <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Grading & Metadata
          </h3>
        </div>
        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <Label>Point Value</Label>
            <div className="relative">
              <Input
                type="number"
                min={0}
                value={question.maxPoints}
                onChange={(e) =>
                  onChange({ ...question, maxPoints: Number(e.target.value) || 0 })
                }
                className="pr-12 font-mono font-bold"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground uppercase">
                pts
              </span>
            </div>
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
                {questionGroups.map((group) => (
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
      </div>
    </div>
  );
}
