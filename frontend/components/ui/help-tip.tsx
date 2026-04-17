'use client';

import { CircleHelp } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export function HelpTip({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          role="button"
          className="ml-1 inline-flex items-center text-muted-foreground hover:text-foreground"
          aria-label="Show help"
        >
          <CircleHelp className="h-3.5 w-3.5" />
        </span>
      </TooltipTrigger>
      <TooltipContent sideOffset={6} className="max-w-xs whitespace-pre-line">
        {text}
      </TooltipContent>
    </Tooltip>
  );
}
