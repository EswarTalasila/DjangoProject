"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createCourse } from "@/lib/course-api";

export default function CreateCoursePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Course name is required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const created = await createCourse(name.trim());
      toast.success(`Course created: ${created.name}`);
      router.push("/courses");
    } catch (submissionError: unknown) {
      const detail =
        typeof submissionError === "object" &&
        submissionError !== null &&
        "response" in submissionError &&
        typeof (submissionError as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === "string"
          ? (submissionError as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail ?? "Failed to create course."
          : "Failed to create course.";
      setError(detail);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl">
      <Card>
        <CardHeader>
          <CardTitle>Create Course</CardTitle>
          <CardDescription>Course names are the only required field at the API level.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <Input
              placeholder="Course name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={isSubmitting}
            />
            {error ? <p className="text-sm text-red-600">{error}</p> : null}
            <div className="flex gap-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating..." : "Create"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => router.push("/courses")}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
