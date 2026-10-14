import { createBrowserRouter, Navigate } from 'react-router-dom';

// Layouts
import PublicLayout from '../layouts/PublicLayout';
import StudentLayout from '../layouts/StudentLayout';
import ExaminerLayout from '../layouts/ExaminerLayout';

// Components
import ProtectedRoute from '../components/ProtectedRoute';

// Pages
import LandingPage from '../pages/LandingPage';
import TodaysExamsPage from '../pages/student/TodaysExamsPage';
import StudentLoginPage from '../pages/student/StudentLoginPage';
import ExamInstructionsPage from '../pages/student/ExamInstructionsPage';
import DeviceCheckPage from '../pages/student/DeviceCheckPage';
import IdentityVerificationPage from '../pages/student/IdentityVerificationPage';
import OnlineExamPage from '../pages/student/OnlineExamPage';
import SubmissionPage from '../pages/student/SubmissionPage';
import ExaminerLoginPage from '../pages/auth/ExaminerLoginPage';
import ExaminerRegisterPage from '../pages/auth/ExaminerRegisterPage';
import OTPVerificationPage from '../pages/auth/OTPVerificationPage';
import ForgotPasswordPage from '../pages/auth/ForgotPasswordPage';
import ResetPasswordPage from '../pages/auth/ResetPasswordPage';
import DashboardPage from '../pages/examiner/DashboardPage';
import StudentRegistrationPage from '../pages/examiner/StudentRegistrationPage';
import QuestionPapersPage from '../pages/examiner/QuestionPapersPage';
import ExamsPage from '../pages/examiner/ExamsPage';
import ExamBuilderPage from '../pages/examiner/ExamBuilderPage';
import ExamDetailsWorkspacePage from '../pages/examiner/ExamDetailsWorkspacePage';
import LiveMonitoringPage from '../pages/examiner/LiveMonitoringPage';
import MonitoringListPage from '../pages/examiner/MonitoringListPage';
import MonitoringReportsPage from '../pages/examiner/MonitoringReportsPage';
import StatisticsPage from '../pages/examiner/StatisticsPage';
import AttemptReviewPage from '../pages/examiner/AttemptReviewPage';
import ProfilePage from '../pages/examiner/ProfilePage';
import SupervisorsPage from '../pages/examiner/SupervisorsPage';
import SettingsPage from '../pages/examiner/SettingsPage';

// Admin Pages
import SystemDashboardPage from '../pages/admin/SystemDashboardPage';
import SystemLogsPage from '../pages/admin/SystemLogsPage';
import PlatformSettingsPage from '../pages/admin/PlatformSettingsPage';

const router = createBrowserRouter([
  // Public — Landing
  {
    path: '/',
    element: <PublicLayout />,
    children: [{ index: true, element: <LandingPage /> }],
  },

  // Student Flow
  {
    path: '/student',
    element: <StudentLayout />,
    children: [
      // Open routes
      { path: 'login', element: <StudentLoginPage /> },
      // Protected routes
      {
        element: <ProtectedRoute allowedRoles={['Student']} redirectPath="/student/login" />,
        children: [
          { index: true, element: <TodaysExamsPage /> },
          { path: 'instructions', element: <ExamInstructionsPage /> },
          { path: 'device-check', element: <DeviceCheckPage /> },
          { path: 'identity', element: <IdentityVerificationPage /> },
          { path: 'exam', element: <OnlineExamPage /> },
          { path: 'submitted', element: <SubmissionPage /> },
        ]
      }
    ]
  },

  // Examiner Auth — standalone
  {
    path: '/examiner/login',
    element: <ExaminerLoginPage />,
  },
  {
    path: '/examiner/register',
    element: <ExaminerRegisterPage />,
  },
  {
    path: '/examiner/verify-otp',
    element: <OTPVerificationPage />,
  },
  {
    path: '/examiner/forgot-password',
    element: <ForgotPasswordPage />,
  },
  {
    path: '/examiner/reset-password',
    element: <ResetPasswordPage />,
  },

  // Examiner Dashboard Shell - Protected
  {
    path: '/examiner',
    element: <ExaminerLayout />,
    children: [
      {
        element: <ProtectedRoute allowedRoles={['Examiner', 'Admin']} redirectPath="/examiner/login" />,
        children: [
          { index: true, element: <Navigate to="/examiner/dashboard" replace /> },
          { path: 'dashboard', element: <DashboardPage /> },
          { path: 'students', element: <StudentRegistrationPage /> },
          { path: 'question-papers', element: <QuestionPapersPage /> },
          { path: 'exams', element: <ExamsPage /> },
          { path: 'exams/build', element: <ExamBuilderPage /> },
          { path: 'exams/details/:examId', element: <ExamDetailsWorkspacePage /> },
          { path: 'monitoring', element: <MonitoringListPage /> },
          { path: 'monitoring/:sessionId', element: <LiveMonitoringPage /> },
          { path: 'live-monitoring/:sessionId', element: <LiveMonitoringPage /> },
          { path: 'reports', element: <MonitoringReportsPage /> },
          { path: 'attempts/:sessionId/review', element: <AttemptReviewPage /> },
          { path: 'statistics', element: <StatisticsPage /> },
          { path: 'profile', element: <ProfilePage /> },
          { path: 'supervisors', element: <SupervisorsPage /> },
          { path: 'settings', element: <SettingsPage /> },
        ]
      }
    ],
  },

  // Admin Shell - Reuses ExaminerLayout
  {
    path: '/admin',
    element: <ExaminerLayout />,
    children: [
      {
        element: <ProtectedRoute allowedRoles={['Admin']} redirectPath="/examiner/login" />,
        children: [
          { index: true, element: <Navigate to="/admin/system-dashboard" replace /> },
          { path: 'system-dashboard', element: <SystemDashboardPage /> },
          { path: 'system-logs', element: <SystemLogsPage /> },
          { path: 'platform-settings', element: <PlatformSettingsPage /> },
        ]
      }
    ]
  },

  // 404 catch-all
  { path: '*', element: <Navigate to="/" replace /> },
]);

export default router;
