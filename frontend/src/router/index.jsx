import { createBrowserRouter } from "react-router-dom";

import AppLayout from "@/layouts/AppLayout";
import { ProtectedRoute, PublicOnlyRoute } from "@/router/guards";
import LoginPage from "@/features/auth/pages/LoginPage";
import RegisterPage from "@/features/auth/pages/RegisterPage";
import ForgotPasswordPage from "@/features/auth/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/features/auth/pages/ResetPasswordPage";
import DashboardPage from "@/features/dashboard/pages/DashboardPage";
import NotFoundPage from "@/pages/NotFoundPage";
import LeadsListPage from "@/features/leads/pages/LeadsListPage";
import LeadCreatePage from "@/features/leads/pages/LeadCreatePage";
import LeadDetailPage from "@/features/leads/pages/LeadDetailPage";
import CustomersListPage from "@/features/customers/pages/CustomersListPage";
import CustomerDetailPage from "@/features/customers/pages/CustomerDetailPage";
import TasksListPage from "@/features/tasks/pages/TasksListPage";
import TaskCreatePage from "@/features/tasks/pages/TaskCreatePage";
import TaskDetailPage from "@/features/tasks/pages/TaskDetailPage";
import MeetingsListPage from "@/features/meetings/pages/MeetingsListPage";
import MeetingCreatePage from "@/features/meetings/pages/MeetingCreatePage";
import MeetingDetailPage from "@/features/meetings/pages/MeetingDetailPage";
import FollowUpsListPage from "@/features/followups/pages/FollowUpsListPage";
import RemindersPage from "@/features/reminders/pages/RemindersPage";
import QuotationsListPage from "@/features/quotations/pages/QuotationsListPage";
import QuotationCreatePage from "@/features/quotations/pages/QuotationCreatePage";
import QuotationDetailPage from "@/features/quotations/pages/QuotationDetailPage";
import NotificationsPage from "@/features/notifications/pages/NotificationsPage";
import NotificationTemplatesPage from "@/features/notifications/pages/NotificationTemplatesPage";
import CallTemplatesPage from "@/features/callforms/pages/CallTemplatesPage";
import CallTemplateDetailPage from "@/features/callforms/pages/CallTemplateDetailPage";
import CallFormSubmitPage from "@/features/callforms/pages/CallFormSubmitPage";
import CallFormRulesPage, { AdhocProposalsPage } from "@/features/callforms/pages/CallFormRulesPage";
import AdminRolesPage from "@/features/admin/pages/AdminRolesPage";
import AdminLeadSourcesPage from "@/features/admin/pages/AdminLeadSourcesPage";
import AdminPipelinesPage from "@/features/admin/pages/AdminPipelinesPage";
import AuditLogsPage from "@/features/admin/pages/AuditLogsPage";
import ProfilePage from "@/features/admin/pages/ProfilePage";
import SettingsPage from "@/features/settings/pages/SettingsPage";
import StitchPreview from "@/pages/StitchPreview";
import RouteErrorBoundary from "@/pages/RouteErrorBoundary";

export const router = createBrowserRouter([
  {
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        element: <PublicOnlyRoute />,
        errorElement: <RouteErrorBoundary />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/register", element: <RegisterPage /> },
          { path: "/forgot-password", element: <ForgotPasswordPage /> },
          { path: "/reset-password", element: <ResetPasswordPage /> },
        ],
      },
      {
        element: <ProtectedRoute />,
        errorElement: <RouteErrorBoundary />,
        children: [
          {
            element: <AppLayout />,
            errorElement: <RouteErrorBoundary />,
            children: [
          { path: "/", element: <DashboardPage /> },
          { path: "/leads", element: <LeadsListPage /> },
          { path: "/leads/new", element: <LeadCreatePage /> },
          { path: "/leads/:leadId", element: <LeadDetailPage /> },
          { path: "/customers", element: <CustomersListPage /> },
          { path: "/customers/:customerId", element: <CustomerDetailPage /> },
          { path: "/tasks", element: <TasksListPage /> },
          { path: "/tasks/new", element: <TaskCreatePage /> },
          { path: "/tasks/:taskId", element: <TaskDetailPage /> },
          { path: "/meetings", element: <MeetingsListPage /> },
          { path: "/meetings/new", element: <MeetingCreatePage /> },
          { path: "/meetings/:meetingId", element: <MeetingDetailPage /> },
          { path: "/followups", element: <FollowUpsListPage /> },
          { path: "/quotations", element: <QuotationsListPage /> },
          { path: "/quotations/new", element: <QuotationCreatePage /> },
          { path: "/quotations/:quotationId", element: <QuotationDetailPage /> },
          { path: "/notifications", element: <NotificationsPage /> },
          { path: "/notifications/templates", element: <NotificationTemplatesPage /> },
          { path: "/callforms", element: <CallTemplatesPage /> },
          { path: "/callforms/templates/:templateId", element: <CallTemplateDetailPage /> },
          { path: "/callforms/submit", element: <CallFormSubmitPage /> },
          { path: "/callforms/rules", element: <CallFormRulesPage /> },
          { path: "/callforms/adhoc", element: <AdhocProposalsPage /> },
          { path: "/admin/roles", element: <AdminRolesPage /> },
          { path: "/admin/sources", element: <AdminLeadSourcesPage /> },
          { path: "/admin/pipelines", element: <AdminPipelinesPage /> },
          { path: "/admin/audit-logs", element: <AuditLogsPage /> },
          { path: "/profile", element: <ProfilePage /> },
          { path: "/settings", element: <SettingsPage /> },
          { path: "/stitch-preview", element: <StitchPreview /> },
          { path: "/reminders", element: <RemindersPage /> },
          // Remaining module routes land in Phases 13–15.
        ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
