import { Route, Routes } from "react-router";
import { GuestRoute, ProtectedRoute } from "./components/ProtectedRoute.jsx";
import AppLayout from "./layouts/AppLayout.jsx";
import AuthLayout from "./layouts/AuthLayout.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import DocumentPage from "./pages/DocumentPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import SystemStatusPage from "./pages/SystemStatusPage.jsx";

export default function App() {
  return (
    <Routes>
      {/* Pages for visitors who are NOT logged in */}
      <Route element={<GuestRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
      </Route>

      {/* Pages that require login */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/status" element={<SystemStatusPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
