'use client';

import type { RegistrationCodeType } from '@/lib/registration-code-api';
import { cn } from '@/lib/utils';

function labelForCodeType(codeType: RegistrationCodeType): string {
  if (codeType === 'STUDENT') return 'Student';
  if (codeType === 'TEACHER') return 'Teacher';
  return 'Researcher';
}

type CodeTypeTabsProps = {
  tabs: RegistrationCodeType[];
  activeTab: RegistrationCodeType;
  onTabChange: (tab: RegistrationCodeType) => void;
};

export function CodeTypeTabs({ tabs, activeTab, onTabChange }: CodeTypeTabsProps) {
  return (
    <div className="flex gap-0 border-b border-border">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onTabChange(tab)}
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors -mb-px',
            tab === activeTab
              ? 'border-b-2 border-primary text-primary'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {labelForCodeType(tab)}
        </button>
      ))}
    </div>
  );
}
