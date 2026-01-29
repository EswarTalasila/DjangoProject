'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Cookies from 'js-cookie';
import api from '@/lib/api';
import { toast } from 'sonner';

// UI Components
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// Icons
import { Loader2 } from 'lucide-react';
import Image from 'next/image'; // For Google Icon

const loginSchema = z.object({
  username: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    try {
      const res = await api.post('/auth/login', data);
      
      const { accessToken, role, name } = res.data;
      
      Cookies.set('access_token', accessToken, { expires: 1 });
      if (role) Cookies.set('user_role', role);

      toast.success(`Welcome back, ${name || 'Instructor'}!`);
      router.push('/dashboard'); 

    } catch (error: any) {
      const errorMessage = typeof error.response?.data === 'string' 
        ? error.response.data 
        : error.response?.data?.detail || "Invalid credentials.";
      
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="flex flex-col space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">
          Welcome back
        </h1>
        <p className="text-sm text-slate-500">
          Enter your email to sign in to your account
        </p>
      </div>

      <div className="grid gap-6">
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <div className="grid gap-4">
            
            {/* Username / Email */}
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                placeholder="username@school.k12.nc.us"
                type="email"
                autoCapitalize="none"
                autoComplete="email"
                autoCorrect="off"
                disabled={isLoading}
                {...form.register('username')}
              />
              {form.formState.errors.username && (
                <p className="text-xs text-red-500">
                  {form.formState.errors.username.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link 
                  href="/forgot-password" 
                  className="text-xs text-blue-600 hover:text-blue-500 hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                disabled={isLoading}
                {...form.register('password')}
              />
              {form.formState.errors.password && (
                <p className="text-xs text-red-500">
                  {form.formState.errors.password.message}
                </p>
              )}
            </div>

            <Button disabled={isLoading}>
              {isLoading && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Sign In
            </Button>
          </div>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-2 text-slate-500">
              Or continue with
            </span>
          </div>
        </div>

        {/* Google Login Button */}
        {/* Note: This requires the Google SVG in public/google.svg */}
        <Button variant="outline" type="button" disabled={isLoading} onClick={() => alert("Wire up to /api/auth/google")}>
          {/* If you don't have the SVG yet, use text */}
          {/* <Image src="/google.svg" alt="Google" width={16} height={16} className="mr-2" /> */}
          <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
            <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
          </svg>
          Google
        </Button>
      </div>

      <p className="px-8 text-center text-sm text-slate-500">
        <Link 
          href="/register" 
          className="hover:text-brand underline underline-offset-4"
        >
          Don&apos;t have an account? Sign Up
        </Link>
      </p>
    </>
  );
}
