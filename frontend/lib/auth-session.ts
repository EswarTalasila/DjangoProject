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

const VALID_ROLES = ["ADMIN", "TEACHER", "RESEARCHER", "STUDENT"] as const;

const EMPTY_SUDO_CAPABILITIES: SudoCapabilities = {
  hasSudo: false,
  canGrantSudo: false,
  permissions: [],
  isStaff: false,
};

/** Resolve the API base URL for server-side fetches.
 *  Priority: SERVER_PROXY_ORIGIN + NEXT_PUBLIC_API_URL > NEXT_PUBLIC_API_URL.
 *  Browser code uses same-origin "/api/v1" through nginx. Server-side fetches
 *  need an absolute URL, so local fallback points at the proxy entrypoint. */
function resolveApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
  const normalizedConfigured = configured.replace(/\/$/, "");
  let configuredPath = normalizedConfigured;

  try {
    const url = new URL(normalizedConfigured);
    configuredPath = url.pathname.replace(/\/$/, "") || "/api/v1";
  } catch {
    if (!configuredPath.startsWith("/")) {
      configuredPath = `/${configuredPath}`;
    }
  }

  // Prefer an explicit proxy origin so SSR traverses the same proxy layer as browser traffic.
  if (process.env.SERVER_PROXY_ORIGIN) {
    return `${process.env.SERVER_PROXY_ORIGIN.replace(/\/$/, "")}${configuredPath}`;
  }

  try {
    const url = new URL(normalizedConfigured);
    return url.toString().replace(/\/$/, "");
  } catch {
    // configured is a relative path (e.g. "/api/v1") — unusable for server-side fetch
    // without a proxy origin. Fall back to the local proxy listener.
    return `http://localhost:8080${normalizedConfigured}`;
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

/** GET /api/v1/sudo-grants/me — Fetch the current user's sudo capabilities (cached per render pass). */
export const getSudoCapabilities = cache(async (): Promise<SudoCapabilities | null> => {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  if (!accessToken) return null;

  let response: Response;
  try {
    response = await fetch(`${resolveApiBaseUrl()}/sudo-grants/me`, {
      method: "GET",
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: 'no-store',
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
