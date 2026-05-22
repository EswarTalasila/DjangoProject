"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import api from "@/lib/api";
import type { ApiError } from "@/lib/api-error";
import { isApiErrorRecord } from "@/lib/api-error";
import { toErrorMessage } from "@/lib/utils";

// OAuth Imports
import { GoogleOAuthProvider, useGoogleLogin } from "@react-oauth/google";

// UI Components
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Loader2, AlertCircle, FlaskConical } from "lucide-react";

const loginSchema = z.object({
  identifier: z.string().min(1, "Identifier is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;
type LoginSuccessPayload = {
  role?: string;
  name?: string;
};
const loginFieldNames = new Set<keyof LoginForm>(["identifier", "password"]);
const adminConsoleHref = "/admin/";
const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() || "";

const DEMO_ROLES = [
  {
    role: "RESEARCHER",
    label: "Researcher",
    description: "Design assessments, manage templates, and view analytics across all courses.",
  },
  {
    role: "TEACHER",
    label: "Teacher",
    description: "Create courses, build assignments, manage students, and track submissions.",
  },
  {
    role: "STUDENT",
    label: "Student",
    description: "View enrolled courses, complete assignments, and see your results.",
  },
] as const;

type GoogleLoginButtonProps = {
  isLoading: boolean;
  onStart: () => void;
  onSuccess: (data: LoginSuccessPayload) => void;
  onError: (msg: string) => void;
};

function GoogleLoginButton({ isLoading, onStart, onSuccess, onError }: GoogleLoginButtonProps) {
  const loginGoogle = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      onStart();
      try {
        const res = await api.post("/auth/sessions/oauth", {
          accessToken: tokenResponse.access_token,
        });
        onSuccess(res.data);
      } catch (error: unknown) {
        onError(toErrorMessage(error as ApiError, "Google login failed."));
      }
    },
    onError: () => {
      onError("Google login failed to initialize.");
    },
  });

  return (
    <Button onClick={() => loginGoogle()} disabled={isLoading} variant="outline">
      {isLoading ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <svg
          className="mr-2 h-4 w-4"
          aria-hidden="true"
          focusable="false"
          role="img"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 488 512"
        >
          <path
            fill="currentColor"
            d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"
          />
        </svg>
      )}
      Continue with Google
    </Button>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const [isHydrated, setIsHydrated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [adminBlocked, setAdminBlocked] = useState(false);
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [demoLoading, setDemoLoading] = useState<string | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: "", password: "" },
  });

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  const handleLoginSuccess = (data: LoginSuccessPayload) => {
    const { role, name } = data;
    if (role === "ADMIN") {
      Cookies.remove("user_name");
      setAdminBlocked(true);
      return;
    }
    Cookies.set("user_name", name || "Instructor", { expires: 1 });
    router.push("/dashboard");
  };

  const handleLoginError = (error: ApiError) => {
    const errorData = error.response?.data;

    if (isApiErrorRecord(errorData)) {
      let hasFieldError = false;
      Object.entries(errorData).forEach(([field, messages]) => {
        if (loginFieldNames.has(field as keyof LoginForm)) {
          const message = Array.isArray(messages) ? String(messages[0]) : String(messages);
          form.setError(field as keyof LoginForm, { type: "manual", message });
          hasFieldError = true;
        }
      });
      if (hasFieldError) return;
    }

    const errorMessage = toErrorMessage(error, "Authentication failed. Please check your credentials.");
    if (errorMessage === "Admin accounts must use Django admin.") {
      setAdminBlocked(true);
    }
    setGeneralError(errorMessage);
  };

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    setGeneralError(null);
    setAdminBlocked(false);
    try {
      const res = await api.post("/auth/sessions", data);
      handleLoginSuccess(res.data);
    } catch (error: unknown) {
      handleLoginError(error as ApiError);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoLogin = async (role: string) => {
    setDemoLoading(role);
    setDemoError(null);
    try {
      const res = await api.post("/auth/demo-sessions", { role });
      const { name } = res.data;
      Cookies.set("user_name", name || "Demo User", { expires: 1 });
      router.push("/dashboard");
    } catch (error: unknown) {
      setDemoError(toErrorMessage(error as ApiError, "Demo login is not available right now."));
      setDemoLoading(null);
    }
  };

  return (
    <>
      <div className="flex flex-col space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
        <p className="text-sm text-slate-500">
          Enter your identifier to sign in to your account
        </p>
      </div>

      <div className="grid gap-6">
        {generalError && (
          <Alert variant="destructive" className="bg-red-50 text-red-900 border-red-200">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{generalError}</AlertDescription>
          </Alert>
        )}
        {adminBlocked && (
          <Alert className="bg-blue-50 text-blue-900 border-blue-200">
            <AlertCircle className="h-4 w-4 text-blue-600" />
            <AlertTitle>Use Django Admin</AlertTitle>
            <AlertDescription>
              Admin accounts use the Django admin site.{" "}
              <a href={adminConsoleHref} className="underline underline-offset-4">
                Open Django Admin
              </a>
              .
            </AlertDescription>
          </Alert>
        )}

        {/* Keep the login form inert until hydration completes. This avoids a
            browser-native submit race on slow dev/test pages and ensures
            credentials are never leaked into the URL query string. */}
        <form method="post" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="identifier">Identifier</Label>
              <Input
                id="identifier"
                placeholder="e.g. jsmith or teacher@school.edu"
                type="text"
                autoCapitalize="none"
                autoComplete="username"
                autoCorrect="off"
                disabled={!isHydrated || isLoading}
                className={
                  form.formState.errors.identifier
                    ? "border-red-500 focus-visible:ring-red-500"
                    : ""
                }
                {...form.register("identifier")}
              />
              <p className="text-xs text-slate-500">
                Students use username. Teachers and researchers can use username or email.
              </p>
              {form.formState.errors.identifier && (
                <p className="text-xs font-medium text-red-500 flex items-center mt-1">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {form.formState.errors.identifier.message}
                </p>
              )}
            </div>

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
                disabled={!isHydrated || isLoading}
                className={
                  form.formState.errors.password
                    ? "border-red-500 focus-visible:ring-red-500"
                    : ""
                }
                {...form.register("password")}
              />
              {form.formState.errors.password && (
                <p className="text-xs font-medium text-red-500 flex items-center mt-1">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {form.formState.errors.password.message}
                </p>
              )}
            </div>

            {!isHydrated && (
              <p className="text-xs text-slate-500">Preparing secure sign-in…</p>
            )}
            <Button disabled={!isHydrated || isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Sign In
            </Button>
          </div>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-2 text-slate-500">Or</span>
          </div>
        </div>

        {googleClientId ? (
          <GoogleLoginButton
            isLoading={isLoading}
            onStart={() => { setIsLoading(true); setGeneralError(null); setAdminBlocked(false); }}
            onSuccess={handleLoginSuccess}
            onError={(msg) => { setGeneralError(msg); setIsLoading(false); }}
          />
        ) : (
          <p className="text-xs text-slate-500">
            Google sign-in is unavailable in this environment.
          </p>
        )}

        <Button
          variant="outline"
          onClick={() => { setShowDemoModal(true); setDemoError(null); }}
          disabled={isLoading}
          className="group border-[#6d28d9] text-[#6d28d9] transition-all duration-200 hover:bg-[#6d28d9] hover:text-white hover:shadow-md hover:shadow-violet-500/25 active:scale-[0.98]"
        >
          <FlaskConical className="mr-2 h-4 w-4 transition-transform duration-300 group-hover:rotate-12" />
          Try a Demo
        </Button>
      </div>

      <p className="px-8 text-center text-sm text-slate-500">
        <Link href="/register" className="hover:text-brand underline underline-offset-4">
          Don&apos;t have an account? Sign Up
        </Link>
      </p>
      <p className="px-8 text-center text-sm text-slate-500">
        <a href={adminConsoleHref} className="hover:text-brand underline underline-offset-4">
          Admin? Open Django Admin
        </a>
      </p>

      <Dialog open={showDemoModal} onOpenChange={setShowDemoModal}>
        <DialogContent className="sm:max-w-md">
          <DialogTitle className="text-lg font-semibold">Choose a demo role</DialogTitle>
          <DialogDescription className="text-sm text-slate-500">
            Explore Prism from any perspective. Pick a role to jump straight into a pre-loaded demo account.
          </DialogDescription>

          {demoError && (
            <Alert variant="destructive" className="bg-red-50 text-red-900 border-red-200">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <AlertDescription>{demoError}</AlertDescription>
            </Alert>
          )}

          <div className="grid gap-3 pt-1">
            {DEMO_ROLES.map(({ role, label, description }) => (
              <button
                key={role}
                onClick={() => handleDemoLogin(role)}
                disabled={demoLoading !== null}
                className="group flex items-start gap-4 rounded-lg border border-slate-200 p-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-[#6d28d9] hover:bg-[#6d28d9]/5 hover:shadow-lg hover:shadow-violet-500/10 active:translate-y-0 active:shadow-sm disabled:pointer-events-none disabled:opacity-50"
              >
                <div className="flex-1">
                  <p className="font-medium text-sm text-slate-900 transition-colors group-hover:text-[#6d28d9]">{label}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{description}</p>
                </div>
                {demoLoading === role && (
                  <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-[#6d28d9]" />
                )}
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function LoginPage() {
  if (!googleClientId) {
    return <LoginPageContent />;
  }

  return (
    <GoogleOAuthProvider clientId={googleClientId}>
      <LoginPageContent />
    </GoogleOAuthProvider>
  );
}
