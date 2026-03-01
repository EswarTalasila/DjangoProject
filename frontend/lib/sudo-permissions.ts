export type PermissionGroup = {
  key: string;
  title: string;
  description: string;
  permissions: string[];
};

type PermissionMeta = {
  label: string;
  group: string;
};

const PERMISSION_META: Record<string, PermissionMeta> = {
  CREATE_TEACHER: {
    label: 'Create Teacher Accounts',
    group: 'user_management',
  },
  CREATE_STUDENT: {
    label: 'Create Student Accounts',
    group: 'user_management',
  },
  ISSUE_RESEARCHER_REG_CODE: {
    label: 'Issue Researcher Registration Codes',
    group: 'registration',
  },
  ISSUE_STUDENT_REG_CODE: {
    label: 'Issue Student Registration Codes',
    group: 'registration',
  },
  EDIT_USER: {
    label: 'Edit User Accounts',
    group: 'user_management',
  },
  DELETE_USER: {
    label: 'Delete User Accounts',
    group: 'user_management',
  },
  ISSUE_STUDENT_RESET_CODE: {
    label: 'Issue Student Password Reset Codes',
    group: 'password_reset',
  },
  ISSUE_RESEARCHER_RESET_CODE: {
    label: 'Issue Researcher Password Reset Codes',
    group: 'password_reset',
  },
  VIEW_IDENTIFIABLE_VIZ: {
    label: 'View Identifiable Visualization Data',
    group: 'data_access',
  },
  EXPORT_IDENTIFIABLE: {
    label: 'Export Identifiable Data',
    group: 'data_access',
  },
};

const GROUP_ORDER: Array<{ key: string; title: string; description: string }> = [
  {
    key: 'registration',
    title: 'Registration Permissions',
    description: 'Control registration code issuance for students and researchers.',
  },
  {
    key: 'password_reset',
    title: 'Password Reset Permissions',
    description: 'Control issuance of reset codes by role.',
  },
  {
    key: 'user_management',
    title: 'User Management Permissions',
    description: 'Control account create/edit/delete operations.',
  },
  {
    key: 'data_access',
    title: 'Data Access Permissions',
    description: 'Control access to identifiable data in analytics and exports.',
  },
];

export const SUDO_CAPABILITY_NOTE =
  'You can only delegate a subset of your own permissions.';

export function getSudoPermissionLabel(permission: string): string {
  return PERMISSION_META[permission]?.label ?? permission;
}

export function groupSudoPermissions(permissions: string[]): PermissionGroup[] {
  return GROUP_ORDER.map((group) => ({
    ...group,
    permissions: permissions.filter((permission) => PERMISSION_META[permission]?.group === group.key),
  })).filter((group) => group.permissions.length > 0);
}
