import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router";
import { api, ApiError, type User } from "./api/client";
import { Shell } from "./app/Shell";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Setup } from "./pages/Setup";

export function App() {
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () =>
      api<User>("/auth/me").catch((e) => {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }),
  });
  const user = me.data;
  const setup = useQuery({
    queryKey: ["setup"],
    queryFn: () => api<{ needed: boolean }>("/setup"),
    enabled: user === null,
    staleTime: 0,
  });

  if (me.isError) return <p className="auth error">Can't reach the server.</p>;
  if (user === undefined || (user === null && !setup.data)) return null;
  if (user === null) return setup.data?.needed ? <Setup /> : <Login />;

  return (
    <Routes>
      <Route element={<Shell user={user} />}>
        <Route index element={<Home />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
