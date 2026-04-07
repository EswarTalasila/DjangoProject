'use client';

import { memo, useEffect, useRef, useState } from 'react';
import {
  Settings,
  BarChart3,
  Info,
  ShieldCheck,
  ChevronRight,
  AlertCircle,
  Plus,
  Eye,
  Pencil,
  Trash2,
  ArrowLeft,
  Unlink2,
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
  QuestionGroupInput,
  ScoringPolicy,
  QuestionKind,
  GradingStrategy,
} from '@/lib/assessment-api';
import type { Rubric } from '@/lib/rubric-api';
import { cn } from '@/lib/utils';
import type { StudioValidationIssue } from './validation';

type BuilderGradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';

const GRADING_MODES: { value: BuilderGradingMode; label: string; desc: string }[] = [
  { value: 'AUTO', label: 'Automatic', desc: 'Pre-defined answers for instant results.' },
  { value: 'MANUAL', label: 'Manual', desc: 'All responses require manual review.' },
  { value: 'HYBRID', label: 'Hybrid', desc: 'Mix of auto-graded and manual review.' },
];

const SCORING_POLICIES: { value: ScoringPolicy; label: string }[] = [
  { value: 'STANDARD', label: 'Standard scoring' },
  { value: 'COMPLETION', label: 'Completion (100 on submit)' },
];

type ValidationRailProps = {
  // Assessment-level settings
  gradingMode: BuilderGradingMode;
  onGradingModeChange: (mode: BuilderGradingMode) => void;
  scoringPolicy: ScoringPolicy;
  onScoringPolicyChange: (policy: ScoringPolicy) => void;
  // Active question context
  activeQuestion: QuestionInput | undefined;
  onActiveQuestionPointsChange: (points: number) => void;
  onActiveQuestionGradingStrategyChange: (strategy: GradingStrategy) => void;
  // Validation
  questions: QuestionInput[];
  questionsError: string | null;
  issues: StudioValidationIssue[];
  activeIssue: StudioValidationIssue | null;
  onNavigateToIssue: (issue: StudioValidationIssue) => void;
  // Rubric binding
  isRubricEnabled: boolean;
  isRubricsLoading: boolean;
  rubrics: Rubric[];
  assessmentRubricId: number | null;
  onAssessmentRubricChange: (rubricId: number | null) => void;
  activeQuestionRubricId: number | null;
  onActiveQuestionRubricChange: (rubricId: number | null) => void;
  onOpenQuickRubric: () => void;
  onOpenInlineRubricEditor: (rubricId: number | null | undefined) => void;
  onOpenRubricPreview: (rubricId: number | null | undefined) => void;
  // Group management
  questionGroups: QuestionGroupInput[];
  newGroupName: string;
  onNewGroupNameChange: (value: string) => void;
  onCreateGroup: () => void;
  assignGroupKey: string;
  onAssignGroupKeyChange: (value: string) => void;
  selectedAssignGroup: QuestionGroupInput | null;
  questionCountByGroupKey: Map<string, number>;
  rubricById: Map<number, Rubric>;
  onUpdateQuestionGroup: (
    clientKey: string,
    patch: Partial<QuestionGroupInput>,
  ) => void;
  onRemoveQuestionGroup: (clientKey: string) => void;
  onUngroupActiveQuestion: () => void;
  // Category
  category: string;
  categoryOptions: string[];
  isCategoryComposerOpen: boolean;
  onCategoryComposerOpenChange: (open: boolean) => void;
  categoryDraft: string;
  onCategoryDraftChange: (draft: string) => void;
  onApplyCategoryDraft: () => void;
  onCancelCategoryComposer: () => void;
  onChooseCategoryFromBank: (category: string) => void;
  onClearCategory: () => void;
  onBackToEditor?: () => void;
};

function formatQuestionKind(kind: QuestionKind): string {
  switch (kind) {
    case 'MULTIPLE_CHOICE':
      return 'Multiple Choice';
    case 'SHORT_ANSWER':
      return 'Short Answer';
    case 'NUMBER_SCALE':
      return 'Number Scale';
    case 'MOOD_METER':
      return 'Mood Meter';
    default:
      return kind;
  }
}

function ValidationRail({
  gradingMode,
  onGradingModeChange,
  scoringPolicy,
  onScoringPolicyChange,
  activeQuestion,
  onActiveQuestionPointsChange,
  onActiveQuestionGradingStrategyChange,
  questions,
  questionsError,
  issues,
  activeIssue,
  onNavigateToIssue,
  isRubricEnabled,
  isRubricsLoading,
  rubrics,
  assessmentRubricId,
  onAssessmentRubricChange,
  activeQuestionRubricId,
  onActiveQuestionRubricChange,
  onOpenQuickRubric,
  onOpenInlineRubricEditor,
  onOpenRubricPreview,
  questionGroups,
  newGroupName,
  onNewGroupNameChange,
  onCreateGroup,
  assignGroupKey,
  onAssignGroupKeyChange,
  selectedAssignGroup,
  questionCountByGroupKey,
  rubricById,
  onUpdateQuestionGroup,
  onRemoveQuestionGroup,
  onUngroupActiveQuestion,
  category,
  categoryOptions,
  isCategoryComposerOpen,
  onCategoryComposerOpenChange,
  categoryDraft,
  onCategoryDraftChange,
  onApplyCategoryDraft,
  onCancelCategoryComposer,
  onChooseCategoryFromBank,
  onClearCategory,
  onBackToEditor,
}: ValidationRailProps) {
  const rubricSectionRef = useRef<HTMLElement>(null);
  const groupSectionRef = useRef<HTMLElement>(null);
  const [highlightedSection, setHighlightedSection] = useState<
    'rubricBinding' | 'groupManager' | null
  >(null);

  useEffect(() => {
    if (!activeIssue || activeIssue.panel !== 'settings') return;

    let target: HTMLElement | null = null;
    let nextSection: typeof highlightedSection = null;
    if (activeIssue.section === 'rubricBinding') {
      target = rubricSectionRef.current;
      nextSection = 'rubricBinding';
    } else if (activeIssue.section === 'groupManager') {
      target = groupSectionRef.current;
      nextSection = 'groupManager';
    }
    if (!target || !nextSection) return;

    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setHighlightedSection(nextSection);
    const timeout = window.setTimeout(() => setHighlightedSection(null), 1800);
    return () => window.clearTimeout(timeout);
  }, [activeIssue]);

  const totalPoints = questions.reduce(
    (sum, q) => sum + (q.maxPoints || 0),
    0,
  );

  return (
    <div className="flex flex-col h-full gap-6 p-4 overflow-y-auto">
      <div className="lg:hidden -m-4 mb-2 p-3 border-b border-border bg-card flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onBackToEditor}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          Settings
        </span>
      </div>

      {/* Assessment Configuration */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Settings className="h-4 w-4 text-primary" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
            Configuration
          </h3>
        </div>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
                Grading Mode
              </Label>
              <HelpTip text="AUTO: no rubrics. MANUAL: rubrics required. HYBRID: per-question choice." />
            </div>
            <Select
              value={gradingMode}
              onValueChange={(v) =>
                onGradingModeChange(v as BuilderGradingMode)
              }
            >
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {GRADING_MODES.map((gm) => (
                  <SelectItem key={gm.value} value={gm.value}>
                    {gm.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[10px] text-muted-foreground leading-relaxed">
              {GRADING_MODES.find((gm) => gm.value === gradingMode)?.desc}
            </p>
          </div>

          <div className="space-y-1.5">
            <Label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
              Scoring Policy
            </Label>
            <Select
              value={scoringPolicy}
              onValueChange={(v) =>
                onScoringPolicyChange(v as ScoringPolicy)
              }
            >
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCORING_POLICIES.map((sp) => (
                  <SelectItem key={sp.value} value={sp.value}>
                    {sp.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Category */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
                Category
              </Label>
              <HelpTip text="Optional tag to organize assessments." />
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {category ? (
                <span className="inline-flex items-center rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-foreground">
                  {category}
                </span>
              ) : (
                <span className="text-[10px] text-muted-foreground">
                  No category
                </span>
              )}
              {!isCategoryComposerOpen && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-6 px-2 text-[10px]"
                  onClick={() => onCategoryComposerOpenChange(true)}
                >
                  <Plus className="mr-0.5 h-3 w-3" />
                  {category ? 'Change' : 'Add'}
                </Button>
              )}
              {category && !isCategoryComposerOpen && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[10px]"
                  onClick={onClearCategory}
                >
                  Clear
                </Button>
              )}
            </div>
            {isCategoryComposerOpen && (
              <div className="rounded border border-border bg-muted/30 p-2 space-y-2">
                <div className="flex items-center gap-1.5">
                  <Input
                    placeholder="Type a category..."
                    className="h-7 text-xs"
                    value={categoryDraft}
                    onChange={(e) => onCategoryDraftChange(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        onApplyCategoryDraft();
                      }
                      if (e.key === 'Escape') {
                        e.preventDefault();
                        onCancelCategoryComposer();
                      }
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 px-2 text-[10px]"
                    onClick={onApplyCategoryDraft}
                    disabled={!categoryDraft.trim()}
                  >
                    Set
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-[10px]"
                    onClick={onCancelCategoryComposer}
                  >
                    Cancel
                  </Button>
                </div>
                {categoryOptions.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {categoryOptions.slice(0, 8).map((option) => (
                      <Button
                        key={option}
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-5 px-1.5 text-[9px]"
                        onClick={() => onChooseCategoryFromBank(option)}
                      >
                        {option}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Question Context */}
      {activeQuestion && (
        <section className="p-3 bg-muted/30 rounded-lg border border-border">
          <div className="flex items-center gap-2 mb-2">
            <div className="flex items-center gap-1.5">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-foreground">
                Active Question
              </h3>
              <HelpTip text="Shows the currently selected question's type, relative weight in this assessment, and whether it can be graded automatically." />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-[11px] text-muted-foreground">Type</span>
              <span className="text-[10px] font-medium text-foreground">
                {formatQuestionKind(activeQuestion.type)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[11px] text-muted-foreground">Weight</span>
              <span className="text-[10px] font-mono font-medium text-foreground">
                {totalPoints > 0
                  ? ((activeQuestion.maxPoints / totalPoints) * 100).toFixed(1)
                  : '0.0'}
                %
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[11px] text-muted-foreground">
                Auto-gradable
              </span>
              <ShieldCheck
                className={cn(
                  'h-3.5 w-3.5',
                  activeQuestion.type !== 'SHORT_ANSWER'
                    ? 'text-green-500'
                    : 'text-muted-foreground',
                )}
              />
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-border/70 space-y-2">
            <div className="space-y-1.5">
              <Label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
                Question Value
              </Label>
              {activeQuestion.type === 'MULTIPLE_CHOICE' ? (
                <div className="rounded border border-border bg-card px-2.5 py-2">
                  <p className="text-sm font-mono font-semibold text-foreground">
                    {activeQuestion.maxPoints} pts
                  </p>
                  <p className="mt-1 text-[10px] text-muted-foreground">
                    Derived automatically from this question&apos;s choice values.
                  </p>
                </div>
              ) : (
                <div className="relative">
                  <Input
                    type="number"
                    min={0}
                    value={activeQuestion.maxPoints}
                    onChange={(e) =>
                      onActiveQuestionPointsChange(Number(e.target.value) || 0)
                    }
                    className="h-8 pr-10 text-xs font-mono font-semibold"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-muted-foreground uppercase">
                    pts
                  </span>
                </div>
              )}
            </div>

            {gradingMode === 'HYBRID' && (
              <div className="space-y-1.5">
                <Label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
                  Grading Strategy
                </Label>
                <Select
                  value={activeQuestion.gradingStrategy ?? 'AUTO'}
                  onValueChange={(value) =>
                    onActiveQuestionGradingStrategyChange(value as GradingStrategy)
                  }
                >
                  <SelectTrigger className="h-8 text-xs">
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
        </section>
      )}

      {/* Rubric Binding */}
      <section
        ref={rubricSectionRef}
        className={cn(
          'rounded-lg transition-shadow',
          highlightedSection === 'rubricBinding' && 'ring-2 ring-amber-400/70 ring-offset-2 ring-offset-muted/30',
        )}
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5">
            <h3 className="text-xs font-bold text-foreground">Rubric Binding</h3>
            <HelpTip text="Attach rubric templates to manual questions." />
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 text-[10px]"
            onClick={onOpenQuickRubric}
          >
            <Plus className="mr-0.5 h-3 w-3" /> New
          </Button>
        </div>

        {!isRubricEnabled ? (
          <div className="rounded border border-border bg-muted/40 p-2.5 text-[10px] text-muted-foreground space-y-0.5">
            <p className="font-medium text-foreground">
              Rubrics disabled in AUTO mode
            </p>
            <p>Switch to MANUAL or HYBRID to attach rubrics.</p>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="space-y-1.5">
              <Label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
                Assessment Default
              </Label>
              <div className="grid grid-cols-[1fr_auto_auto] gap-1.5">
                <Select
                  value={
                    assessmentRubricId != null
                      ? String(assessmentRubricId)
                      : '__NONE__'
                  }
                  onValueChange={(value) =>
                    onAssessmentRubricChange(
                      value === '__NONE__' ? null : Number(value),
                    )
                  }
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="No assessment rubric" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__NONE__">No assessment rubric</SelectItem>
                    {rubrics.map((rubric) => (
                      <SelectItem
                        key={rubric.id}
                        value={String(rubric.id)}
                        disabled={rubric.status !== 'ACTIVE'}
                      >
                        {rubric.title}
                        {rubric.status !== 'ACTIVE' ? ' (Archived)' : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  disabled={assessmentRubricId == null}
                  onClick={() => onOpenInlineRubricEditor(assessmentRubricId)}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  disabled={assessmentRubricId == null}
                  onClick={() => onOpenRubricPreview(assessmentRubricId)}
                >
                  <Eye className="h-3.5 w-3.5" />
                </Button>
              </div>
              <p className="text-[10px] text-muted-foreground">
                {assessmentRubricId != null
                  ? `Default rubric: ${
                      rubricById.get(assessmentRubricId)?.title ?? 'Unavailable'
                    }`
                  : 'No assessment-level default rubric'}
              </p>
              {assessmentRubricId != null && (
                <p className="text-[10px] text-amber-700 dark:text-amber-400">
                  Assessment-level rubric is active. Question and group rubrics must remain clear.
                </p>
              )}
            </div>

            {isRubricsLoading ? (
              <p className="text-[10px] text-muted-foreground">
                Loading rubrics...
              </p>
            ) : (
              <div className="space-y-1.5">
                <Label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
                  Active Question
                </Label>
                <div className="grid grid-cols-[1fr_auto_auto] gap-1.5">
                  <Select
                    value={
                      activeQuestionRubricId != null
                        ? String(activeQuestionRubricId)
                        : '__NONE__'
                    }
                    onValueChange={(value) =>
                      onActiveQuestionRubricChange(
                        value === '__NONE__' ? null : Number(value),
                      )
                    }
                    disabled={assessmentRubricId != null || !activeQuestion}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="No question rubric" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__NONE__">No question rubric</SelectItem>
                      {rubrics.map((rubric) => (
                        <SelectItem
                          key={rubric.id}
                          value={String(rubric.id)}
                          disabled={rubric.status !== 'ACTIVE'}
                        >
                          {rubric.title}
                          {rubric.status !== 'ACTIVE' ? ' (Archived)' : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    disabled={activeQuestionRubricId == null || assessmentRubricId != null}
                    onClick={() =>
                      onOpenInlineRubricEditor(
                        activeQuestionRubricId,
                      )
                    }
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    disabled={activeQuestionRubricId == null || assessmentRubricId != null}
                    onClick={() =>
                      onOpenRubricPreview(activeQuestionRubricId)
                    }
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <p className="text-[10px] text-muted-foreground">
                  {activeQuestion
                    ? activeQuestionRubricId != null
                      ? `Rubric for active question: ${
                          rubricById.get(activeQuestionRubricId)?.title ?? 'Unavailable'
                        }`
                      : 'No question-level rubric on the active question'
                    : 'Select a question to assign a question-level rubric'}
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Group Manager */}
      <section
        ref={groupSectionRef}
        className={cn(
          'rounded-lg transition-shadow',
          highlightedSection === 'groupManager' && 'ring-2 ring-amber-400/70 ring-offset-2 ring-offset-muted/30',
        )}
      >
        <div className="flex items-center gap-1.5 mb-2">
          <h3 className="text-xs font-bold text-foreground">Groups</h3>
          <HelpTip text="Group questions to share rubric settings." />
        </div>

        <div className="space-y-2">
          <div className="grid grid-cols-[1fr_auto] gap-1.5">
            <Input
              placeholder="New group name"
              className="h-8 text-xs"
              value={newGroupName}
              onChange={(e) => onNewGroupNameChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  onCreateGroup();
                }
              }}
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={onCreateGroup}
            >
              <Plus className="mr-0.5 h-3 w-3" /> Add
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-1.5">
            <Select value={assignGroupKey} onValueChange={onAssignGroupKeyChange}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Assign to group" />
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

          {questionGroups.length > 0 && selectedAssignGroup && (
            <div className="rounded border border-border p-2 space-y-2">
              <div className="flex items-center gap-1.5">
                <Input
                  value={selectedAssignGroup.name}
                  onChange={(e) =>
                    onUpdateQuestionGroup(selectedAssignGroup.clientKey, {
                      name: e.target.value,
                    })
                  }
                  placeholder="Group name"
                  className="h-7 text-xs"
                />
                <span className="rounded bg-muted px-1.5 py-0.5 text-[9px] text-muted-foreground whitespace-nowrap">
                  {questionCountByGroupKey.get(selectedAssignGroup.clientKey) ??
                    0}
                </span>
              </div>

              {isRubricEnabled && (
                <div className="grid grid-cols-[1fr_auto_auto] gap-1.5">
                  <Select
                    value={
                      selectedAssignGroup.rubricId != null
                        ? String(selectedAssignGroup.rubricId)
                        : '__NONE__'
                    }
                    onValueChange={(value) =>
                      onUpdateQuestionGroup(selectedAssignGroup.clientKey, {
                        rubricId:
                          value === '__NONE__' ? null : Number(value),
                      })
                    }
                    disabled={assessmentRubricId != null}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="Group rubric" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__NONE__">No group rubric</SelectItem>
                      {rubrics.map((rubricOption) => (
                        <SelectItem
                          key={rubricOption.id}
                          value={String(rubricOption.id)}
                          disabled={rubricOption.status !== 'ACTIVE'}
                        >
                          {rubricOption.title}
                          {rubricOption.status !== 'ACTIVE'
                            ? ' (Archived)'
                            : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    disabled={selectedAssignGroup.rubricId == null || assessmentRubricId != null}
                    onClick={() =>
                      onOpenInlineRubricEditor(selectedAssignGroup.rubricId)
                    }
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    disabled={selectedAssignGroup.rubricId == null || assessmentRubricId != null}
                    onClick={() =>
                      onOpenRubricPreview(selectedAssignGroup.rubricId)
                    }
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}

              <p className="text-[10px] text-muted-foreground">
                {selectedAssignGroup.rubricId
                  ? `Rubric: ${
                      rubricById.get(selectedAssignGroup.rubricId)?.title ??
                      'Unavailable'
                    }`
                  : 'No rubric attached'}
              </p>
              {assessmentRubricId != null && (
                <p className="text-[10px] text-amber-700 dark:text-amber-400">
                  Clear the assessment rubric before assigning a group rubric.
                </p>
              )}

              {activeQuestion?.groupClientKey === selectedAssignGroup.clientKey && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={onUngroupActiveQuestion}
                >
                  <Unlink2 className="mr-1 h-3.5 w-3.5" />
                  Remove Active Question From Group
                </Button>
              )}

              {(questionCountByGroupKey.get(selectedAssignGroup.clientKey) ?? 0) === 0 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="w-full text-xs text-destructive hover:text-destructive"
                  onClick={() =>
                    onRemoveQuestionGroup(selectedAssignGroup.clientKey)
                  }
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  Delete Empty Group
                </Button>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Validation issues */}
      <section className="mt-auto">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-amber-500 dark:text-amber-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-foreground">
              Validation
            </h3>
          </div>
            <span
            className={cn(
              'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold',
              issues.length === 0
                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
            )}
          >
            {issues.length} issue{issues.length !== 1 ? 's' : ''}
          </span>
        </div>

        {questionsError && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 mb-3">
            <p className="text-sm text-destructive font-medium">
              {questionsError}
            </p>
          </div>
        )}

        <div className="space-y-2">
          {issues.map((issue) => (
            <button
              key={issue.id}
              type="button"
              onClick={() => onNavigateToIssue(issue)}
              className="w-full flex items-center gap-3 p-3 bg-card border border-border rounded-lg text-left hover:border-amber-300 dark:hover:border-amber-700 transition-colors group"
            >
              <AlertCircle className="h-5 w-5 text-amber-500 dark:text-amber-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground">
                  {issue.title}
                </p>
                <p className="text-xs text-muted-foreground">
                  {issue.detail}
                </p>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground/50 group-hover:text-amber-500 transition-colors shrink-0" />
            </button>
          ))}

          {/* All good */}
          {issues.length === 0 && questions.length > 0 && (
            <div className="p-4 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800/30 rounded-lg text-center">
              <p className="text-sm font-bold text-green-700 dark:text-green-400">
                All checks passed
              </p>
              <p className="text-xs text-green-600/70 dark:text-green-400/70 mt-1">
                Assessment is ready to save.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default memo(ValidationRail);
