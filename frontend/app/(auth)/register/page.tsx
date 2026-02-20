"use client";

import { useState } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import api from "@/lib/api";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2, CheckCircle2, ArrowRight, AlertCircle } from "lucide-react";

type CodeValidationResponse = {
  valid: boolean;
  code_type: "STUDENT" | "TEACHER" | "RESEARCHER";
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
  firstName: z.string().trim().min(1, "First name is required"),
  lastName: z.string().trim().min(1, "Last name is required"),
  email: z.string().trim().email("Enter a valid email").optional().or(z.literal("")),
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string().min(1, "Confirm password is required"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type CodeForm = z.infer<typeof codeSchema>;
type RegisterForm = z.infer<typeof registerSchema>;
type ApiError = { response?: { data?: unknown } };
const registerFieldNames = new Set<keyof RegisterForm>([
  "firstName",
  "lastName",
  "email",
  "password",
  "confirmPassword",
]);

function RegisterPageContent() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState<"CODE" | "DETAILS">("CODE");
  const [validatedCode, setValidatedCode] = useState<string>("");
  const [codeContext, setCodeContext] = useState<CodeValidationResponse | null>(
    null,
  );
  const [generalError, setGeneralError] = useState<string | null>(null);

  const codeForm = useForm<CodeForm>({ resolver: zodResolver(codeSchema) });
  const detailsForm = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  const handleApiError = (
    error: ApiError,
    form: UseFormReturn<RegisterForm>,
  ) => {
    const errorData = error.response?.data;
    if (
      typeof errorData === "object" &&
      errorData !== null &&
      !Array.isArray(errorData)
    ) {
      let hasFieldError = false;
      Object.entries(errorData as Record<string, unknown>).forEach(
        ([field, messages]) => {
          if (registerFieldNames.has(field as keyof RegisterForm)) {
            const message = Array.isArray(messages)
              ? String(messages[0])
              : String(messages);
            form.setError(field as keyof RegisterForm, {
              type: "manual",
              message,
            });
            hasFieldError = true;
          }
        },
      );
      if (hasFieldError) return;
    }

    if (typeof errorData === "string") {
      setGeneralError(errorData);
      return;
    }
    setGeneralError(errorData?.detail || "An unexpected error occurred.");
  };

  const onValidateCode = async (data: CodeForm) => {
    setIsLoading(true);
    setGeneralError(null);
    try {
      const res = await api.post("/registration/code-validations", {
        code: data.code,
      });
      const responseData = res.data as CodeValidationResponse;
      setValidatedCode(data.code);
      setCodeContext(responseData);
      setStep("DETAILS");
    } catch (error: unknown) {
      const err = error as ApiError;
      const detail = (err.response?.data as { detail?: string } | undefined)
        ?.detail;
      const errorMsg = detail || "Invalid registration code.";
      codeForm.setError("code", { type: "manual", message: errorMsg });
    } finally {
      setIsLoading(false);
    }
  };

  const onRegister = async (data: RegisterForm) => {
    setIsLoading(true);
    setGeneralError(null);
    try {
      const isStudent = codeContext?.code_type === "STUDENT";
      if (!isStudent && !data.email?.trim()) {
        detailsForm.setError("email", {
          type: "manual",
          message: "Email is required for teacher/researcher registration",
        });
        return;
      }

      const payload: Record<string, string> = {
        code: validatedCode,
        firstName: data.firstName.trim(),
        lastName: data.lastName.trim(),
        password: data.password,
        confirmPassword: data.confirmPassword,
      };
      if (!isStudent && data.email?.trim()) {
        payload.email = data.email.trim().toLowerCase();
      }

      const registerRes = await api.post("/registration/accounts", {
        method: "LOCAL",
        ...payload,
      });
      const {
        accessToken,
        role,
        name,
        username: resolvedUsername,
      } = registerRes.data as {
        accessToken?: string;
        role?: string;
        name?: string;
        username?: string;
      };

      if (!resolvedUsername) {
        setGeneralError(
          "Registration succeeded, but no username was returned.",
        );
        return;
      }

      if (!accessToken) {
        setGeneralError("Registration succeeded, but token response was missing.");
        return;
      }
      Cookies.set("access_token", accessToken, { expires: 1 });
      if (role) Cookies.set("user_role", role);
      Cookies.set("user_name", name || "User", { expires: 1 });

      toast.success(`Account created. Username: ${resolvedUsername}`);
      router.push("/dashboard");
    } catch (error: unknown) {
      handleApiError(error as ApiError, detailsForm);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="flex flex-col space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">
          Create an account
        </h1>
        <p className="text-sm text-slate-500">
          {step === "CODE"
            ? "Enter your invitation code to get started"
            : "Complete your registration"}
        </p>
      </div>

      <div className="grid gap-6">
        {step === "CODE" && (
          <form
            onSubmit={codeForm.handleSubmit(onValidateCode)}
            className="space-y-4"
          >
            <div className="grid gap-2">
              <Label htmlFor="code">Registration Code</Label>
              <Input
                id="code"
                placeholder="e.g. AB12CD"
                className={`text-center text-lg tracking-widest uppercase ${codeForm.formState.errors.code ? "border-red-500 focus-visible:ring-red-500" : ""}`}
                maxLength={64}
                disabled={isLoading}
                {...codeForm.register("code")}
              />
              {codeForm.formState.errors.code && (
                <p className="text-xs font-medium text-red-500 flex items-center mt-1">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {codeForm.formState.errors.code.message}
                </p>
              )}
            </div>
            <Button className="w-full" disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="mr-2 h-4 w-4" />
              )}
              Continue
            </Button>
          </form>
        )}

        {step === "DETAILS" && (
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

            <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-900 flex items-start">
              <CheckCircle2 className="mr-2 h-5 w-5 text-blue-600 shrink-0" />
              <div>
                <p className="font-medium">Code Validated</p>
                <p className="text-blue-700 mt-1">
                  You are joining as a <strong>{codeContext?.code_type}</strong>
                  {codeContext?.context?.course_name && (
                    <span>
                      {" "}
                      for <strong>{codeContext.context.course_name}</strong>
                    </span>
                  )}
                  .
                </p>
              </div>
            </div>

            <form onSubmit={detailsForm.handleSubmit(onRegister)}>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    placeholder="Jane"
                    disabled={isLoading}
                    className={
                      detailsForm.formState.errors.firstName
                        ? "border-red-500 focus-visible:ring-red-500"
                        : ""
                    }
                    {...detailsForm.register("firstName")}
                  />
                  {detailsForm.formState.errors.firstName && (
                    <p className="text-xs text-red-500 mt-1">
                      {detailsForm.formState.errors.firstName.message}
                    </p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    placeholder="Doe"
                    disabled={isLoading}
                    className={
                      detailsForm.formState.errors.lastName
                        ? "border-red-500 focus-visible:ring-red-500"
                        : ""
                    }
                    {...detailsForm.register("lastName")}
                  />
                  {detailsForm.formState.errors.lastName && (
                    <p className="text-xs text-red-500 mt-1">
                      {detailsForm.formState.errors.lastName.message}
                    </p>
                  )}
                </div>

                {codeContext?.code_type !== "STUDENT" && (
                  <div className="grid gap-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="name@example.com"
                      disabled={isLoading}
                      className={
                        detailsForm.formState.errors.email
                          ? "border-red-500 focus-visible:ring-red-500"
                          : ""
                      }
                      {...detailsForm.register("email")}
                    />
                    {detailsForm.formState.errors.email && (
                      <p className="text-xs text-red-500 mt-1">
                        {detailsForm.formState.errors.email.message}
                      </p>
                    )}
                  </div>
                )}

                <div className="grid gap-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    disabled={isLoading}
                    className={
                      detailsForm.formState.errors.password
                        ? "border-red-500 focus-visible:ring-red-500"
                        : ""
                    }
                    {...detailsForm.register("password")}
                  />
                  {detailsForm.formState.errors.password && (
                    <p className="text-xs text-red-500 mt-1">
                      {detailsForm.formState.errors.password.message}
                    </p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="confirmPassword">Confirm Password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    disabled={isLoading}
                    className={
                      detailsForm.formState.errors.confirmPassword
                        ? "border-red-500 focus-visible:ring-red-500"
                        : ""
                    }
                    {...detailsForm.register("confirmPassword")}
                  />
                  {detailsForm.formState.errors.confirmPassword && (
                    <p className="text-xs text-red-500 mt-1">
                      {detailsForm.formState.errors.confirmPassword.message}
                    </p>
                  )}
                </div>

                <Button disabled={isLoading}>
                  {isLoading && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Complete Registration
                </Button>
              </div>
            </form>
          </>
        )}
      </div>

      <p className="px-8 text-center text-sm text-slate-500">
        <Link
          href="/login"
          className="hover:text-brand underline underline-offset-4"
        >
          Already have an account? Sign In
        </Link>
      </p>
    </>
  );
}

export default function RegisterPage() {
  return <RegisterPageContent />;
}
