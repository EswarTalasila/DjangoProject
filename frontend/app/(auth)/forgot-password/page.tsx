"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

import { completePasswordReset } from "@/lib/password-reset-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const resetSchema = z
  .object({
    identifier: z.string().trim().min(1, "Identifier is required"),
    resetCode: z.string().trim().min(1, "Reset code is required"),
    newPassword: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string().min(8, "Confirm password is required"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type ResetForm = z.infer<typeof resetSchema>;
type ApiError = { response?: { data?: { detail?: string } } };

export default function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const form = useForm<ResetForm>({
    resolver: zodResolver(resetSchema),
    defaultValues: {
      identifier: "",
      resetCode: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  async function onSubmit(data: ResetForm) {
    setIsLoading(true);
    setGeneralError(null);
    try {
      await completePasswordReset({
        identifier: data.identifier,
        resetCode: data.resetCode,
        newPassword: data.newPassword,
        confirmPassword: data.confirmPassword,
      });
      setIsSuccess(true);
      toast.success("Password reset successful.");
    } catch (error: unknown) {
      const detail = (error as ApiError).response?.data?.detail;
      setGeneralError(detail || "Password reset failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <>
      <div className="flex flex-col space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Reset your password</h1>
        <p className="text-sm text-slate-500">
          Enter your identifier and one-time reset code.
        </p>
      </div>

      <div className="grid gap-6">
        {isSuccess ? (
          <Alert className="bg-green-50 text-green-900 border-green-200">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertTitle>Password updated</AlertTitle>
            <AlertDescription>
              Your password was reset. You can now sign in with your new password.
            </AlertDescription>
          </Alert>
        ) : (
          <>
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

            <form onSubmit={form.handleSubmit(onSubmit)}>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="identifier">Identifier</Label>
                  <Input
                    id="identifier"
                    placeholder="username or email"
                    disabled={isLoading}
                    {...form.register("identifier")}
                  />
                  {form.formState.errors.identifier && (
                    <p className="text-xs font-medium text-red-500">
                      {form.formState.errors.identifier.message}
                    </p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="resetCode">Reset code</Label>
                  <Input
                    id="resetCode"
                    placeholder="RESET-XXXXXX"
                    disabled={isLoading}
                    {...form.register("resetCode")}
                  />
                  {form.formState.errors.resetCode && (
                    <p className="text-xs font-medium text-red-500">
                      {form.formState.errors.resetCode.message}
                    </p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="newPassword">New password</Label>
                  <Input
                    id="newPassword"
                    type="password"
                    disabled={isLoading}
                    {...form.register("newPassword")}
                  />
                  {form.formState.errors.newPassword && (
                    <p className="text-xs font-medium text-red-500">
                      {form.formState.errors.newPassword.message}
                    </p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="confirmPassword">Confirm password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    disabled={isLoading}
                    {...form.register("confirmPassword")}
                  />
                  {form.formState.errors.confirmPassword && (
                    <p className="text-xs font-medium text-red-500">
                      {form.formState.errors.confirmPassword.message}
                    </p>
                  )}
                </div>

                <p className="text-xs text-slate-500">
                  Password must include uppercase, lowercase, number, and special character.
                </p>

                <Button disabled={isLoading}>
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Reset password
                </Button>
              </div>
            </form>
          </>
        )}

        <p className="px-8 text-center text-sm text-slate-500">
          <Link
            href="/login"
            className="hover:text-brand underline underline-offset-4"
          >
            Back to login
          </Link>
        </p>
      </div>
    </>
  );
}
