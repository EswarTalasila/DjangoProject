'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Download,
  FileText,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';

import { ExportCard } from '@/components/archive/ExportCard';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { HelpTip } from '@/components/ui/help-tip';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import {
  downloadCourseRoster,
  downloadCourseSubmissions,
  extractExportErrorMessage,
} from '@/lib/export-api';
import { triggerBrowserDownload } from '@/lib/utils';

/* ── Sentinel value so Radix Select never receives an empty string ── */
const NONE = '__NONE__';

/* ── Dropdown option sets ── */
const ROSTER_STATUS_OPTIONS = [
  { value: NONE, label: 'All Students' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'INACTIVE', label: 'Inactive' },
] as const;

const CATEGORY_OPTIONS = [
  { value: NONE, label: 'All Categories' },
  { value: 'QUIZ', label: 'Quiz' },
  { value: 'EXAM', label: 'Exam' },
  { value: 'HOMEWORK', label: 'Homework' },
  { value: 'SURVEY', label: 'Survey' },
  { value: 'REFLECTION', label: 'Reflection' },
  { value: 'OTHER', label: 'Other' },
] as const;

const SUBMISSION_STATUS_OPTIONS = [
  { value: NONE, label: 'All Statuses' },
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'GRADED', label: 'Graded' },
  { value: 'LATE', label: 'Late' },
] as const;

/* ── Props ── */
type QuickExportTabProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
};

/* ── Component ── */
export default function QuickExportTab({ role, canExportIdentifiable }: QuickExportTabProps) {
  /* ---- shared course data ---- */
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(true);

  /* ---- roster state ---- */
  const [rosterCourseId, setRosterCourseId] = useState('');
  const [rosterStatus, setRosterStatus] = useState(NONE);
  const [rosterIdentifiable, setRosterIdentifiable] = useState(false);
  const [downloadingRoster, setDownloadingRoster] = useState(false);

  /* ---- course submissions state ---- */
  const [subsCourseId, setSubsCourseId] = useState('');
  const [subsStartDate, setSubsStartDate] = useState('');
  const [subsEndDate, setSubsEndDate] = useState('');
  const [subsCategory, setSubsCategory] = useState(NONE);
  const [subsStatus, setSubsStatus] = useState(NONE);
  const [subsIncludeAnswers, setSubsIncludeAnswers] = useState(false);
  const [subsIdentifiable, setSubsIdentifiable] = useState(false);
  const [downloadingSubs, setDownloadingSubs] = useState(false);

  /* ---- load courses on mount ---- */
  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const data = await listCourses();
        if (!active) return;
        setCourses(data);
        if (data.length > 0) {
          const first = String(data[0].id);
          setRosterCourseId((prev) => prev || first);
          setSubsCourseId((prev) => prev || first);
        }
      } catch {
        toast.error('Failed to load courses.');
      } finally {
        if (active) setLoadingCourses(false);
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, []);

  const courseOptions = useMemo(
    () => courses.map((c) => ({ value: String(c.id), label: c.name })),
    [courses],
  );
  const hasCourses = courseOptions.length > 0;

  /* ---- helper: resolve sentinel to undefined ---- */
  function val(v: string): string | undefined {
    return v === NONE ? undefined : v || undefined;
  }

  /* ---- handlers ---- */
  async function handleRosterDownload() {
    if (!rosterCourseId) {
      toast.error('Select a course first.');
      return;
    }
    setDownloadingRoster(true);
    try {
      const { blob, filename } = await downloadCourseRoster(Number(rosterCourseId), {
        status: val(rosterStatus),
        identifiable: rosterIdentifiable || undefined,
      });
      triggerBrowserDownload(blob, filename);
      toast.success('Download started.');
    } catch (error) {
      toast.error(await extractExportErrorMessage(error));
    } finally {
      setDownloadingRoster(false);
    }
  }

  async function handleSubsDownload() {
    if (!subsCourseId) {
      toast.error('Select a course first.');
      return;
    }
    setDownloadingSubs(true);
    try {
      const { blob, filename } = await downloadCourseSubmissions(Number(subsCourseId), {
        startDate: subsStartDate || undefined,
        endDate: subsEndDate || undefined,
        category: val(subsCategory),
        status: val(subsStatus),
        includeAnswers: subsIncludeAnswers || undefined,
        identifiable: subsIdentifiable || undefined,
      });
      triggerBrowserDownload(blob, filename);
      toast.success('Download started.');
    } catch (error) {
      toast.error(await extractExportErrorMessage(error));
    } finally {
      setDownloadingSubs(false);
    }
  }

  /* ---- render ---- */
  return (
    <div className="space-y-4">
      {!loadingCourses && !hasCourses && (
        <div className="rounded-lg border border-dashed border-border bg-muted/30 px-4 py-5 text-sm text-muted-foreground">
          No active courses are available for live export yet. Create or restore a
          course first, then return here to download roster and submission data.
        </div>
      )}

      {/* ── Card 1: Course Roster ── */}
      <ExportCard
        icon={<Users className="size-5" />}
        title="Course Roster"
        description="Download a list of students enrolled in a course."
        helpText="Export enrollment data for a single course as a CSV file."
        defaultOpen
      >
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {/* Course selector */}
            <div className="space-y-1">
              <Label>Course <HelpTip text="Select which course to export data from." /></Label>
              <Select
                value={rosterCourseId}
                onValueChange={setRosterCourseId}
                disabled={loadingCourses || !hasCourses}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select course" />
                </SelectTrigger>
                <SelectContent>
                  {courseOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Status filter */}
            <div className="space-y-1">
              <Label>Status <HelpTip text="Filter students by enrollment status." /></Label>
              <Select value={rosterStatus} onValueChange={setRosterStatus}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROSTER_STATUS_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Identifiable checkbox */}
            {canExportIdentifiable && (
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Checkbox
                    checked={rosterIdentifiable}
                    onCheckedChange={(checked) => setRosterIdentifiable(checked === true)}
                  />
                  Include names &amp; emails
                  <HelpTip text="Include student names and email addresses. Requires EXPORT_IDENTIFIABLE permission." />
                </label>
              </div>
            )}
          </div>

          <Button
            onClick={() => void handleRosterDownload()}
            disabled={downloadingRoster || !rosterCourseId}
          >
            <Download className="mr-2 h-4 w-4" />
            {downloadingRoster ? 'Downloading...' : 'Download Roster'}
          </Button>
        </div>
      </ExportCard>

      {/* ── Card 2: Course Submissions ── */}
      <ExportCard
        icon={<FileText className="size-5" />}
        title="Course Submissions"
        description="Download submission records for a single course, with optional date and category filters."
        helpText="Export submission data for a specific course as a CSV file."
      >
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {/* Course selector */}
            <div className="space-y-1">
              <Label>Course <HelpTip text="Select which course to export data from." /></Label>
              <Select
                value={subsCourseId}
                onValueChange={setSubsCourseId}
                disabled={loadingCourses || !hasCourses}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select course" />
                </SelectTrigger>
                <SelectContent>
                  {courseOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Date range */}
            <div className="space-y-1">
              <Label>From <HelpTip text="Filter to submissions within this date range." /></Label>
              <Input
                type="date"
                value={subsStartDate}
                onChange={(e) => setSubsStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>To <HelpTip text="Filter to submissions within this date range." /></Label>
              <Input
                type="date"
                value={subsEndDate}
                onChange={(e) => setSubsEndDate(e.target.value)}
              />
            </div>

            {/* Category filter */}
            <div className="space-y-1">
              <Label>Category <HelpTip text="Filter by assignment category (Quiz, Exam, Homework, etc.)." /></Label>
              <Select value={subsCategory} onValueChange={setSubsCategory}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORY_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Status filter */}
            <div className="space-y-1">
              <Label>Status <HelpTip text="Filter by submission status." /></Label>
              <Select value={subsStatus} onValueChange={setSubsStatus}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SUBMISSION_STATUS_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Checkboxes */}
            <div className="flex flex-col justify-end gap-3">
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox
                  checked={subsIncludeAnswers}
                  onCheckedChange={(checked) => setSubsIncludeAnswers(checked === true)}
                />
                Include student answers
                <HelpTip text="Include the full text of student responses in the export." />
              </label>
              {canExportIdentifiable && (
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Checkbox
                    checked={subsIdentifiable}
                    onCheckedChange={(checked) => setSubsIdentifiable(checked === true)}
                  />
                  Include names &amp; emails
                  <HelpTip text="Include student names and email addresses. Requires EXPORT_IDENTIFIABLE permission." />
                </label>
              )}
            </div>
          </div>

          <Button
            onClick={() => void handleSubsDownload()}
            disabled={downloadingSubs || !subsCourseId}
          >
            <Download className="mr-2 h-4 w-4" />
            {downloadingSubs ? 'Downloading...' : 'Download Submissions'}
          </Button>
        </div>
      </ExportCard>

      {/* ── Permission notice for researchers without identifiable access ── */}
      {!canExportIdentifiable && role === 'RESEARCHER' && (
        <div className="rounded-sm border border-border bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
          The &quot;Include names &amp; emails&quot; option is disabled for your account. Request the
          <span className="font-mono"> EXPORT_IDENTIFIABLE </span>
          sudo permission to enable it.
        </div>
      )}
    </div>
  );
}
