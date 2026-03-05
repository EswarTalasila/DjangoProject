'use client';

import { useEffect, useState } from 'react';
import { Plus, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

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
import { listCourses, type CourseSummary } from '@/lib/course-api';
import {
  createWorkspace,
  listWorkspaces,
  type PackageWorkspace,
} from '@/lib/package-api';

type PackageListViewProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
  onOpenPackage: (workspaceId: number) => void;
};

const NO_COURSE = '__NONE__';

function toErrorMessage(error: unknown) {
  return (
    (error as { response?: { data?: { detail?: string } } })?.response?.data
      ?.detail ?? 'Unexpected error.'
  );
}

function statusLabel(status: string): { text: string; className: string } {
  switch (status) {
    case 'SEALED':
      return {
        text: 'Ready',
        className:
          'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      };
    case 'DRAFT':
    default:
      return {
        text: 'Draft',
        className:
          'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      };
  }
}

export default function PackageListView({
  role,
  canExportIdentifiable,
  onOpenPackage,
}: PackageListViewProps) {
  const [packages, setPackages] = useState<PackageWorkspace[]>([]);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createCourseId, setCreateCourseId] = useState(NO_COURSE);

  useEffect(() => {
    void loadData();
  }, []);

  async function loadData() {
    setIsLoading(true);
    try {
      const [workspaces, courseList] = await Promise.all([
        listWorkspaces(),
        listCourses(),
      ]);
      setPackages(workspaces);
      setCourses(courseList);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreate() {
    if (!createName.trim()) {
      toast.error('Package name is required.');
      return;
    }
    setIsCreating(true);
    try {
      const created = await createWorkspace({
        name: createName.trim(),
        description: createDescription.trim() || undefined,
        scopeCourseId:
          createCourseId === NO_COURSE ? null : Number(createCourseId),
      });
      setCreateName('');
      setCreateDescription('');
      setCreateCourseId(NO_COURSE);
      setShowCreateForm(false);
      toast.success('Package created.');
      onOpenPackage(created.id);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Your Packages</h2>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void loadData()}
            disabled={isLoading}
          >
            <RefreshCw className="mr-2 size-4" />
            Refresh
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => setShowCreateForm((prev) => !prev)}
          >
            <Plus className="mr-2 size-4" />
            New Package
          </Button>
        </div>
      </div>

      {showCreateForm && (
        <div className="rounded-sm border border-border bg-card p-4 space-y-3">
          <h3 className="text-sm font-semibold text-foreground">
            Create a New Package
          </h3>
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr]">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input
                value={createName}
                onChange={(event) => setCreateName(event.target.value)}
                placeholder="My Data Package"
              />
            </div>
            <div className="space-y-1">
              <Label>Associated Course</Label>
              <Select value={createCourseId} onValueChange={setCreateCourseId}>
                <SelectTrigger>
                  <SelectValue placeholder="All courses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_COURSE}>All courses</SelectItem>
                  {courses.map((course) => (
                    <SelectItem key={course.id} value={String(course.id)}>
                      {course.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Description</Label>
              <Input
                value={createDescription}
                onChange={(event) => setCreateDescription(event.target.value)}
                placeholder="Optional description"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => void handleCreate()}
              disabled={isCreating}
            >
              {isCreating ? 'Creating...' : 'Create'}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setShowCreateForm(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
          Loading packages...
        </div>
      ) : packages.length === 0 ? (
        <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
          No packages yet. Create one to organize your data exports.
        </div>
      ) : (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">
                  Name
                </th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">
                  Status
                </th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground hidden md:table-cell">
                  Description
                </th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground hidden lg:table-cell">
                  Last Modified
                </th>
                <th className="px-4 py-2 text-right font-medium text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {packages.map((pkg) => {
                const badge = statusLabel(pkg.status);
                return (
                  <tr
                    key={pkg.id}
                    className="border-b border-border last:border-b-0 hover:bg-accent/30 cursor-pointer transition-colors"
                    onClick={() => onOpenPackage(pkg.id)}
                  >
                    <td className="px-4 py-2 font-medium text-foreground">
                      {pkg.name}
                    </td>
                    <td className="px-4 py-2">
                      <span className={badge.className}>{badge.text}</span>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground truncate max-w-[200px] hidden md:table-cell">
                      {pkg.description || '\u2014'}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground hidden lg:table-cell">
                      {new Date(pkg.updatedAt).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={(event) => {
                          event.stopPropagation();
                          onOpenPackage(pkg.id);
                        }}
                      >
                        Open
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
