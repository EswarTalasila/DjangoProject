'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { HelpTip } from '@/components/ui/help-tip';

type ExportCardProps = {
  icon: React.ReactNode;
  title: string;
  description: string;
  helpText: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
};

export function ExportCard({
  icon,
  title,
  description,
  helpText,
  defaultOpen = false,
  children,
}: ExportCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent/30 transition-colors"
          >
            <span className="text-muted-foreground">{icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1">
                <span className="font-medium text-sm text-foreground">{title}</span>
                <HelpTip text={helpText} />
              </div>
              <p className="text-xs text-muted-foreground truncate">{description}</p>
            </div>
            <ChevronDown
              className={cn(
                'size-4 text-muted-foreground transition-transform',
                open && 'rotate-180',
              )}
            />
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="border-t border-border px-4 py-4">
            {children}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}
