"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

import { validateResetCode, completePasswordReset } from "@/lib/password-reset-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PasswordStrengthChecklist } from "@/components/ui/password-strength-checklist";

const validateSchema = z.object({
  identifier: z.string().trim().min(1, "Identifier is required"),
  resetCode: z.string().trim().min(1, "Reset code is required"),
});

const resetSchema = z
  .object({
    newPassword: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must include at least one uppercase letter")
      .regex(/[a-z]/, "Must include at least one lowercase letter")
      .regex(/[0-9]/, "Must include at least one number")
      .regex(/[^A-Za-z0-9]/, "Must include at least one special character"),
    confirmPassword: z.string().min(8, "Confirm password is required"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type ValidateForm = z.infer<typeof validateSchema>;
type ResetForm = z.infer<typeof resetSchema>;
type ApiError = { response?: { data?: { detail?: string } } };

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<"VALIDATE" | "RESET">("VALIDATE");
  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);
  const [validatedIdentifier, setValidatedIdentifier] = useState("");
  const [validatedResetCode, setValidatedResetCode] = useState("");

  const validateForm = useForm<ValidateForm>({
    resolver: zodResolver(validateSchema),
    defaultValues: { identifier: "", resetCode: "" },
  });

  const resetForm = useForm<ResetForm>({
    resolver: zodResolver(resetSchema),
    defaultValues: { newPassword: "", confirmPassword: "" },
  });

  async function onValidate(data: ValidateForm) {
    setIsLoading(true);
    setGeneralError(null);
    try {
      await validateResetCode(data.identifier, data.resetCode);
      setValidatedIdentifier(data.identifier);
      setValidatedResetCode(data.resetCode);
      setStep("RESET");
    } catch (error: unknown) {
      const detail = (error as ApiError).response?.data?.detail;
      setGeneralError(detail || "Invalid or expired reset code.");
    } finally {
      setIsLoading(false);
    }
  }

  async function onReset(data: ResetForm) {
    // State guard: if identifier/resetCode missing, force back to step 1
    if (!validatedIdentifier || !validatedResetCode) {
      setStep("VALIDATE");
      setGeneralError("Session expired. Please verify your reset code again.");
      return;
    }

    setIsLoading(true);
    setGeneralError(null);
    try {
      await completePasswordReset({
        identifier: validatedIdentifier,
        resetCode: validatedResetCode,
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
          {step === "VALIDATE"
            ? "Enter your identifier and one-time reset code."
            : "Set your new password."}
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

            {step === "VALIDATE" && (
              <form onSubmit={validateForm.handleSubmit(onValidate)}>
                <div className="grid gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="identifier">Identifier</Label>
                    <Input
                      id="identifier"
                      placeholder="username or email"
                      disabled={isLoading}
                      {...validateForm.register("identifier")}
                    />
                    {validateForm.formState.errors.identifier && (
                      <p className="text-xs font-medium text-red-500">
                        {validateForm.formState.errors.identifier.message}
                      </p>
                    )}
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="resetCode">Reset code</Label>
                    <Input
                      id="resetCode"
                      placeholder="RESET-XXXXXX"
                      disabled={isLoading}
                      {...validateForm.register("resetCode")}
                    />
                    {validateForm.formState.errors.resetCode && (
                      <p className="text-xs font-medium text-red-500">
                        {validateForm.formState.errors.resetCode.message}
                      </p>
                    )}
                  </div>

                  <Button disabled={isLoading}>
                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Verify code
                  </Button>
                </div>
              </form>
            )}

            {step === "RESET" && (
              <form onSubmit={resetForm.handleSubmit(onReset)}>
                <div className="grid gap-4">
                  <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-900 flex items-start">
                    <CheckCircle2 className="mr-2 h-5 w-5 text-blue-600 shrink-0" />
                    <p className="text-blue-700">
                      Code verified for <strong>{validatedIdentifier}</strong>. Enter your new password below.
                    </p>
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="newPassword">New password</Label>
                    <Input
                      id="newPassword"
                      type="password"
                      disabled={isLoading}
                      {...resetForm.register("newPassword")}
                    />
                    {resetForm.formState.errors.newPassword && (
                      <p className="text-xs font-medium text-red-500">
                        {resetForm.formState.errors.newPassword.message}
                      </p>
                    )}
                    <PasswordStrengthChecklist password={resetForm.watch("newPassword") || ""} />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="confirmPassword">Confirm password</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      disabled={isLoading}
                      {...resetForm.register("confirmPassword")}
                    />
                    {resetForm.formState.errors.confirmPassword && (
                      <p className="text-xs font-medium text-red-500">
                        {resetForm.formState.errors.confirmPassword.message}
                      </p>
                    )}
                  </div>

                  <Button disabled={isLoading}>
                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Reset password
                  </Button>
                </div>
              </form>
            )}
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
