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
import DashboardPage from '../pages/examiner/DashboardPage';
import StudentRegistrationPage from '../pages/examiner/StudentRegistrationPage';
import QuestionPapersPage from '../pages/examiner/QuestionPapersPage';
import ExamManagementPage from '../pages/examiner/ExamManagementPage';
import LiveMonitoringPage from '../pages/examiner/LiveMonitoringPage';
import MonitoringReportsPage from '../pages/examiner/MonitoringReportsPage';
import StatisticsPage from '../pages/examiner/StatisticsPage';

const router = createBrowserRouter([
  // Public — Landing
  {
    path: '/',
    element: <PublicLayout />,
    children: [{ index: true, element: <LandingPage /> }],
  },

  // Student Flow - Open Routes
  {
    path: '/student',
    element: <StudentLayout />,
    children: [
      { path: 'login', element: <StudentLoginPage /> },
    ],
  },

  // Student Flow - Protected Routes
  {
    path: '/student',
    element: <StudentLayout />,
    children: [
      {
        element: <ProtectedRoute allowedRoles={['STUDENT']} redirectPath="/student/login" />,
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

  // Examiner Login — standalone (no drawer)
  {
    path: '/examiner/login',
    element: <ExaminerLoginPage />,
  },

  // Examiner Dashboard Shell - Protected
  {
    path: '/examiner',
    element: <ExaminerLayout />,
    children: [
      {
        element: <ProtectedRoute allowedRoles={['EXAMINER', 'ADMIN']} redirectPath="/examiner/login" />,
        children: [
          { index: true, element: <Navigate to="/examiner/dashboard" replace /> },
          { path: 'dashboard', element: <DashboardPage /> },
          { path: 'students', element: <StudentRegistrationPage /> },
          { path: 'question-papers', element: <QuestionPapersPage /> },
          { path: 'exams', element: <ExamManagementPage /> },
          { path: 'monitoring', element: <LiveMonitoringPage /> },
          { path: 'reports', element: <MonitoringReportsPage /> },
          { path: 'statistics', element: <StatisticsPage /> },
        ]
      }
    ],
  },

  // 404 catch-all
  { path: '*', element: <Navigate to="/" replace /> },
]);

export default router;
