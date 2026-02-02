"use client";

import { useEffect, useState } from "react";
import Cookies from "js-cookie";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Users, 
  TrendingUp, 
  ArrowRight, 
  Clock,
  Plus
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Mock Data
const performanceData = [
  { name: 'Mon', score: 85 },
  { name: 'Tue', score: 88 },
  { name: 'Wed', score: 92 },
  { name: 'Thu', score: 89 },
  { name: 'Fri', score: 94 },
];

const pendingGrading = [
  { id: 1, student: "Alice M.", assignment: "Resilience Reflection #3", time: "2 hrs ago" },
  { id: 2, student: "Jordan T.", assignment: "Unit 1 Assessment", time: "5 hrs ago" },
  { id: 3, student: "Casey L.", assignment: "Unit 1 Assessment", time: "1 day ago" },
];


export default function DashboardPage() {
    const [userName, setUserName] = useState("Instructor");
  useEffect(() => {
    const storedName = Cookies.get("user_name");
    if (storedName) setUserName(storedName);
  }, []);
  return (
    <div className="space-y-8">
      
      {/* HEADER */}
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">
            Welcome back,{" "}
            {/* 4. THE SPECIAL BOLD NAME STYLE */}
            <span className="font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-green-600 pr-2">
              {userName}
            </span>
          </h2>
          <p className="text-slate-500">Here is what's happening in your classroom today.</p>
        </div>
        <div className="flex items-center space-x-2">
           <Button>Create Assessment</Button>
        </div>
      </div>

      {/* KPI CARDS - Adjusted to grid-cols-3 since we removed Mood Meter */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Students</CardTitle>
            <Users className="h-4 w-4 text-slate-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">124</div>
            <p className="text-xs text-slate-500">+4 enrolled this week</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Resilience Score</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">88.5%</div>
            <p className="text-xs text-slate-500">+2.1% from last unit</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Grades</CardTitle>
            <Clock className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-slate-500">3 assessments need review</p>
          </CardContent>
        </Card>
      </div>

      {/* VISUALIZATION & ACTIONS */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        
        {/* Viz Chart */}
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Class Performance Trends</CardTitle>
            <CardDescription>Average scores across active courses (Last 5 Days)</CardDescription>
          </CardHeader>
          <CardContent className="pl-2">
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip cursor={{fill: 'transparent'}} />
                  <Bar dataKey="score" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Action Items */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Needs Grading</CardTitle>
            <CardDescription>Recent submissions requiring attention.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {pendingGrading.map((item) => (
                <div key={item.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
                  <div className="flex items-center space-x-4">
                    <div className="h-9 w-9 rounded-full bg-orange-100 flex items-center justify-center text-orange-600 font-bold text-xs">
                      {item.student.split(" ")[0][0]}{item.student.split(" ")[1][0]}
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-medium leading-none">{item.student}</p>
                      <p className="text-xs text-slate-500">{item.assignment}</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" className="text-blue-600 hover:text-blue-700">
                    Grade <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button variant="outline" className="w-full mt-2">View All</Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ACTIVE COURSES */}
      <Tabs defaultValue="active" className="space-y-4">
        <TabsList>
          <TabsTrigger value="active">Active Courses</TabsTrigger>
          <TabsTrigger value="archived">Archived</TabsTrigger>
        </TabsList>
        <TabsContent value="active" className="space-y-4">
           <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {/* Course 1 */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">Intro to Resilience (Period 1)</CardTitle>
                  <CardDescription>24 Students • High School</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-500">Progress</span>
                    <span className="font-bold">75%</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden mb-4">
                    <div className="h-full bg-blue-500 w-[75%]" />
                  </div>
                  <Button variant="secondary" className="w-full">Manage Course</Button>
                </CardContent>
              </Card>

              {/* Add New */}
              <Card className="flex flex-col items-center justify-center border-dashed border-2 shadow-none hover:bg-slate-50 cursor-pointer min-h-[180px]">
                  <div className="flex flex-col items-center space-y-2 text-slate-500">
                    <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center">
                       <Plus className="h-6 w-6" />
                    </div>
                    <span className="font-medium">Add New Course</span>
                  </div>
               </Card>
           </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}