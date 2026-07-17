import DashboardIcon from '@mui/icons-material/Dashboard';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import DescriptionIcon from '@mui/icons-material/Description';
import AssignmentIcon from '@mui/icons-material/Assignment';
import MonitorIcon from '@mui/icons-material/Monitor';
import AssessmentIcon from '@mui/icons-material/Assessment';
import BarChartIcon from '@mui/icons-material/BarChart';
import SupervisorAccountIcon from '@mui/icons-material/SupervisorAccount';
import SettingsIcon from '@mui/icons-material/Settings';
import PersonIcon from '@mui/icons-material/Person';

export interface ResourceConfig {
  name: string;
  route: string;
  icon: React.ElementType;
  permissions: string[];
  searchable: boolean;
  navVisibility: boolean;
  dashboardVisibility: boolean;
}

export const resourceRegistry: ResourceConfig[] = [
  {
    name: 'Dashboard',
    route: '/examiner/dashboard',
    icon: DashboardIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: false,
    navVisibility: true,
    dashboardVisibility: false,
  },
  {
    name: 'Exams',
    route: '/examiner/exams',
    icon: AssignmentIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: true,
    navVisibility: true,
    dashboardVisibility: true,
  },
  {
    name: 'Students',
    route: '/examiner/students',
    icon: PersonAddIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: true,
    navVisibility: true,
    dashboardVisibility: true,
  },
  {
    name: 'Supervisors',
    route: '/examiner/supervisors',
    icon: SupervisorAccountIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: true,
    navVisibility: true,
    dashboardVisibility: true,
  },
  {
    name: 'Question Papers',
    route: '/examiner/question-papers',
    icon: DescriptionIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: true,
    navVisibility: true,
    dashboardVisibility: true,
  },
  {
    name: 'Monitoring',
    route: '/examiner/monitoring',
    icon: MonitorIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: false,
    navVisibility: true,
    dashboardVisibility: true,
  },
  {
    name: 'Reports',
    route: '/examiner/reports',
    icon: AssessmentIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: true,
    navVisibility: true,
    dashboardVisibility: true,
  },
  {
    name: 'Statistics',
    route: '/examiner/statistics',
    icon: BarChartIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: false,
    navVisibility: true,
    dashboardVisibility: false,
  },
  {
    name: 'Profile',
    route: '/examiner/profile',
    icon: PersonIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: false,
    navVisibility: false, // In User Menu instead
    dashboardVisibility: false,
  },
  {
    name: 'Settings',
    route: '/examiner/settings',
    icon: SettingsIcon,
    permissions: ['Examiner', 'Admin'],
    searchable: false,
    navVisibility: false, // In User Menu instead
    dashboardVisibility: false,
  },
  {
    name: 'System Dashboard',
    route: '/admin/system-dashboard',
    icon: DashboardIcon,
    permissions: ['Admin'],
    searchable: true,
    navVisibility: true,
    dashboardVisibility: true,
  },
  {
    name: 'Platform Settings',
    route: '/admin/platform-settings',
    icon: SettingsIcon,
    permissions: ['Admin'],
    searchable: true,
    navVisibility: true,
    dashboardVisibility: true,
  },
  {
    name: 'System Logs',
    route: '/admin/system-logs',
    icon: AssignmentIcon,
    permissions: ['Admin'],
    searchable: true,
    navVisibility: true,
    dashboardVisibility: true,
  }
];
