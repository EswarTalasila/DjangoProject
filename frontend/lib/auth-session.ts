import { cookies } from "next/headers";

export type SessionProfile = {
  id: string;
  name: string;
  username: string;
  email: string | null;
  role: string;
  isStaff: boolean;
};

const VALID_ROLES = ["TEACHER", "RESEARCHER", "STUDENT"] as const;

function resolveApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  try {
    const url = new URL(configured);
    if (
      (url.hostname === "localhost" || url.hostname === "127.0.0.1") &&
      process.env.PROXY_TARGET
    ) {
      const proxyTarget = process.env.PROXY_TARGET.replace(/\/$/, "");
      return `${proxyTarget}/api/v1`;
    }
    return url.toString().replace(/\/$/, "");
  } catch {
    return configured.replace(/\/$/, "");
  }
}

export async function getSessionProfile(): Promise<SessionProfile | null> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  if (!accessToken) return null;

  let response: Response;
  try {
    response = await fetch(`${resolveApiBaseUrl()}/auth/me`, {
      method: "GET",
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
  } catch {
    return null;
  }

  if (!response.ok) return null;

  const profile = (await response.json()) as SessionProfile;
  if (!profile.role || !VALID_ROLES.includes(profile.role as (typeof VALID_ROLES)[number])) {
    return null;
  }

  return profile;
}
