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
import { Loader2, AlertCircle } from "lucide-react";

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

function LoginPageContent() {
  const router = useRouter();
  const [isHydrated, setIsHydrated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [adminBlocked, setAdminBlocked] = useState(false);

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: "", password: "" },
  });

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  // Shared success handler for both password and Google login
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

    // 1. Handle DRF Field Errors (e.g. { identifier: ["Invalid identifier"] })
    if (isApiErrorRecord(errorData)) {
      let hasFieldError = false;
      Object.entries(errorData).forEach(
        ([field, messages]) => {
          if (loginFieldNames.has(field as keyof LoginForm)) {
            const message = Array.isArray(messages)
              ? String(messages[0])
              : String(messages);
            form.setError(field as keyof LoginForm, {
              type: "manual",
              message,
            });
            hasFieldError = true;
          }
        },
      );
      if (hasFieldError) return;
    }

    // 2. Handle Generic/Detail Errors
    const errorMessage = toErrorMessage(
      error,
      "Authentication failed. Please check your credentials.",
    );

    if (errorMessage === "Admin accounts must use Django admin.") {
      setAdminBlocked(true);
    }
    setGeneralError(errorMessage);
  };

  // Standard identifier/password login
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

  const loginGoogle = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setIsLoading(true);
      setGeneralError(null);
      setAdminBlocked(false);
      try {
        const res = await api.post("/auth/sessions/oauth", {
          accessToken: tokenResponse.access_token,
        });
        handleLoginSuccess(res.data);
      } catch (error: unknown) {
        setGeneralError(toErrorMessage(error, "Google login failed."));
      } finally {
        setIsLoading(false);
      }
    },
    onError: () => {
      setGeneralError("Google login failed to initialize.");
      setIsLoading(false);
    },
  });

  return (
    <>
      <div className="flex flex-col space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
        <p className="text-sm text-slate-500">
          Enter your identifier to sign in to your account
        </p>
      </div>

      <div className="grid gap-6">
        {/* General Error Alert */}
        {generalError && (
          <Alert
            variant="destructive"
            className="bg-red-50 text-red-900 border-red-200"
          >
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
            {/* Identifier */}
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
                Students use username. Teachers and researchers can use username
                or email.
              </p>
              {form.formState.errors.identifier && (
                <p className="text-xs font-medium text-red-500 flex items-center mt-1">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {form.formState.errors.identifier.message}
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
              <p className="text-xs text-slate-500">
                Preparing secure sign-in…
              </p>
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
            <span className="bg-white px-2 text-slate-500">
              Or
            </span>
          </div>
        </div>

        {/* Google Login Button */}
        <Button
          onClick={() => loginGoogle()}
          disabled={!googleClientId || isLoading}
          variant="outline"
        >
          {isLoading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <svg
              className="mr-2 h-4 w-4"
              aria-hidden="true"
              focusable="false"
              data-prefix="fab"
              data-icon="google"
              role="img"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 488 512"
          >
              <path
              fill="currentColor"
              d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"
              ></path>
          </svg>
          )}
          Continue with Google
        </Button>
        {!googleClientId && (
          <p className="text-xs text-slate-500">
            Google sign-in is unavailable in this environment.
          </p>
        )}
      </div>

      <p className="px-8 text-center text-sm text-slate-500">
        <Link
          href="/register"
          className="hover:text-brand underline underline-offset-4"
        >
          Don&apos;t have an account? Sign Up
        </Link>
      </p>
      <p className="px-8 text-center text-sm text-slate-500">
        <a
          href={adminConsoleHref}
          className="hover:text-brand underline underline-offset-4"
        >
          Admin? Open Django Admin
        </a>
      </p>
    </>
  );
}

// Wrapper component to provide OAuth context
export default function LoginPage() {
  if (!googleClientId) {
    return <LoginPageContent />;
  }

  return (
    <GoogleOAuthProvider
      clientId={googleClientId}
    >
      <LoginPageContent />
    </GoogleOAuthProvider>
  );
}
