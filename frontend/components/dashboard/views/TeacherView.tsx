'use client';

import { useState } from 'react';
import {
  Users,
  BookOpen,
  ClipboardCheck,
  Plus,
  MoreVertical,
  Search
} from 'lucide-react';

// UI Components (Assuming standard shadcn/ui structure)
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';

export default function TeacherView() {
  const [isLoading, setIsLoading] = useState(false);

  // Mock Data (Replace with API calls later)
  const stats = [
    { label: "Total Students", value: "142", icon: Users, color: "text-[#2b6ea4]" },
    { label: "Active Courses", value: "4", icon: BookOpen, color: "text-[#61323e]" },
    { label: "Pending Grades", value: "28", icon: ClipboardCheck, color: "text-[#754d28]" },
  ];

  const courses = [
    { id: 1, name: "Intro to Computer Science", code: "CS-101", students: 34, pending: 12 },
    { id: 2, name: "Data Structures & Algos", code: "CS-202", students: 28, pending: 5 },
    { id: 3, name: "Cybersecurity Fundamentals", code: "CYB-101", students: 40, pending: 8 },
    { id: 4, name: "Network Engineering", code: "NET-300", students: 40, pending: 3 },
  ];

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">

      {/* --- HEADER --- */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#61323e]">Teacher Dashboard</h1>
          <p className="text-[#754d28] mt-1">Manage your courses, assignments, and student grades.</p>
        </div>
        <Button className="bg-[#2b6ea4] hover:bg-[#205a86] text-white">
          <Plus className="mr-2 h-4 w-4" />
          Create New Course
        </Button>
      </div>

      {/* --- STATS OVERVIEW --- */}
      <div className="grid gap-4 md:grid-cols-3">
        {stats.map((stat, index) => (
          <Card key={index} className="border-[#ebe9e7] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-[#754d28]">
                {stat.label}
              </CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-[#61323e]">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* --- COURSE MANAGEMENT --- */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#61323e]">Your Courses</h2>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-[#754d28]" />
            <Input
              placeholder="Search courses..."
              className="pl-8 border-[#ebe9e7] focus-visible:ring-[#2b6ea4]"
            />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {courses.map((course) => (
            <Card key={course.id} className="border-[#ebe9e7] hover:border-[#2b6ea4] transition-colors cursor-pointer group">
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg font-semibold text-[#2b6ea4] group-hover:underline decoration-[#2b6ea4] underline-offset-4">
                      {course.name}
                    </CardTitle>
                    <p className="text-sm text-[#754d28] mt-1 font-mono bg-[#eff6f7] px-2 py-0.5 rounded inline-block">
                      {course.code}
                    </p>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="h-8 w-8 p-0 text-[#754d28]">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem>Generate Invite Code</DropdownMenuItem>
                      <DropdownMenuItem>View Roster</DropdownMenuItem>
                      <DropdownMenuItem className="text-red-600">Archive Course</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between text-sm text-[#754d28] border-t border-[#ebe9e7] pt-4 mt-2">
                  <div className="flex items-center">
                    <Users className="mr-1 h-4 w-4 opacity-70" />
                    {course.students} Students
                  </div>
                  <div className="flex items-center font-medium text-[#61323e]">
                    <ClipboardCheck className="mr-1 h-4 w-4 opacity-70" />
                    {course.pending} to grade
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
