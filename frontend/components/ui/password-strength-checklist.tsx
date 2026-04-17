'use client';

import { Check, X } from 'lucide-react';

const RULES = [
  { label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
  { label: 'At least one uppercase letter', test: (p: string) => /[A-Z]/.test(p) },
  { label: 'At least one lowercase letter', test: (p: string) => /[a-z]/.test(p) },
  { label: 'At least one number', test: (p: string) => /[0-9]/.test(p) },
  { label: 'At least one special character', test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

export function PasswordStrengthChecklist({ password }: { password: string }) {
  if (!password) return null;
  return (
    <ul className="space-y-1 text-xs">
      {RULES.map((rule) => {
        const passed = rule.test(password);
        return (
          <li key={rule.label} className={`flex items-center gap-1.5 ${passed ? 'text-green-600' : 'text-red-500'}`}>
            {passed ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
            {rule.label}
          </li>
        );
      })}
    </ul>
  );
}
