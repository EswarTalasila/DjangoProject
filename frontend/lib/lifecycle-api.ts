/**
 * Centralized re-exports for lifecycle operations (archive / restore / purge).
 *
 * The canonical implementations live in each domain API file.
 * This module exists so DataArchivesTab can import all lifecycle
 * functions from a single location without reaching into three files.
 */

export type LifecycleStatus = 'ACTIVE' | 'ARCHIVED';

// -- Course lifecycle --
export { archiveCourse, restoreCourse, deleteCourse as purgeCourse } from '@/lib/course-api';

// -- Assignment template lifecycle --
export {
  archiveAssignmentTemplate,
  restoreAssignmentTemplate,
  purgeAssignmentTemplate,
} from '@/lib/assignment-template-api';

// -- Assignment lifecycle --
export { archiveAssignment, restoreAssignment, deleteAssignment as purgeAssignment } from '@/lib/assignment-api';
