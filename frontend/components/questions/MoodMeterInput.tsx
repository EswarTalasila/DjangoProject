"use client";

import { useState } from "react";

type QuadrantKey =
  | "highEnergyLowPleasantness"
  | "highEnergyHighPleasantness"
  | "lowEnergyLowPleasantness"
  | "lowEnergyHighPleasantness";

export type MoodSelection = {
  quadrant: string;
  moodName: string;
  row: number;
  col: number;
};

type MoodCell = {
  name: string;
  row: number;
  col: number;
  quadrant: QuadrantKey;
};

const MOOD_EMOJI: Record<string, string> = {
  Angry: '😠',
  Frustrated: '😤',
  Anxious: '😰',
  Irritated: '😒',
  Stressed: '😖',
  Excited: '🤩',
  Energized: '⚡',
  Motivated: '💪',
  Proud: '😊',
  Joyful: '😄',
  Sad: '😢',
  Tired: '😴',
  Bored: '😐',
  Lonely: '😔',
  Down: '☹️',
  Calm: '😌',
  Relaxed: '🙂',
  Content: '😌',
  Grateful: '🙏',
  Peaceful: '🕊️',
};

const MOODS_BY_QUADRANT: Record<QuadrantKey, MoodCell[]> = {
  highEnergyLowPleasantness: [
    { name: "Angry", row: 0, col: 0, quadrant: "highEnergyLowPleasantness" },
    { name: "Frustrated", row: 1, col: 2, quadrant: "highEnergyLowPleasantness" },
    { name: "Anxious", row: 2, col: 4, quadrant: "highEnergyLowPleasantness" },
    { name: "Irritated", row: 3, col: 1, quadrant: "highEnergyLowPleasantness" },
    { name: "Stressed", row: 4, col: 3, quadrant: "highEnergyLowPleasantness" },
  ],
  highEnergyHighPleasantness: [
    { name: "Excited", row: 0, col: 5, quadrant: "highEnergyHighPleasantness" },
    { name: "Energized", row: 1, col: 7, quadrant: "highEnergyHighPleasantness" },
    { name: "Motivated", row: 2, col: 9, quadrant: "highEnergyHighPleasantness" },
    { name: "Proud", row: 3, col: 6, quadrant: "highEnergyHighPleasantness" },
    { name: "Joyful", row: 4, col: 8, quadrant: "highEnergyHighPleasantness" },
  ],
  lowEnergyLowPleasantness: [
    { name: "Sad", row: 5, col: 0, quadrant: "lowEnergyLowPleasantness" },
    { name: "Tired", row: 6, col: 2, quadrant: "lowEnergyLowPleasantness" },
    { name: "Bored", row: 7, col: 4, quadrant: "lowEnergyLowPleasantness" },
    { name: "Lonely", row: 8, col: 1, quadrant: "lowEnergyLowPleasantness" },
    { name: "Down", row: 9, col: 3, quadrant: "lowEnergyLowPleasantness" },
  ],
  lowEnergyHighPleasantness: [
    { name: "Calm", row: 5, col: 5, quadrant: "lowEnergyHighPleasantness" },
    { name: "Relaxed", row: 6, col: 7, quadrant: "lowEnergyHighPleasantness" },
    { name: "Content", row: 7, col: 9, quadrant: "lowEnergyHighPleasantness" },
    { name: "Grateful", row: 8, col: 6, quadrant: "lowEnergyHighPleasantness" },
    { name: "Peaceful", row: 9, col: 8, quadrant: "lowEnergyHighPleasantness" },
  ],
};

const QUADRANT_CONFIG: {
  key: QuadrantKey;
  title: string;
  bgClass: string;
  textClass: string;
}[] = [
  {
    key: "highEnergyLowPleasantness",
    title: "High Energy · Low Pleasantness",
    bgClass: "bg-red-100 dark:bg-red-950/40",
    textClass: "text-red-900 dark:text-red-200",
  },
  {
    key: "highEnergyHighPleasantness",
    title: "High Energy · High Pleasantness",
    bgClass: "bg-yellow-100 dark:bg-yellow-950/40",
    textClass: "text-yellow-900 dark:text-yellow-200",
  },
  {
    key: "lowEnergyLowPleasantness",
    title: "Low Energy · Low Pleasantness",
    bgClass: "bg-blue-100 dark:bg-blue-950/40",
    textClass: "text-blue-900 dark:text-blue-200",
  },
  {
    key: "lowEnergyHighPleasantness",
    title: "Low Energy · High Pleasantness",
    bgClass: "bg-green-100 dark:bg-green-950/40",
    textClass: "text-green-900 dark:text-green-200",
  },
];

function moodKey(mood: MoodCell) {
  return `${mood.quadrant}:${mood.name}`;
}

function Quadrant({
  config,
  moods,
  selectedKey,
  onSelect,
  disabled,
}: {
  config: (typeof QUADRANT_CONFIG)[number];
  moods: MoodCell[];
  selectedKey: string | null;
  onSelect: (mood: MoodCell) => void;
  disabled?: boolean;
}) {
  return (
    <div className={`rounded-lg p-3 ${config.bgClass}`}>
      <div className={`text-center font-semibold text-xs mb-2 ${config.textClass}`}>
        {config.title}
      </div>
      <div className="grid grid-cols-5 grid-rows-5 gap-1">
        {moods.map((mood) => {
          const key = moodKey(mood);
          const isSelected = selectedKey === key;
          const localRow = (mood.row % 5) + 1;
          const localCol = (mood.col % 5) + 1;
          const emoji = MOOD_EMOJI[mood.name] ?? '•';

          return (
            <button
              key={key}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(mood)}
              style={{ gridRow: localRow, gridColumn: localCol }}
              className={`rounded-md px-1 py-2 text-[11px] font-medium border transition-colors ${
                isSelected
                  ? "bg-foreground text-background border-foreground shadow-sm"
                  : `bg-background/70 hover:bg-background ${config.textClass} border-border/50 hover:border-border`
              } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
              aria-label={mood.name}
            >
              <span className="flex flex-col items-center gap-0.5 leading-none">
                <span className="text-base">{emoji}</span>
                <span className="text-[10px] font-medium">{mood.name}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function MoodMeterInput({
  value,
  onChange,
  disabled = false,
}: {
  value: MoodSelection | null;
  onChange: (selection: MoodSelection) => void;
  disabled?: boolean;
}) {
  const selectedKey = value ? moodKey({ ...value, name: value.moodName } as MoodCell) : null;

  const handleSelect = (mood: MoodCell) => {
    if (disabled) return;
    onChange({
      quadrant: mood.quadrant,
      moodName: mood.name,
      row: mood.row,
      col: mood.col,
    });
  };

  return (
    <div className="space-y-3">
      <div className="text-center text-sm text-muted-foreground mb-2">
        How are you feeling? Select the mood that best describes you right now.
      </div>
      <div className="grid grid-cols-2 gap-3">
        {QUADRANT_CONFIG.map((config) => (
          <Quadrant
            key={config.key}
            config={config}
            moods={MOODS_BY_QUADRANT[config.key]}
            selectedKey={selectedKey}
            onSelect={handleSelect}
            disabled={disabled}
          />
        ))}
      </div>
      {value && (
        <div className="text-center text-sm font-medium text-foreground mt-2">
          Selected: <span className="font-bold">{MOOD_EMOJI[value.moodName] ?? ''} {value.moodName}</span>
        </div>
      )}
    </div>
  );
}
