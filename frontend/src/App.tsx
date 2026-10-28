import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router";
import { api, ApiError, type User } from "./api/client";
import { Shell } from "./app/Shell";
import { Documents } from "./pages/Documents";
import { Garage } from "./pages/Garage";
import { ImportLubeLogger } from "./pages/ImportLubeLogger";
import { HomeRedirect } from "./pages/HomeRedirect";
import { Login } from "./pages/Login";
import { QuickFuel } from "./pages/QuickFuel";
import { RecordForm } from "./pages/RecordForm";
import { Records } from "./pages/Records";
import { ReminderForm } from "./pages/ReminderForm";
import { Reminders } from "./pages/Reminders";
import { Settings } from "./pages/Settings";
import { Setup } from "./pages/Setup";
import { VehicleForm } from "./pages/VehicleForm";
import { VehicleHome } from "./pages/VehicleHome";

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
        <Route index element={<HomeRedirect />} />
        <Route path="garage" element={<Garage />} />
        <Route path="vehicles/new" element={<VehicleForm />} />
        <Route path="vehicles/:id" element={<VehicleHome />} />
        <Route path="vehicles/:id/edit" element={<VehicleForm />} />
        <Route path="vehicles/:id/records" element={<Records />} />
        <Route path="vehicles/:id/records/new" element={<RecordForm />} />
        <Route path="vehicles/:id/fuel" element={<QuickFuel />} />
        <Route path="vehicles/:id/reminders/new" element={<ReminderForm />} />
        <Route path="reminders" element={<Reminders />} />
        <Route path="reminders/:reminderId" element={<ReminderForm />} />
        <Route path="documents" element={<Documents />} />
        <Route path="settings" element={<Settings />} />
        <Route path="settings/import" element={<ImportLubeLogger />} />
        <Route path="records/:recordId" element={<RecordForm />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
