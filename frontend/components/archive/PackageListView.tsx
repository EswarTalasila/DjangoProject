'use client';

import { useEffect, useState } from 'react';
import { Package, Plus, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
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
import { StatusBadge } from '@/components/ui/status-badge';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import {
  createWorkspace,
  listWorkspaces,
  type PackageWorkspace,
} from '@/lib/package-api';
import { toErrorMessage } from '@/lib/utils';

type PackageListViewProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
  onOpenPackage: (workspaceId: number) => void;
};

const NO_COURSE = '__NONE__';

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
          <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
            <DialogTrigger asChild>
              <Button type="button" size="sm">
                <Plus className="mr-2 size-4" />
                New Package
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create a New Package</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-1">
                  <Label>
                    Name
                    <HelpTip text="A descriptive name for this data package." />
                  </Label>
                  <Input
                    value={createName}
                    onChange={(event) => setCreateName(event.target.value)}
                    placeholder="My Data Package"
                  />
                </div>
                <div className="space-y-1">
                  <Label>
                    Associated Course
                    <HelpTip text="Scope this package to a single course, or leave as 'All' for cross-course data." />
                  </Label>
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
                  <Label>
                    Description
                    <HelpTip text="Optional notes about what this package contains." />
                  </Label>
                  <Input
                    value={createDescription}
                    onChange={(event) => setCreateDescription(event.target.value)}
                    placeholder="Optional description"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setShowCreateForm(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => void handleCreate()}
                    disabled={isCreating}
                  >
                    {isCreating ? 'Creating...' : 'Create'}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
          Loading packages...
        </div>
      ) : packages.length === 0 ? (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <Package className="mx-auto mb-2 size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No packages yet. Create one to organize your data exports.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {packages.map((pkg) => (
            <div
              key={pkg.id}
              className="rounded-lg border border-border bg-card p-4 hover:bg-accent/30 cursor-pointer transition-colors"
              onClick={() => onOpenPackage(pkg.id)}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-foreground">{pkg.name}</span>
                <StatusBadge status={pkg.status} />
              </div>
              <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                {pkg.description || '\u2014'}
              </p>
              <p className="mt-3 text-xs text-muted-foreground">
                {new Date(pkg.updatedAt).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
