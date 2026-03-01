import { cookies } from "next/headers";
import { cache } from "react";

export type SessionProfile = {
  id: string;
  name: string;
  username: string;
  email: string | null;
  role: string;
  isStaff: boolean;
};

export type SudoCapabilities = {
  hasSudo: boolean;
  canGrantSudo: boolean;
  permissions: string[];
  isStaff: boolean;
};

const VALID_ROLES = ["TEACHER", "RESEARCHER", "STUDENT"] as const;

const EMPTY_SUDO_CAPABILITIES: SudoCapabilities = {
  hasSudo: false,
  canGrantSudo: false,
  permissions: [],
  isStaff: false,
};

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

// React cache() deduplicates calls within the same server render pass.
// The dashboard layout and SidebarWrapper both call getSessionProfile(),
// so without this they'd fire two separate /auth/me requests per navigation.
export const getSessionProfile = cache(async (): Promise<SessionProfile | null> => {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  if (!accessToken) return null;

  let response: Response;
  try {
    response = await fetch(`${resolveApiBaseUrl()}/auth/me`, {
      method: "GET",
      headers: { Authorization: `Bearer ${accessToken}` },
      next: { revalidate: 30 },
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
});

export const getSudoCapabilities = cache(async (): Promise<SudoCapabilities | null> => {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  if (!accessToken) return null;

  let response: Response;
  try {
    response = await fetch(`${resolveApiBaseUrl()}/sudo-grants/me`, {
      method: "GET",
      headers: { Authorization: `Bearer ${accessToken}` },
      next: { revalidate: 30 },
    });
  } catch {
    return EMPTY_SUDO_CAPABILITIES;
  }

  if (!response.ok) return EMPTY_SUDO_CAPABILITIES;

  const data = (await response.json()) as Partial<SudoCapabilities>;
  return {
    hasSudo: Boolean(data.hasSudo),
    canGrantSudo: Boolean(data.canGrantSudo),
    permissions: Array.isArray(data.permissions) ? data.permissions : [],
    isStaff: Boolean(data.isStaff),
  };
});
