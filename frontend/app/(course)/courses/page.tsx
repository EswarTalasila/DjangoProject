"use client";

import { useEffect, useMemo, useState } from "react";
import Cookies from "js-cookie";
import { ClipboardCheck, Plus, Search, Users } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RegistrationCodeDialog } from "@/components/codes/RegistrationCodeDialog";
import { Input } from "@/components/ui/input";
import { createCourse, listCourses, type CourseSummary } from "@/lib/course-api";
import { createStudentRegistrationCode } from "@/lib/registration-code-api";

export default function CoursesPage() {
  const [userName, setUserName] = useState("Instructor");
  const [search, setSearch] = useState("");
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [registrationCode, setRegistrationCode] = useState<string | null>(null);
  const [isCodeDialogOpen, setIsCodeDialogOpen] = useState(false);

  useEffect(() => {
    const storedName = Cookies.get("user_name");
    if (storedName) setUserName(storedName);
  }, []);

  const filteredCourses = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return courses;
    return courses.filter((course) => course.name.toLowerCase().includes(needle));
  }, [courses, search]);

  async function loadCourses() {
    setLoadError(null);
    try {
      const data = await listCourses();
      setCourses(data);
    } catch {
      setLoadError("Failed to load courses.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadCourses();
  }, []);

  async function handleCreateCourse() {
    const name = window.prompt("Course name");
    if (!name || !name.trim()) return;

    setIsMutating(true);
    try {
      await createCourse(name.trim());
      toast.success("Course created.");
      await loadCourses();
    } catch (error: unknown) {
      const detail =
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ===
          "string"
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "Failed to create course.";
      toast.error(detail);
    } finally {
      setIsMutating(false);
    }
  }

  async function handleGenerateInviteCode(courseId: number) {
    setIsMutating(true);
    try {
      const code = await createStudentRegistrationCode(courseId);
      setRegistrationCode(code);
      setIsCodeDialogOpen(true);
    } catch (error: unknown) {
      const detail =
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ===
          "string"
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "Failed to generate invite code.";
      toast.error(detail);
    } finally {
      setIsMutating(false);
    }
  }

  return (
    <div className="space-y-8">
      <RegistrationCodeDialog
        open={isCodeDialogOpen}
        onOpenChange={setIsCodeDialogOpen}
        code={registrationCode}
      />

      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">
            Welcome back,{" "}
            <span className="font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-green-600 pr-2">
              {userName}
            </span>
          </h2>
          <p className="text-slate-500">Manage your live courses and invite codes from one place.</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={handleCreateCourse} disabled={isMutating}>
            <Plus className="mr-2 h-4 w-4" />
            Create Course
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        <div className="relative w-full md:w-72">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-500" />
          <Input
            placeholder="Search courses..."
            className="pl-8"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}
        {isLoading ? <p className="text-sm text-slate-500">Loading courses...</p> : null}

        {!isLoading && !filteredCourses.length ? (
          <p className="text-sm text-slate-500">No courses found.</p>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCourses.map((course) => (
            <Card key={course.id}>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">{course.name}</CardTitle>
                <CardDescription>Course #{course.id}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between text-sm text-slate-600">
                  <div className="flex items-center gap-1">
                    <Users className="h-4 w-4" />
                    {course.studentCount} students
                  </div>
                  <div className="flex items-center gap-1">
                    <ClipboardCheck className="h-4 w-4" />
                    {course.assignmentIds.length} assignments
                  </div>
                </div>
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => handleGenerateInviteCode(course.id)}
                  disabled={isMutating}
                >
                  Generate Student Invite Code
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
