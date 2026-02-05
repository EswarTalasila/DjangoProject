import type { Config } from "tailwindcss"

const config = {
  darkMode: ["class"],
  // CRITICAL FIX: Ensure these paths point to 'app' and 'components' at the root
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}', // Keep this just in case
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      // ... keep your existing Shadcn colors/animations here
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config

export default config