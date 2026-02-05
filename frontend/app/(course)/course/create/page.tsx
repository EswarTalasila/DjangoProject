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
      {}

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