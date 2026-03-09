import { MonitorSmartphone } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen w-full lg:grid lg:grid-cols-2">
      {/* LEFT SIDE: Branding & Visuals (Hidden on mobile) */}
      <div className="hidden bg-[#2a8a42] lg:flex flex-col justify-between p-10 text-white">
        
        {/* Logo Area */}
        <div className="flex items-center gap-2 text-lg font-bold">
          <MonitorSmartphone className="h-6 w-6" />
          <span>EE Lab Dashboard</span>
        </div>
      </div>

      {/* RIGHT SIDE: The Login Form */}
      <div className="flex items-center justify-center bg-white p-8 lg:p-12">
        <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
          {children}
        </div>
      </div>
    </div>
  );
}
