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

type ExportsHubViewProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
};

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

export default function ExportsHubView({ role, canExportIdentifiable }: ExportsHubViewProps) {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(true);

  const [rosterCourseId, setRosterCourseId] = useState('');
  const [rosterStatus, setRosterStatus] = useState('');
  const [rosterIdentifiable, setRosterIdentifiable] = useState(false);
  const [downloadingRoster, setDownloadingRoster] = useState(false);

  const [submissionsCourseId, setSubmissionsCourseId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [category, setCategory] = useState('');
  const [assessmentId, setAssessmentId] = useState('');
  const [assignmentId, setAssignmentId] = useState('');
  const [submissionStatus, setSubmissionStatus] = useState('');
  const [includeAnswers, setIncludeAnswers] = useState(false);
  const [submissionsIdentifiable, setSubmissionsIdentifiable] = useState(false);
  const [downloadingCourseSubs, setDownloadingCourseSubs] = useState(false);

  const [crossStartDate, setCrossStartDate] = useState('');
  const [crossEndDate, setCrossEndDate] = useState('');
  const [crossCategory, setCrossCategory] = useState('');
  const [crossAssessmentId, setCrossAssessmentId] = useState('');
  const [crossSubmissionStatus, setCrossSubmissionStatus] = useState('');
  const [crossIncludeAnswers, setCrossIncludeAnswers] = useState(false);
  const [crossIdentifiable, setCrossIdentifiable] = useState(false);
  const [downloadingCrossSubs, setDownloadingCrossSubs] = useState(false);

  const canUseCrossCourse = role === 'RESEARCHER' || role === 'ADMIN';

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const data = await listCourses();
        if (!active) return;
        setCourses(data);
        setRosterCourseId((prev) => prev || String(data[0]?.id ?? ''));
        setSubmissionsCourseId((prev) => prev || String(data[0]?.id ?? ''));
      } catch {
        toast.error('Failed to load courses for export.');
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
    () => courses.map((course) => ({ value: String(course.id), label: course.name })),
    [courses],
  );

  async function handleRosterExport() {
    if (!rosterCourseId) {
      toast.error('Select a course first.');
      return;
    }
    setDownloadingRoster(true);
    try {
      const { blob, filename } = await downloadCourseRoster(Number(rosterCourseId), {
        status: rosterStatus || undefined,
        identifiable: rosterIdentifiable || undefined,
      });
      triggerBrowserDownload(blob, filename);
      toast.success('Roster export started.');
    } catch (error) {
      toast.error(await extractExportErrorMessage(error));
    } finally {
      setDownloadingRoster(false);
    }
  }

  async function handleCourseSubmissionsExport() {
    if (!submissionsCourseId) {
      toast.error('Select a course first.');
      return;
    }
    setDownloadingCourseSubs(true);
    try {
      const { blob, filename } = await downloadCourseSubmissions(Number(submissionsCourseId), {
        startDate: startDate || undefined,
        endDate: endDate || undefined,
        category: category || undefined,
        assessmentId: assessmentId ? Number(assessmentId) : undefined,
        assignmentId: assignmentId ? Number(assignmentId) : undefined,
        status: submissionStatus || undefined,
        includeAnswers: includeAnswers || undefined,
        identifiable: submissionsIdentifiable || undefined,
      });
      triggerBrowserDownload(blob, filename);
      toast.success('Course submissions export started.');
    } catch (error) {
      toast.error(await extractExportErrorMessage(error));
    } finally {
      setDownloadingCourseSubs(false);
    }
  }

  async function handleCrossCourseExport() {
    if (!canUseCrossCourse) return;
    if (!crossStartDate || !crossEndDate) {
      toast.error('Cross-course export requires start and end date.');
      return;
    }
    setDownloadingCrossSubs(true);
    try {
      const { blob, filename } = await downloadCrossCourseSubmissions({
        startDate: crossStartDate,
        endDate: crossEndDate,
        category: crossCategory || undefined,
        assessmentId: crossAssessmentId ? Number(crossAssessmentId) : undefined,
        status: crossSubmissionStatus || undefined,
        includeAnswers: crossIncludeAnswers || undefined,
        identifiable: crossIdentifiable || undefined,
      });
      triggerBrowserDownload(blob, filename);
      toast.success('Cross-course submissions export started.');
    } catch (error) {
      toast.error(await extractExportErrorMessage(error));
    } finally {
      setDownloadingCrossSubs(false);
    }
  }

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Exports</h1>
        <p className="text-muted-foreground mt-1">
          Download CSV exports for roster and submissions data.
        </p>
      </div>

      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Course Roster</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="space-y-1">
            <Label>Course</Label>
            <Select
              value={rosterCourseId}
              onValueChange={setRosterCourseId}
              disabled={loadingCourses}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select course" />
              </SelectTrigger>
              <SelectContent>
                {courseOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Enrollment Status (optional)</Label>
            <Input
              placeholder="ACTIVE, DROPPED..."
              value={rosterStatus}
              onChange={(event) => setRosterStatus(event.target.value)}
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={rosterIdentifiable}
                disabled={!canExportIdentifiable}
                onCheckedChange={(checked) => setRosterIdentifiable(checked === true)}
              />
              Include identifiable fields
            </label>
          </div>
        </div>
        <Button onClick={() => void handleRosterExport()} disabled={downloadingRoster || !rosterCourseId}>
          <Download className="mr-2 h-4 w-4" />
          {downloadingRoster ? 'Exporting...' : 'Download Roster CSV'}
        </Button>
      </section>

      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Course Submissions</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="space-y-1">
            <Label>Course</Label>
            <Select
              value={submissionsCourseId}
              onValueChange={setSubmissionsCourseId}
              disabled={loadingCourses}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select course" />
              </SelectTrigger>
              <SelectContent>
                {courseOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Start Date (optional)</Label>
            <Input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>End Date (optional)</Label>
            <Input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Category (optional)</Label>
            <Input value={category} onChange={(event) => setCategory(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Assessment ID (optional)</Label>
            <Input value={assessmentId} onChange={(event) => setAssessmentId(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Assignment ID (optional)</Label>
            <Input value={assignmentId} onChange={(event) => setAssignmentId(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Submission Status (optional)</Label>
            <Input
              placeholder="NOT_STARTED, IN_PROGRESS..."
              value={submissionStatus}
              onChange={(event) => setSubmissionStatus(event.target.value)}
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={includeAnswers}
                onCheckedChange={(checked) => setIncludeAnswers(checked === true)}
              />
              Include answer details
            </label>
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={submissionsIdentifiable}
                disabled={!canExportIdentifiable}
                onCheckedChange={(checked) => setSubmissionsIdentifiable(checked === true)}
              />
              Include identifiable fields
            </label>
          </div>
        </div>
        <Button
          onClick={() => void handleCourseSubmissionsExport()}
          disabled={downloadingCourseSubs || !submissionsCourseId}
        >
          <Download className="mr-2 h-4 w-4" />
          {downloadingCourseSubs ? 'Exporting...' : 'Download Course Submissions CSV'}
        </Button>
      </section>

      {canUseCrossCourse && (
        <section className="rounded-sm border border-border bg-card p-4 space-y-4">
          <h2 className="text-lg font-semibold text-foreground">Cross-Course Submissions</h2>
          <p className="text-xs text-muted-foreground">
            This export requires both start and end date filters.
          </p>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="space-y-1">
              <Label>Start Date</Label>
              <Input
                type="date"
                value={crossStartDate}
                onChange={(event) => setCrossStartDate(event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>End Date</Label>
              <Input
                type="date"
                value={crossEndDate}
                onChange={(event) => setCrossEndDate(event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>Category (optional)</Label>
              <Input
                value={crossCategory}
                onChange={(event) => setCrossCategory(event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>Assessment ID (optional)</Label>
              <Input
                value={crossAssessmentId}
                onChange={(event) => setCrossAssessmentId(event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>Submission Status (optional)</Label>
              <Input
                placeholder="SUBMITTED, GRADED..."
                value={crossSubmissionStatus}
                onChange={(event) => setCrossSubmissionStatus(event.target.value)}
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox
                  checked={crossIncludeAnswers}
                  onCheckedChange={(checked) => setCrossIncludeAnswers(checked === true)}
                />
                Include answer details
              </label>
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox
                  checked={crossIdentifiable}
                  disabled={!canExportIdentifiable}
                  onCheckedChange={(checked) => setCrossIdentifiable(checked === true)}
                />
                Include identifiable fields
              </label>
            </div>
          </div>
          <Button
            onClick={() => void handleCrossCourseExport()}
            disabled={downloadingCrossSubs || !crossStartDate || !crossEndDate}
          >
            <Download className="mr-2 h-4 w-4" />
            {downloadingCrossSubs ? 'Exporting...' : 'Download Cross-Course CSV'}
          </Button>
        </section>
      )}

      {!canExportIdentifiable && role === 'RESEARCHER' && (
        <div className="rounded-sm border border-border bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
          Identifiable exports are disabled for your account. Request the
          <span className="font-mono"> EXPORT_IDENTIFIABLE </span>
          sudo permission to enable those options.
        </div>
      )}
    </div>
  );
}
