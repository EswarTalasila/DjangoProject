// Runtime base-path detection for imperative navigation (window.location.href,
// API redirect targets, etc.) called from lib modules that don't have access
// to Next's useRouter hook.
//
// Next's router auto-prefixes basePath on router.push/replace — use those when
// possible. Only fall back to this when assigning window.location directly.

const BASE_PATHS = ["/_dev", "/_test"] as const;

export function detectBasePath(): string {
  if (typeof window === "undefined") return "";
  const pathname = window.location.pathname;
  for (const prefix of BASE_PATHS) {
    if (pathname === prefix || pathname.startsWith(`${prefix}/`)) {
      return prefix;
    }
  }
  return "";
}

export function withBasePath(path: string): string {
  const prefix = detectBasePath();
  if (!prefix) return path;
  if (path.startsWith(prefix)) return path;
  return `${prefix}${path}`;
}
