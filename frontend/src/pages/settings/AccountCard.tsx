import { LogOut } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import type { User } from "../../api/client";
import { useLogout } from "../../api/hooks";
import { Card } from "../../components/Card";

export function AccountCard() {
  const logout = useLogout();
  const user = useQueryClient().getQueryData<User>(["me"]);
  return (
    <Card label="Account">
      <p>Signed in as {user?.username}.</p>
      <div className="actions">
        <button className="btn" onClick={() => logout.mutate()}>
          <LogOut size={18} aria-hidden="true" /> Sign out
        </button>
      </div>
    </Card>
  );
}
