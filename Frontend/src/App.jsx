import { Routes, Route, Navigate, Outlet } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute.jsx";
import { Shell } from "./components/Shell.jsx";
import { LandingPage } from "./pages/LandingPage.jsx";
import { LoginPage } from "./pages/LoginPage.jsx";
import { SignupPage } from "./pages/SignupPage.jsx";
import { DashboardPage } from "./pages/DashboardPage.jsx";
import { ProjectDetailPage } from "./pages/ProjectDetailPage.jsx";
import { IntegrationDocsPage } from "./pages/IntegrationDocsPage.jsx";
import { ProfilePage } from "./pages/ProfilePage.jsx";
import { SettingsPage } from "./pages/SettingsPage.jsx";
import { FaqPage } from "./pages/FaqPage.jsx";
import { UsagePage } from "./pages/UsagePage.jsx";
import { UsageKeyDetailPage } from "./pages/UsageKeyDetailPage.jsx";

function DashboardLayout() {
  return (
    <ProtectedRoute>
      <Shell>
        <Outlet />
      </Shell>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/dashboard" element={<DashboardLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="integration" element={<IntegrationDocsPage />} />
        <Route path="usage" element={<UsagePage />} />
        <Route path="usage/keys/:apiKeyId" element={<UsageKeyDetailPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="faq" element={<FaqPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
