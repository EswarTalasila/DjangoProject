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
import { GoogleOAuthProvider, useGoogleLogin } from '@react-oauth/google';

// UI Components
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Loader2, CheckCircle2, ArrowRight, AlertCircle } from 'lucide-react';

// --- Types & Schemas ---

type CodeValidationResponse = {
  valid: boolean;
  code_type: 'STUDENT' | 'TEACHER' | 'RESEARCHER';
  context: {
    course_name?: string;
    teacher_name?: string;
    school?: string;
  };
};

const codeSchema = z.object({
  code: z.string().min(1, "Registration code is required").max(64),
});

const registerSchema = z.object({
  name: z.string().min(2, "Name is required"),
  username: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type CodeForm = z.infer<typeof codeSchema>;
type RegisterForm = z.infer<typeof registerSchema>;

// --- Components ---

function RegisterPageContent() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  // const [step, setStep] = useState<'CODE' | 'DETAILS'>('CODE');
  // const [validatedCode, setValidatedCode] = useState<string>('');
  // const [codeContext, setCodeContext] = useState<CodeValidationResponse | null>(null);
  // TODO: Remove forced code acceptance after api endpoint is implemented
  const [step, setStep] = useState<'CODE' | 'DETAILS'>('DETAILS');
  // FORCE the context so the UI has something to display
  const [validatedCode, setValidatedCode] = useState<string>('TEST-CODE-123');

  const [codeContext, setCodeContext] = useState<CodeValidationResponse | null>({
    valid: true,
    code_type: 'STUDENT',
    context: {
      course_name: 'Test Course',
      school: 'Test school'
    }
  });
  // Context ^

  const [generalError, setGeneralError] = useState<string | null>(null);
  // Forms
  const codeForm = useForm<CodeForm>({ resolver: zodResolver(codeSchema) });
  const detailsForm = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  // --- Handlers ---

  const handleApiError = (error: any, form: any) => {
    const errorData = error.response?.data;
    if (typeof errorData === 'object' && errorData !== null && !Array.isArray(errorData)) {
      let hasFieldError = false;
      Object.entries(errorData).forEach(([field, messages]) => {
        // @ts-ignore
        if (form.getValues(field) !== undefined) {
           // @ts-ignore
          form.setError(field as any, {
            type: 'manual',
            message: Array.isArray(messages) ? messages[0] : messages
          });
          hasFieldError = true;
        }
      });
      if (hasFieldError) return;
    }
    setGeneralError(errorData?.detail || "An unexpected error occurred.");
  };

  const onValidateCode = async (data: CodeForm) => {
    setIsLoading(true);
    setGeneralError(null);
    try {
      const request = USE_MOCK_API ? mockApi : api;
      const res = await request.post('/auth/validate-code', { code: data.code });
      const responseData = res.data as CodeValidationResponse;

      setValidatedCode(data.code);
      setCodeContext(responseData);

      if (responseData.context?.teacher_name) {
        detailsForm.setValue('name', responseData.context.teacher_name);
      }
      setStep('DETAILS');
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || "Invalid registration code.";
      codeForm.setError('code', { type: 'manual', message: errorMsg });
    } finally {
      setIsLoading(false);
    }
  };

  const onRegisterEmail = async (data: RegisterForm) => {
    setIsLoading(true);
    setGeneralError(null);
    try {
      const request = USE_MOCK_API ? mockApi : api;
      await request.post('/auth/register', { code: validatedCode, ...data });

      const loginRes = await request.post('/auth/login', {
        username: data.username,
        password: data.password
      });

      const { accessToken, role, name } = loginRes.data;
      Cookies.set('access_token', accessToken, { expires: 1 });
      if (role) Cookies.set('user_role', role);
      Cookies.set('user_name', name || "User", { expires: 1 });

      toast.success("Account created successfully!");
      router.push('/dashboard');

    } catch (error: any) {
      handleApiError(error, detailsForm);
    } finally {
      setIsLoading(false);
    }
  };

  const googleRegister = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setIsLoading(true);
      setGeneralError(null);
      try {
        const request = USE_MOCK_API ? mockApi : api;
        const res = await request.post('/auth/register', {
          code: validatedCode,
          accessToken: tokenResponse.access_token
        });
        // Handle Success
        const { accessToken, role, name } = res.data; // Assuming register returns tokens too
        Cookies.set('access_token', accessToken, { expires: 1 });
        if (role) Cookies.set('user_role', role);
        Cookies.set('user_name', name || "User", { expires: 1 });

        toast.success("Account created successfully!");
        router.push('/dashboard');
      } catch (error: any) {
        setGeneralError(error.response?.data?.detail || "Google registration failed.");
      } finally {
        setIsLoading(false);
      }
    },
    onError: () => setGeneralError("Google login window closed or failed to initialize."),
  });

  // --- Render ---

  return (
    <>
      <div className="flex flex-col space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">
          Create an account
        </h1>
        <p className="text-sm text-slate-500">
          {step === 'CODE'
            ? "Enter your invitation code to get started"
            : "Complete your profile to finish registration"}
        </p>
      </div>

      <div className="grid gap-6">

        {/* Step 1: Code Entry */}
        {step === 'CODE' && (
          <form onSubmit={codeForm.handleSubmit(onValidateCode)} className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="code">Registration Code</Label>
              <Input
                id="code"
                placeholder="e.g. AB12CD"
                className={`text-center text-lg tracking-widest uppercase ${codeForm.formState.errors.code ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                maxLength={20}
                disabled={isLoading}
                {...codeForm.register('code')}
              />
              {codeForm.formState.errors.code && (
                <p className="text-xs font-medium text-red-500 flex items-center mt-1">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {codeForm.formState.errors.code.message}
                </p>
              )}
            </div>
            <Button className="w-full" disabled={isLoading}>
              {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-2 h-4 w-4" />}
              Continue
            </Button>
          </form>
        )}

        {/* Step 2: Registration Details */}
        {step === 'DETAILS' && (
          <>
            {generalError && (
              <Alert variant="destructive" className="bg-red-50 text-red-900 border-red-200">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{generalError}</AlertDescription>
              </Alert>
            )}

            {/* Context Banner */}
            <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-900 flex items-start">
              <CheckCircle2 className="mr-2 h-5 w-5 text-blue-600 shrink-0" />
              <div>
                <p className="font-medium">Code Validated</p>
                <p className="text-blue-700 mt-1">
                  You are joining as a <strong>{codeContext?.code_type}</strong>
                  {codeContext?.context?.course_name && (
                    <span> for <strong>{codeContext.context.course_name}</strong></span>
                  )}
                  .
                </p>
              </div>
            </div>

            <form onSubmit={detailsForm.handleSubmit(onRegisterEmail)}>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Full Name</Label>
                  <Input
                    id="name"
                    placeholder="Jane Doe"
                    disabled={isLoading}
                    className={detailsForm.formState.errors.name ? 'border-red-500 focus-visible:ring-red-500' : ''}
                    {...detailsForm.register('name')}
                  />
                  {detailsForm.formState.errors.name && (
                    <p className="text-xs text-red-500 mt-1">{detailsForm.formState.errors.name.message}</p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="username">Email</Label>
                  <Input
                    id="username"
                    type="email"
                    placeholder="jane@example.com"
                    disabled={isLoading}
                    className={detailsForm.formState.errors.username ? 'border-red-500 focus-visible:ring-red-500' : ''}
                    {...detailsForm.register('username')}
                  />
                  {detailsForm.formState.errors.username && (
                    <p className="text-xs text-red-500 mt-1">{detailsForm.formState.errors.username.message}</p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    disabled={isLoading}
                    className={detailsForm.formState.errors.password ? 'border-red-500 focus-visible:ring-red-500' : ''}
                    {...detailsForm.register('password')}
                  />
                  {detailsForm.formState.errors.password && (
                    <p className="text-xs text-red-500 mt-1">{detailsForm.formState.errors.password.message}</p>
                  )}
                </div>

                <Button disabled={isLoading}>
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Create Account
                </Button>
              </div>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-slate-500">Or</span>
              </div>
            </div>

            <Button
              variant="outline"
              type="button"
              disabled={isLoading}
              onClick={() => googleRegister()}
            >
              <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
                <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
              </svg>
              Register with Google
            </Button>
          </>
        )}
      </div>

      <p className="px-8 text-center text-sm text-slate-500">
        <Link href="/login" className="hover:text-brand underline underline-offset-4">
          Already have an account? Sign In
        </Link>
      </p>
    </>
  );
}

export default function RegisterPage() {
  return (
    <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ""}>
      <RegisterPageContent />
    </GoogleOAuthProvider>
  );
}

