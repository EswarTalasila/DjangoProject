import { Sparkles } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen w-full lg:grid lg:grid-cols-[1.1fr_1fr]">
      {/* LEFT: Branding panel — animated purple gradient mesh */}
      <div className="relative hidden overflow-hidden lg:flex lg:flex-col lg:justify-between p-12 text-white">
        <div className="absolute inset-0 bg-gradient-to-br from-violet-600 via-purple-700 to-indigo-900" />

        {/* Drifting blobs */}
        <div
          aria-hidden
          className="absolute -left-32 top-10 h-[28rem] w-[28rem] rounded-full bg-violet-400/40 blur-3xl animate-blob-drift"
        />
        <div
          aria-hidden
          className="absolute -right-24 bottom-10 h-[26rem] w-[26rem] rounded-full bg-indigo-500/40 blur-3xl animate-blob-drift-slow"
        />
        <div
          aria-hidden
          className="absolute left-1/3 bottom-1/4 h-[18rem] w-[18rem] rounded-full bg-fuchsia-400/25 blur-3xl animate-blob-drift"
          style={{ animationDelay: "-12s" }}
        />

        <div className="relative z-10 flex items-center gap-3 animate-fade-up">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/15 backdrop-blur transition-transform duration-500 hover:scale-110 hover:rotate-12">
            <Sparkles className="h-5 w-5" />
          </div>
          <span className="text-xs font-semibold tracking-[0.3em] text-white/80">
            PRISM
          </span>
        </div>

        <div className="relative z-10 space-y-5">
          <h1 className="text-7xl font-bold leading-[0.95] tracking-tight xl:text-8xl animate-fade-up-delay-1">
            Prism
          </h1>
          <p className="max-w-md text-lg leading-relaxed text-white/85 animate-fade-up-delay-2">
            An educational assessment platform connecting researchers, teachers, and students through a single shared lens.
          </p>
        </div>

        <div className="relative z-10 text-sm text-white/60 animate-fade-up-delay-3">
          A platform for learning, designed for clarity.
        </div>
      </div>

      {/* RIGHT: Form panel */}
      <div className="flex items-center justify-center bg-white p-8 lg:p-12">
        <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[380px] animate-fade-up">
          {children}
        </div>
      </div>
    </div>
  );
}
