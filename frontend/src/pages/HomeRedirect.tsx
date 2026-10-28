import { Navigate } from "react-router";
import { useVehicles } from "../api/hooks";
import { getLastVehicle } from "../lib/lastVehicle";

// The last vehicle you looked at, or the garage when there is none (or it's gone).
export function HomeRedirect() {
  const { data, isPending } = useVehicles();
  if (isPending) return null;
  const last = getLastVehicle();
  return <Navigate to={data?.some((v) => v.id === last) ? `/vehicles/${last}` : "/garage"} replace />;
}
