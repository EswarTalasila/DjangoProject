'use client';

import { useState } from 'react';
import {
  Users,
  BookOpen,
  ClipboardCheck,
  Plus,
  Search,
  Shield,
  ShieldOff,
  UserPlus
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

interface ResearcherViewProps {
  hasSudo?: boolean;
  hasCreateTeacher?: boolean;
}

export default function ResearcherView({ hasSudo = false, hasCreateTeacher = false }: ResearcherViewProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showCodeDialog, setShowCodeDialog] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);

  const stats = [
    { label: "Total Students", value: "1,247", icon: Users, color: "text-[#2b6ea4]" },
    { label: "Active Courses", value: "42", icon: BookOpen, color: "text-[#61323e]" },
    { label: "Active Teachers", value: "18", icon: ClipboardCheck, color: "text-[#754d28]" },
  ];

  const teachers = [
    { id: 1, name: "Dr. Sarah Chen", email: "s.chen@university.edu", courses: 3, students: 89 },
    { id: 2, name: "Prof. James Miller", email: "j.miller@university.edu", courses: 2, students: 67 },
    { id: 3, name: "Dr. Emily Rodriguez", email: "e.rodriguez@university.edu", courses: 4, students: 112 },
    { id: 4, name: "Prof. Michael Thompson", email: "m.thompson@university.edu", courses: 2, students: 54 },
  ];

  const handleGenerateTeacherCode = () => {
    setGeneratedCode("TCH-" + Math.random().toString(36).substring(2, 8).toUpperCase());
    setShowCodeDialog(true);
  };

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      {/* --- HEADER --- */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#61323e]">Researcher Dashboard</h1>
          <p className="text-[#754d28] mt-1">View platform data and manage teacher accounts.</p>
        </div>
        
        <div className="flex items-center gap-3">
          {hasSudo ? (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-md">
              <Shield className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium text-green-700">Sudo Active</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-md">
              <ShieldOff className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-600">Read-Only</span>
            </div>
          )}
          
          <Dialog open={showCodeDialog} onOpenChange={setShowCodeDialog}>
            <DialogTrigger asChild>
              <Button 
                className="bg-[#2b6ea4] hover:bg-[#205a86] text-white"
                disabled={!hasCreateTeacher}
                onClick={handleGenerateTeacherCode}
              >
                <UserPlus className="mr-2 h-4 w-4" />
                Add Teacher
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Teacher Registration Code</DialogTitle>
                <DialogDescription>
                  Share this code with the teacher to register their account.
                </DialogDescription>
              </DialogHeader>
              <div className="mt-4 p-4 bg-[#eff6f7] border border-[#2b6ea4] rounded-md">
                <p className="text-center text-2xl font-mono font-bold text-[#2b6ea4]">
                  {generatedCode}
                </p>
              </div>
              <p className="text-sm text-[#754d28] mt-4">
                This code will expire in 7 days.
              </p>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {!hasCreateTeacher && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-sm text-amber-800">
            <strong>Note:</strong> You need sudo permissions with CREATE_TEACHER access to generate teacher registration codes. 
            Contact your administrator to request elevated permissions.
          </p>
        </div>
      )}

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

      {/* --- TEACHER MANAGEMENT (READ-ONLY) --- */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#61323e]">Teacher Accounts</h2>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-[#754d28]" />
            <Input
              placeholder="Search teachers..."
              className="pl-8 border-[#ebe9e7] focus-visible:ring-[#2b6ea4]"
            />
          </div>
        </div>

        <div className="rounded-md border border-[#ebe9e7]">
          <table className="w-full">
            <thead className="bg-[#faf9f8] border-b border-[#ebe9e7]">
              <tr>
                <th className="text-left p-4 text-sm font-medium text-[#754d28]">Name</th>
                <th className="text-left p-4 text-sm font-medium text-[#754d28]">Email</th>
                <th className="text-left p-4 text-sm font-medium text-[#754d28]">Courses</th>
                <th className="text-left p-4 text-sm font-medium text-[#754d28]">Students</th>
              </tr>
            </thead>
            <tbody>
              {teachers.map((teacher) => (
                <tr key={teacher.id} className="border-b border-[#ebe9e7] last:border-0 hover:bg-[#faf9f8]">
                  <td className="p-4 text-sm font-medium text-[#2b6ea4]">{teacher.name}</td>
                  <td className="p-4 text-sm text-[#754d28]">{teacher.email}</td>
                  <td className="p-4 text-sm text-[#61323e]">{teacher.courses}</td>
                  <td className="p-4 text-sm text-[#61323e]">{teacher.students}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
