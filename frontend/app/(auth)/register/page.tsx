"use client";

import { useState } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import api from "@/lib/api";
import type { ApiError } from "@/lib/api-error";
import { isApiErrorRecord } from "@/lib/api-error";
import { toErrorMessage } from "@/lib/utils";
import { toast } from "sonner";
import { GoogleOAuthProvider, useGoogleLogin } from "@react-oauth/google";


import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2, CheckCircle2, ArrowRight, AlertCircle, User, Mail, Lock, GraduationCap, Building2 } from "lucide-react";
import { PasswordStrengthChecklist } from "@/components/ui/password-strength-checklist";

type RoleType = "STUDENT" | "TEACHER" | "RESEARCHER";
type RegistrationMethod = "LOCAL" | "OAUTH";

type CodeValidationResponse = {
    valid: boolean;
    code_type: RoleType;
    context: {
        course_name?: string;
        teacher_name?: string;
        school?: string;
    };
};

type RegisterResponse = {
    message: string;
    username: string;
    name: string;
    email: string | null;
    role: RoleType;
    id: string;
    courseId: number | null;
    createdNewUser: boolean;
    alreadyEnrolled: boolean;
};

const codeSchema = z.object({
    code: z.string().min(1, "Registration code is required").max(64),
});

const passwordSchema = z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Must include at least one uppercase letter")
    .regex(/[a-z]/, "Must include at least one lowercase letter")
    .regex(/[0-9]/, "Must include at least one number")
    .regex(/[^A-Za-z0-9]/, "Must include at least one special character");

const studentRegisterSchema = z
    .object({
        firstName: z.string().trim().min(1, "First name is required").regex(/^[A-Za-z]+$/, "Letters only"),
        lastName: z.string().trim().min(1, "Last name is required").regex(/^[A-Za-z]+$/, "Letters only"),
        password: passwordSchema,
        confirmPassword: z.string().min(1, "Confirm password is required"),
    })
    .refine((data) => data.password === data.confirmPassword, {
        message: "Passwords do not match",
        path: ["confirmPassword"],
    });

const nonStudentLocalSchema = z
    .object({
        firstName: z.string().trim().min(1, "First name is required").regex(/^[A-Za-z]+$/, "Letters only"),
        lastName: z.string().trim().min(1, "Last name is required").regex(/^[A-Za-z]+$/, "Letters only"),
        email: z.string().email("Invalid email address"),
        password: passwordSchema,
        confirmPassword: z.string().min(1, "Confirm password is required"),
    })
    .refine((data) => data.password === data.confirmPassword, {
        message: "Passwords do not match",
        path: ["confirmPassword"],
    });

const oauthNameSchema = z.object({
    firstName: z.string().trim().min(1, "First name is required").regex(/^[A-Za-z]+$/, "Letters only"),
    lastName: z.string().trim().min(1, "Last name is required").regex(/^[A-Za-z]+$/, "Letters only"),
});

type CodeForm = z.infer<typeof codeSchema>;
type StudentRegisterForm = z.infer<typeof studentRegisterSchema>;
type NonStudentLocalForm = z.infer<typeof nonStudentLocalSchema>;
type OAuthNameForm = z.infer<typeof oauthNameSchema>;

function RegisterPageContent() {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [step, setStep] = useState<"CODE" | "DETAILS">("CODE");
    const [validatedCode, setValidatedCode] = useState<string>("");
    const [codeContext, setCodeContext] = useState<CodeValidationResponse | null>(null);
    const [generalError, setGeneralError] = useState<string | null>(null);
    const [registrationMethod, setRegistrationMethod] = useState<RegistrationMethod>("LOCAL");
    const [showOauthForm, setShowOauthForm] = useState(false);
    const [googleAccessToken, setGoogleAccessToken] = useState<string>("");
    const [createdUsername, setCreatedUsername] = useState<string | null>(null);

    const codeForm = useForm<CodeForm>({ resolver: zodResolver(codeSchema) });
    const studentForm = useForm<StudentRegisterForm>({
        resolver: zodResolver(studentRegisterSchema),
        defaultValues: { firstName: "", lastName: "", password: "", confirmPassword: "" },
    });
    const nonStudentForm = useForm<NonStudentLocalForm>({
        resolver: zodResolver(nonStudentLocalSchema),
        defaultValues: { firstName: "", lastName: "", email: "", password: "", confirmPassword: "" },
    });
    const oauthForm = useForm<OAuthNameForm>({
        resolver: zodResolver(oauthNameSchema),
        defaultValues: { firstName: "", lastName: "" },
    });

    const role = codeContext?.code_type;
    const isStudent = role === "STUDENT";

    const handleApiError = (
        error: ApiError,
        form: UseFormReturn<StudentRegisterForm> | UseFormReturn<NonStudentLocalForm> | UseFormReturn<OAuthNameForm>
    ) => {
        const errorData = error.response?.data;
        if (isApiErrorRecord(errorData)) {
            if (Array.isArray(errorData.errors)) {
                const passwordErrors = errorData.errors;
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (form as UseFormReturn<any>).setError("password", { type: "manual", message: passwordErrors.join(" ") });
                return;
            }

            let hasFieldError = false;
            const validFields = isStudent
                ? new Set<string>(["firstName", "lastName", "password", "confirmPassword"])
                : showOauthForm
                    ? new Set<string>(["firstName", "lastName"])
                    : new Set<string>(["firstName", "lastName", "email", "password", "confirmPassword"]);

            Object.entries(errorData).forEach(([field, messages]) => {
                if (validFields.has(field)) {
                    const message = Array.isArray(messages) ? String(messages[0]) : String(messages);
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    form.setError(field as any, { type: "manual", message });
                    hasFieldError = true;
                }
            });
            if (hasFieldError) return;
        }

        setGeneralError(toErrorMessage(error, "An unexpected error occurred."));
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
            const errorMsg = toErrorMessage(error, "Invalid registration code.");
            codeForm.setError("code", { type: "manual", message: errorMsg });
        } finally {
            setIsLoading(false);
        }
    };

    const handleStudentRegistration = async (data: StudentRegisterForm) => {
        setIsLoading(true);
        setGeneralError(null);
        try {
            const payload = {
                method: "LOCAL",
                code: validatedCode,
                firstName: data.firstName.trim(),
                lastName: data.lastName.trim(),
                password: data.password,
                confirmPassword: data.confirmPassword,
            };

            const res = await api.post("/registration/accounts", payload);
            const responseData = res.data as RegisterResponse;

            const { name } = responseData;
            Cookies.set("user_name", name || "User", { expires: 1 });

            setCreatedUsername(responseData.username);
        } catch (error: unknown) {
            handleApiError(error as ApiError, studentForm);
        } finally {
            setIsLoading(false);
        }
    };

    const handleNonStudentLocalRegistration = async (data: NonStudentLocalForm) => {
        setIsLoading(true);
        setGeneralError(null);
        try {
            const payload = {
                method: "LOCAL",
                code: validatedCode,
                firstName: data.firstName.trim(),
                lastName: data.lastName.trim(),
                email: data.email,
                password: data.password,
                confirmPassword: data.confirmPassword,
            };

            const res = await api.post("/registration/accounts", payload);
            const responseData = res.data as RegisterResponse;

            const { name } = responseData;
            Cookies.set("user_name", name || "User", { expires: 1 });

            toast.success("Account created successfully!");
            router.push("/dashboard");
        } catch (error: unknown) {
            handleApiError(error as ApiError, nonStudentForm);
        } finally {
            setIsLoading(false);
        }
    };

    const registerWithGoogle = useGoogleLogin({
        onSuccess: async (tokenResponse) => {
            setGoogleAccessToken(tokenResponse.access_token);
            setShowOauthForm(true);
            setGeneralError(null);
        },
        onError: () => {
            setGeneralError("Google registration failed to initialize.");
        },
    });

    const handleOAuthRegistration = async (data: OAuthNameForm) => {
        setIsLoading(true);
        setGeneralError(null);
        try {
            const payload = {
                method: "OAUTH",
                code: validatedCode,
                accessToken: googleAccessToken,
                firstName: data.firstName.trim(),
                lastName: data.lastName.trim(),
            };

            const res = await api.post("/registration/accounts", payload);
            const responseData = res.data as RegisterResponse;

            const { name } = responseData;
            Cookies.set("user_name", name || "User", { expires: 1 });

            toast.success("Account created with Google!");
            router.push("/dashboard");
        } catch (error: unknown) {
            handleApiError(error as ApiError, oauthForm);
        } finally {
            setIsLoading(false);
        }
    };

    const getRoleIcon = () => {
        switch (role) {
            case "STUDENT":
                return <GraduationCap className="h-5 w-5" />;
            case "TEACHER":
                return <User className="h-5 w-5" />;
            case "RESEARCHER":
                return <Building2 className="h-5 w-5" />;
            default:
                return null;
        }
    };

    const getRoleTitle = () => {
        switch (role) {
            case "STUDENT":
                return "Student Registration";
            case "TEACHER":
                return "Teacher Registration";
            case "RESEARCHER":
                return "Researcher Registration";
            default:
                return "Complete Registration";
        }
    };

    if (createdUsername) {
        return (
            <>
                <div className="flex flex-col space-y-2 text-center">
                    <CheckCircle2 className="mx-auto h-12 w-12 text-green-600" />
                    <h1 className="text-2xl font-semibold tracking-tight">
                        Account Created
                    </h1>
                    <p className="text-sm text-slate-500">
                        Your account has been created successfully.
                    </p>
                </div>

                <div className="rounded-md border-2 border-blue-200 bg-blue-50 p-6 text-center">
                    <p className="text-sm font-medium text-blue-900 mb-2">Your username is:</p>
                    <p className="text-2xl font-bold text-blue-700 font-mono tracking-wide">{createdUsername}</p>
                </div>

                <div className="rounded-md bg-amber-50 border border-amber-200 p-4">
                    <p className="text-sm text-amber-900 font-medium flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
                        Important: Save your username
                    </p>
                    <p className="text-sm text-amber-800 mt-1 ml-6">
                        You will need this username to log in. Please write it down or take a screenshot.
                    </p>
                </div>

                <Button className="w-full" onClick={() => router.push("/dashboard")}>
                    Continue to Dashboard
                    <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
            </>
        );
    }

    return (
        <>
            <div className="flex flex-col space-y-2 text-center">
                <h1 className="text-2xl font-semibold tracking-tight">
                    Create an account
                </h1>
                <p className="text-sm text-slate-500">
                    {step === "CODE"
                        ? "Enter your invitation code to get started"
                        : getRoleTitle()}
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
                                <p className="font-medium flex items-center gap-2">
                                    {getRoleIcon()}
                                    Code Validated
                                </p>
                                <p className="text-blue-700 mt-1">
                                    You are registering as a <strong>{role}</strong>
                                    {codeContext?.context?.course_name && (
                                        <span>
                                            {" "}for <strong>{codeContext.context.course_name}</strong>
                                        </span>
                                    )}
                                    {codeContext?.context?.teacher_name && (
                                        <span>
                                            {" "}with {codeContext.context.teacher_name}
                                        </span>
                                    )}
                                    .
                                </p>
                            </div>
                        </div>

                        {!isStudent && (
                            <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-lg">
                                <Button
                                    type="button"
                                    variant={registrationMethod === "LOCAL" ? "default" : "ghost"}
                                    size="sm"
                                    onClick={() => setRegistrationMethod("LOCAL")}
                                    className="w-full"
                                >
                                    <Lock className="mr-2 h-4 w-4" />
                                    Local
                                </Button>
                                <Button
                                    type="button"
                                    variant={registrationMethod === "OAUTH" ? "default" : "ghost"}
                                    size="sm"
                                    onClick={() => setRegistrationMethod("OAUTH")}
                                    className="w-full"
                                >
                                    <Mail className="mr-2 h-4 w-4" />
                                    Google
                                </Button>
                            </div>
                        )}

                        {isStudent ? (
                            <form method="post" onSubmit={studentForm.handleSubmit(handleStudentRegistration)}>
                                <div className="grid gap-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="grid gap-2">
                                            <Label htmlFor="firstName">First Name</Label>
                                            <Input
                                                id="firstName"
                                                placeholder="Jane"
                                                disabled={isLoading}
                                                className={
                                                    studentForm.formState.errors.firstName
                                                        ? "border-red-500 focus-visible:ring-red-500"
                                                        : ""
                                                }
                                                {...studentForm.register("firstName")}
                                            />
                                            {studentForm.formState.errors.firstName && (
                                                <p className="text-xs text-red-500 mt-1">
                                                    {studentForm.formState.errors.firstName.message}
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
                                                    studentForm.formState.errors.lastName
                                                        ? "border-red-500 focus-visible:ring-red-500"
                                                        : ""
                                                }
                                                {...studentForm.register("lastName")}
                                            />
                                            {studentForm.formState.errors.lastName && (
                                                <p className="text-xs text-red-500 mt-1">
                                                    {studentForm.formState.errors.lastName.message}
                                                </p>
                                            )}
                                        </div>
                                    </div>

                                    <div className="grid gap-2">
                                        <Label htmlFor="password">Password</Label>
                                        <Input
                                            id="password"
                                            type="password"
                                            disabled={isLoading}
                                            className={
                                                studentForm.formState.errors.password
                                                    ? "border-red-500 focus-visible:ring-red-500"
                                                    : ""
                                            }
                                            {...studentForm.register("password")}
                                        />
                                        {studentForm.formState.errors.password && (
                                            <p className="text-xs text-red-500 mt-1">
                                                {studentForm.formState.errors.password.message}
                                            </p>
                                        )}
                                        <PasswordStrengthChecklist password={studentForm.watch("password") || ""} />
                                    </div>

                                    <div className="grid gap-2">
                                        <Label htmlFor="confirmPassword">Confirm Password</Label>
                                        <Input
                                            id="confirmPassword"
                                            type="password"
                                            disabled={isLoading}
                                            className={
                                                studentForm.formState.errors.confirmPassword
                                                    ? "border-red-500 focus-visible:ring-red-500"
                                                    : ""
                                            }
                                            {...studentForm.register("confirmPassword")}
                                        />
                                        {studentForm.formState.errors.confirmPassword && (
                                            <p className="text-xs text-red-500 mt-1">
                                                {studentForm.formState.errors.confirmPassword.message}
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
                        ) : registrationMethod === "LOCAL" ? (
                            <form method="post" onSubmit={nonStudentForm.handleSubmit(handleNonStudentLocalRegistration)}>
                                <div className="grid gap-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="grid gap-2">
                                            <Label htmlFor="firstName">First Name</Label>
                                            <Input
                                                id="firstName"
                                                placeholder="Jane"
                                                disabled={isLoading}
                                                className={
                                                    nonStudentForm.formState.errors.firstName
                                                        ? "border-red-500 focus-visible:ring-red-500"
                                                        : ""
                                                }
                                                {...nonStudentForm.register("firstName")}
                                            />
                                            {nonStudentForm.formState.errors.firstName && (
                                                <p className="text-xs text-red-500 mt-1">
                                                    {nonStudentForm.formState.errors.firstName.message}
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
                                                    nonStudentForm.formState.errors.lastName
                                                        ? "border-red-500 focus-visible:ring-red-500"
                                                        : ""
                                                }
                                                {...nonStudentForm.register("lastName")}
                                            />
                                            {nonStudentForm.formState.errors.lastName && (
                                                <p className="text-xs text-red-500 mt-1">
                                                    {nonStudentForm.formState.errors.lastName.message}
                                                </p>
                                            )}
                                        </div>
                                    </div>

                                    <div className="grid gap-2">
                                        <Label htmlFor="email">Email</Label>
                                        <Input
                                            id="email"
                                            type="email"
                                            placeholder="jane@example.com"
                                            disabled={isLoading}
                                            className={
                                                nonStudentForm.formState.errors.email
                                                    ? "border-red-500 focus-visible:ring-red-500"
                                                    : ""
                                            }
                                            {...nonStudentForm.register("email")}
                                        />
                                        {nonStudentForm.formState.errors.email && (
                                            <p className="text-xs text-red-500 mt-1">
                                                {nonStudentForm.formState.errors.email.message}
                                            </p>
                                        )}
                                    </div>

                                    <div className="grid gap-2">
                                        <Label htmlFor="password">Password</Label>
                                        <Input
                                            id="password"
                                            type="password"
                                            disabled={isLoading}
                                            className={
                                                nonStudentForm.formState.errors.password
                                                    ? "border-red-500 focus-visible:ring-red-500"
                                                    : ""
                                            }
                                            {...nonStudentForm.register("password")}
                                        />
                                        {nonStudentForm.formState.errors.password && (
                                            <p className="text-xs text-red-500 mt-1">
                                                {nonStudentForm.formState.errors.password.message}
                                            </p>
                                        )}
                                        <PasswordStrengthChecklist password={nonStudentForm.watch("password") || ""} />
                                    </div>

                                    <div className="grid gap-2">
                                        <Label htmlFor="confirmPassword">Confirm Password</Label>
                                        <Input
                                            id="confirmPassword"
                                            type="password"
                                            disabled={isLoading}
                                            className={
                                                nonStudentForm.formState.errors.confirmPassword
                                                    ? "border-red-500 focus-visible:ring-red-500"
                                                    : ""
                                            }
                                            {...nonStudentForm.register("confirmPassword")}
                                        />
                                        {nonStudentForm.formState.errors.confirmPassword && (
                                            <p className="text-xs text-red-500 mt-1">
                                                {nonStudentForm.formState.errors.confirmPassword.message}
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
                        ) : showOauthForm ? (
                            <form method="post" onSubmit={oauthForm.handleSubmit(handleOAuthRegistration)}>
                                <div className="grid gap-4">
                                    <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-900 flex items-start">
                                        <Mail className="mr-2 h-5 w-5 text-blue-600 shrink-0" />
                                        <p className="text-blue-700">
                                            Google authenticated. Enter your name to complete registration.
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="grid gap-2">
                                            <Label htmlFor="oauth-firstName">First Name</Label>
                                            <Input
                                                id="oauth-firstName"
                                                placeholder="Jane"
                                                disabled={isLoading}
                                                className={
                                                    oauthForm.formState.errors.firstName
                                                        ? "border-red-500 focus-visible:ring-red-500"
                                                        : ""
                                                }
                                                {...oauthForm.register("firstName")}
                                            />
                                            {oauthForm.formState.errors.firstName && (
                                                <p className="text-xs text-red-500 mt-1">
                                                    {oauthForm.formState.errors.firstName.message}
                                                </p>
                                            )}
                                        </div>

                                        <div className="grid gap-2">
                                            <Label htmlFor="oauth-lastName">Last Name</Label>
                                            <Input
                                                id="oauth-lastName"
                                                placeholder="Doe"
                                                disabled={isLoading}
                                                className={
                                                    oauthForm.formState.errors.lastName
                                                        ? "border-red-500 focus-visible:ring-red-500"
                                                        : ""
                                                }
                                                {...oauthForm.register("lastName")}
                                            />
                                            {oauthForm.formState.errors.lastName && (
                                                <p className="text-xs text-red-500 mt-1">
                                                    {oauthForm.formState.errors.lastName.message}
                                                </p>
                                            )}
                                        </div>
                                    </div>

                                    <Button disabled={isLoading}>
                                        {isLoading && (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        )}
                                        Complete Registration
                                    </Button>
                                </div>
                            </form>
                        ) : (
                            <div className="text-center py-8">
                                <div className="bg-white border-2 border-slate-200 rounded-lg p-6 mb-4">
                                    <Mail className="mx-auto h-12 w-12 text-slate-400 mb-4" />
                                    <h3 className="text-lg font-semibold mb-2">Register with Google</h3>
                                    <p className="text-sm text-slate-600 mb-4">
                                        Click below to authenticate with Google, then complete your registration
                                    </p>

                                    <Button
                                        onClick={() => registerWithGoogle()}
                                        disabled={isLoading}
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
                                </div>
                            </div>
                        )}
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
    return (
        <GoogleOAuthProvider
      clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ""}
    >
        <RegisterPageContent />
        </GoogleOAuthProvider>
    )
}
