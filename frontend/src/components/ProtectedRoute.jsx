import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../context/AuthContext.jsx";
import { FullPageLoader } from "./ui/Spinner.jsx";
import ServerErrorScreen from "./ServerErrorScreen.jsx";

/** Only logged-in users may see the nested routes. */
export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <FullPageLoader />;
  if (status === "error") return <ServerErrorScreen />;
  if (status === "anonymous") {
    // Remember where the user wanted to go, so we can send them back after login.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

/** Login/register pages: logged-in users are sent to the dashboard. */
export function GuestRoute() {
  const { status } = useAuth();

  if (status === "loading") return <FullPageLoader />;
  if (status === "authenticated") return <Navigate to="/" replace />;
  return <Outlet />;
}
