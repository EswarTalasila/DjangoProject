'use client';

import { useEffect, useMemo, useState } from 'react';
import { Download } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
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
  downloadCrossCourseSubmissions,
  extractExportErrorMessage,
} from '@/lib/export-api';

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

/* ── Download helper ── */
function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

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

  /* ---- cross-course submissions state ---- */
  const [crossStartDate, setCrossStartDate] = useState('');
  const [crossEndDate, setCrossEndDate] = useState('');
  const [crossCategory, setCrossCategory] = useState(NONE);
  const [crossStatus, setCrossStatus] = useState(NONE);
  const [crossIncludeAnswers, setCrossIncludeAnswers] = useState(false);
  const [crossIdentifiable, setCrossIdentifiable] = useState(false);
  const [downloadingCross, setDownloadingCross] = useState(false);

  const canUseCrossCourse = role === 'RESEARCHER' || role === 'ADMIN';

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

  async function handleCrossDownload() {
    if (!canUseCrossCourse) return;
    if (!crossStartDate || !crossEndDate) {
      toast.error('A date range is required for this download.');
      return;
    }
    setDownloadingCross(true);
    try {
      const { blob, filename } = await downloadCrossCourseSubmissions({
        startDate: crossStartDate,
        endDate: crossEndDate,
        category: val(crossCategory),
        status: val(crossStatus),
        includeAnswers: crossIncludeAnswers || undefined,
        identifiable: crossIdentifiable || undefined,
      });
      triggerBrowserDownload(blob, filename);
      toast.success('Download started.');
    } catch (error) {
      toast.error(await extractExportErrorMessage(error));
    } finally {
      setDownloadingCross(false);
    }
  }

  /* ---- render ---- */
  return (
    <div className="space-y-6">
      {/* ── Section 1: Course Roster ── */}
      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Course Roster</h2>
        <p className="text-xs text-muted-foreground">
          Download a list of students enrolled in a course.
        </p>

        <div className="grid gap-4 md:grid-cols-3">
          {/* Course selector */}
          <div className="space-y-1">
            <Label>Course</Label>
            <Select
              value={rosterCourseId}
              onValueChange={setRosterCourseId}
              disabled={loadingCourses}
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
            <Label>Status</Label>
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
      </section>

      {/* ── Section 2: Course Submissions ── */}
      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Course Submissions</h2>
        <p className="text-xs text-muted-foreground">
          Download submission records for a single course, with optional date and category filters.
        </p>

        <div className="grid gap-4 md:grid-cols-3">
          {/* Course selector */}
          <div className="space-y-1">
            <Label>Course</Label>
            <Select
              value={subsCourseId}
              onValueChange={setSubsCourseId}
              disabled={loadingCourses}
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
            <Label>From</Label>
            <Input
              type="date"
              value={subsStartDate}
              onChange={(e) => setSubsStartDate(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>To</Label>
            <Input
              type="date"
              value={subsEndDate}
              onChange={(e) => setSubsEndDate(e.target.value)}
            />
          </div>

          {/* Category filter */}
          <div className="space-y-1">
            <Label>Category</Label>
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
            <Label>Status</Label>
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
            </label>
            {canExportIdentifiable && (
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox
                  checked={subsIdentifiable}
                  onCheckedChange={(checked) => setSubsIdentifiable(checked === true)}
                />
                Include names &amp; emails
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
      </section>

      {/* ── Section 3: All Submissions (cross-course, hidden for TEACHER) ── */}
      {canUseCrossCourse && (
        <section className="rounded-sm border border-border bg-card p-4 space-y-4">
          <h2 className="text-lg font-semibold text-foreground">All Submissions</h2>
          <p className="text-xs text-muted-foreground">
            Download submission records across all courses. A date range is required.
          </p>

          <div className="grid gap-4 md:grid-cols-3">
            {/* Date range (required) */}
            <div className="space-y-1">
              <Label>From</Label>
              <Input
                type="date"
                value={crossStartDate}
                onChange={(e) => setCrossStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>To</Label>
              <Input
                type="date"
                value={crossEndDate}
                onChange={(e) => setCrossEndDate(e.target.value)}
              />
            </div>

            {/* Category filter */}
            <div className="space-y-1">
              <Label>Category</Label>
              <Select value={crossCategory} onValueChange={setCrossCategory}>
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
              <Label>Status</Label>
              <Select value={crossStatus} onValueChange={setCrossStatus}>
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
                  checked={crossIncludeAnswers}
                  onCheckedChange={(checked) => setCrossIncludeAnswers(checked === true)}
                />
                Include student answers
              </label>
              {canExportIdentifiable && (
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Checkbox
                    checked={crossIdentifiable}
                    onCheckedChange={(checked) => setCrossIdentifiable(checked === true)}
                  />
                  Include names &amp; emails
                </label>
              )}
            </div>
          </div>

          <Button
            onClick={() => void handleCrossDownload()}
            disabled={downloadingCross || !crossStartDate || !crossEndDate}
          >
            <Download className="mr-2 h-4 w-4" />
            {downloadingCross ? 'Downloading...' : 'Download All Submissions'}
          </Button>
        </section>
      )}

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
