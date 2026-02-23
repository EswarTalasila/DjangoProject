'use client';

import { useEffect, useMemo, useState } from 'react';
import { BookOpen, ClipboardCheck, Search, Users } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { listCourses, type CourseSummary } from '@/lib/course-api';

export default function AdminView() {
  const [search, setSearch] = useState('');
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const filteredCourses = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return courses;
    return courses.filter((course) => course.name.toLowerCase().includes(needle));
  }, [courses, search]);

  useEffect(() => {
    async function load() {
      setLoadError(null);
      try {
        const data = await listCourses();
        setCourses(data);
      } catch {
        setLoadError('Failed to load courses.');
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, []);

  const totalStudents = courses.reduce((sum, course) => sum + course.studentCount, 0);
  const totalAssignments = courses.reduce((sum, course) => sum + course.assignmentIds.length, 0);
  const stats = [
    { label: 'Total Students', value: String(totalStudents), icon: Users, color: 'text-[#2b6ea4]' },
    { label: 'Active Courses', value: String(courses.length), icon: BookOpen, color: 'text-[#61323e]' },
    {
      label: 'Total Assignments',
      value: String(totalAssignments),
      icon: ClipboardCheck,
      color: 'text-[#754d28]',
    },
  ];

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#61323e]">Admin Dashboard</h1>
          <p className="text-[#754d28] mt-1">Cross-course visibility for active classrooms and workload.</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.label} className="border-[#ebe9e7] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-[#754d28]">{stat.label}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-[#61323e]">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#61323e]">Courses</h2>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-[#754d28]" />
            <Input
              placeholder="Search courses..."
              className="pl-8 border-[#ebe9e7] focus-visible:ring-[#2b6ea4]"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}
        {isLoading ? <p className="text-sm text-[#754d28]">Loading courses...</p> : null}
        {!isLoading && !filteredCourses.length ? (
          <p className="text-sm text-[#754d28]">No courses found.</p>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCourses.map((course) => (
            <Card
              key={course.id}
              className="border-[#ebe9e7] hover:border-[#2b6ea4] transition-colors cursor-pointer group"
            >
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold text-[#2b6ea4] group-hover:underline decoration-[#2b6ea4] underline-offset-4">
                  {course.name}
                </CardTitle>
                <p className="text-sm text-[#754d28] mt-1 font-mono bg-[#eff6f7] px-2 py-0.5 rounded inline-block w-fit">
                  Course #{course.id}
                </p>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between text-sm text-[#754d28] border-t border-[#ebe9e7] pt-4 mt-2">
                  <div className="flex items-center">
                    <Users className="mr-1 h-4 w-4 opacity-70" />
                    {course.studentCount} Students
                  </div>
                  <div className="flex items-center font-medium text-[#61323e]">
                    <ClipboardCheck className="mr-1 h-4 w-4 opacity-70" />
                    {course.assignmentIds.length} assignments
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
