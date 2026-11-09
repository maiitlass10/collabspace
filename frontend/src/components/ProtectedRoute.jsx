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

/** Where to go after logging in: the page that was requested, or the dashboard. */
export function redirectTarget(location) {
  const from = location.state?.from;
  // Only paths inside this app (never "//other-site.com").
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/";
}

/** Login/register pages: logged-in users are sent on (see redirectTarget). */
export function GuestRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <FullPageLoader />;
  // This also runs right after a successful login, so it must use the same
  // target as LoginPage; otherwise it would win the race and always go to "/".
  if (status === "authenticated") return <Navigate to={redirectTarget(location)} replace />;
  return <Outlet />;
}
