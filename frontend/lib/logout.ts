import Cookies from "js-cookie";
import api from "@/lib/api";
import { withBasePath } from "@/lib/base-path";

export async function logout(): Promise<void> {
  try {
    await api.post("/auth/session-revocations", {});
  } catch {
    // Continue logout UX even if backend session revocation fails.
  } finally {
    Cookies.remove("user_name");
    window.location.href = withBasePath("/login");
  }
}
