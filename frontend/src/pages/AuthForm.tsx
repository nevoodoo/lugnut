import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api, type User } from "../api/client";

// Shared by Setup and Login: same fields, different endpoint and copy.
export function AuthForm(props: {
  title: string;
  hint: string;
  submit: string;
  path: string;
  newPassword?: boolean;
}) {
  const qc = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const m = useMutation({
    mutationFn: () => api<User>(props.path, "POST", { username, password }),
    onSuccess: (user) => {
      qc.setQueryData(["setup"], { needed: false });
      qc.setQueryData(["me"], user);
    },
  });
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    m.mutate();
  };

  return (
    <main className="auth">
      <form onSubmit={onSubmit}>
        <div>
          <div className="brand">Lugnut</div>
          <h1>{props.title}</h1>
        </div>
        <p className="label" style={{ margin: 0 }}>
          {props.hint}
        </p>
        <label className="field">
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            maxLength={64}
            required
            autoFocus
          />
        </label>
        <label className="field">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={props.newPassword ? "new-password" : "current-password"}
            minLength={props.newPassword ? 12 : undefined}
            required
          />
          {props.newPassword && <small>At least 12 characters.</small>}
        </label>
        {m.error && (
          <p className="error" role="alert">
            {m.error.message}
          </p>
        )}
        <button className="btn primary" disabled={m.isPending}>
          {props.submit}
        </button>
      </form>
    </main>
  );
}
