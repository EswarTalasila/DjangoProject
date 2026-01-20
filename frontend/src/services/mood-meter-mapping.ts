/**
 * Utility for mapping mood meter coordinates (row, col) to mood names
 */

export interface MoodWord {
  name: string;
  row: number;
  col: number;
}

// Complete mood mapping from MoodMeterComponent
const ALL_MOODS: MoodWord[] = [
  // High Energy, Low Pleasantness (rows 0-4, cols 0-4)
  { name: 'Enraged', row: 0, col: 0 },
  { name: 'Panicked', row: 0, col: 1 },
  { name: 'Stressed', row: 0, col: 2 },
  { name: 'Jittery', row: 0, col: 3 },
  { name: 'Shocked', row: 0, col: 4 },
  { name: 'Livid', row: 1, col: 0 },
  { name: 'Furious', row: 1, col: 1 },
  { name: 'Frustrated', row: 1, col: 2 },
  { name: 'Tense', row: 1, col: 3 },
  { name: 'Stunned', row: 1, col: 4 },
  { name: 'Fuming', row: 2, col: 0 },
  { name: 'Frightened', row: 2, col: 1 },
  { name: 'Angry', row: 2, col: 2 },
  { name: 'Nervous', row: 2, col: 3 },
  { name: 'Restless', row: 2, col: 4 },
  { name: 'Anxious', row: 3, col: 0 },
  { name: 'Apprehensive', row: 3, col: 1 },
  { name: 'Worried', row: 3, col: 2 },
  { name: 'Irritated', row: 3, col: 3 },
  { name: 'Annoyed', row: 3, col: 4 },
  { name: 'Repulsed', row: 4, col: 0 },
  { name: 'Troubled', row: 4, col: 1 },
  { name: 'Concerned', row: 4, col: 2 },
  { name: 'Uneasy', row: 4, col: 3 },
  { name: 'Peeved', row: 4, col: 4 },

  // High Energy, High Pleasantness (rows 0-4, cols 5-9)
  { name: 'Surprised', row: 0, col: 5 },
  { name: 'Upbeat', row: 0, col: 6 },
  { name: 'Festive', row: 0, col: 7 },
  { name: 'Exhilarated', row: 0, col: 8 },
  { name: 'Ecstatic', row: 0, col: 9 },
  { name: 'Hyper', row: 1, col: 5 },
  { name: 'Cheerful', row: 1, col: 6 },
  { name: 'Motivated', row: 1, col: 7 },
  { name: 'Inspired', row: 1, col: 8 },
  { name: 'Elated', row: 1, col: 9 },
  { name: 'Energized', row: 2, col: 5 },
  { name: 'Lively', row: 2, col: 6 },
  { name: 'Excited', row: 2, col: 7 },
  { name: 'Optimistic', row: 2, col: 8 },
  { name: 'Enthusiastic', row: 2, col: 9 },
  { name: 'Pleased', row: 3, col: 5 },
  { name: 'Focused', row: 3, col: 6 },
  { name: 'Happy', row: 3, col: 7 },
  { name: 'Proud', row: 3, col: 8 },
  { name: 'Thrilled', row: 3, col: 9 },
  { name: 'Pleasant', row: 4, col: 5 },
  { name: 'Joyful', row: 4, col: 6 },
  { name: 'Hopeful', row: 4, col: 7 },
  { name: 'Playful', row: 4, col: 8 },
  { name: 'Blissful', row: 4, col: 9 },

  // Low Energy, Low Pleasantness (rows 5-9, cols 0-4)
  { name: 'Disgusted', row: 5, col: 0 },
  { name: 'Glum', row: 5, col: 1 },
  { name: 'Disappointed', row: 5, col: 2 },
  { name: 'Down', row: 5, col: 3 },
  { name: 'Apathetic', row: 5, col: 4 },
  { name: 'Pessimistic', row: 6, col: 0 },
  { name: 'Morose', row: 6, col: 1 },
  { name: 'Discouraged', row: 6, col: 2 },
  { name: 'Sad', row: 6, col: 3 },
  { name: 'Bored', row: 6, col: 4 },
  { name: 'Alienated', row: 7, col: 0 },
  { name: 'Miserable', row: 7, col: 1 },
  { name: 'Lonely', row: 7, col: 2 },
  { name: 'Disheartened', row: 7, col: 3 },
  { name: 'Tired', row: 7, col: 4 },
  { name: 'Despondent', row: 8, col: 0 },
  { name: 'Depressed', row: 8, col: 1 },
  { name: 'Sullen', row: 8, col: 2 },
  { name: 'Exhausted', row: 8, col: 3 },
  { name: 'Fatigued', row: 8, col: 4 },
  { name: 'Despairing', row: 9, col: 0 },
  { name: 'Hopeless', row: 9, col: 1 },
  { name: 'Desolate', row: 9, col: 2 },
  { name: 'Spent', row: 9, col: 3 },
  { name: 'Drained', row: 9, col: 4 },

  // Low Energy, High Pleasantness (rows 5-9, cols 5-9)
  { name: 'Eddied', row: 5, col: 5 },
  { name: 'Easy-Going', row: 5, col: 6 },
  { name: 'Content', row: 5, col: 7 },
  { name: 'Loving', row: 5, col: 8 },
  { name: 'Fulfilled', row: 5, col: 9 },
  { name: 'Calm', row: 6, col: 5 },
  { name: 'Secure', row: 6, col: 6 },
  { name: 'Satisfied', row: 6, col: 7 },
  { name: 'Grateful', row: 6, col: 8 },
  { name: 'Touched', row: 6, col: 9 },
  { name: 'Relaxed', row: 7, col: 5 },
  { name: 'Chill', row: 7, col: 6 },
  { name: 'Restful', row: 7, col: 7 },
  { name: 'Blessed', row: 7, col: 8 },
  { name: 'Balanced', row: 7, col: 9 },
  { name: 'Mellow', row: 8, col: 5 },
  { name: 'Thoughtful', row: 8, col: 6 },
  { name: 'Peaceful', row: 8, col: 7 },
  { name: 'Comfortable', row: 8, col: 8 },
  { name: 'Carefree', row: 8, col: 9 },
  { name: 'Sleepy', row: 9, col: 5 },
  { name: 'Complacent', row: 9, col: 6 },
  { name: 'Tranquil', row: 9, col: 7 },
  { name: 'Cozy', row: 9, col: 8 },
  { name: 'Serene', row: 9, col: 9 },
];

/**
 * Get the mood name for a given row and column
 * @param row - The row coordinate (0-9)
 * @param col - The column coordinate (0-9)
 * @returns The mood name, or a default string if not found
 */
export function getMoodName(row: number, col: number): string {
  const mood = ALL_MOODS.find(m => m.row === row && m.col === col);
  return mood ? mood.name : `Unknown mood (${row}, ${col})`;
}

/**
 * Get the quadrant description for a given row and column
 * @param row - The row coordinate (0-9)
 * @param col - The column coordinate (0-9)
 * @returns The quadrant description
 */
export function getMoodQuadrant(row: number, col: number): string {
  const isHighEnergy = row <= 4;
  const isHighPleasantness = col >= 5;

  if (isHighEnergy && !isHighPleasantness) {
    return 'High Energy / Low Pleasantness';
  } else if (isHighEnergy && isHighPleasantness) {
    return 'High Energy / High Pleasantness';
  } else if (!isHighEnergy && !isHighPleasantness) {
    return 'Low Energy / Low Pleasantness';
  } else {
    return 'Low Energy / High Pleasantness';
  }
}

