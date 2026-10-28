import { LogOut } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { User } from "../../api/client";
import { useChangePassword, useChangeUsername, useLogout } from "../../api/hooks";
import { Card } from "../../components/Card";
import { Field } from "../../components/Field";
import { errorsOf } from "./errorsOf";

function PasswordForm() {
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [done, setDone] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    setDone(false);
    if (next !== confirm) return setErrs({ confirm: "Passwords don't match" });
    setErrs({});
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          setCurrent("");
          setNext("");
          setConfirm("");
          setDone(true);
        },
        onError: (x) => setErrs(errorsOf(x)),
      },
    );
  }
  const fieldBound = errs.current_password || errs.new_password || errs.confirm;
  return (
    <form className="fields" onSubmit={submit} noValidate>
      <h3 className="label token-new-head">Change password</h3>
      <Field label="Current password" error={errs.current_password}>
        {(a) => <input {...a} type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />}
      </Field>
      <div className="pair">
        <Field label="New password" error={errs.new_password}>
          {(a) => <input {...a} type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />}
        </Field>
        <Field label="Confirm new password" error={errs.confirm}>
          {(a) => <input {...a} type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />}
        </Field>
      </div>
      {errs.form && !fieldBound && (
        <p className="error" role="alert">
          {errs.form}
        </p>
      )}
      <div className="actions">
        <button className="btn primary" disabled={!current || !next || !confirm || change.isPending}>
          Change password
        </button>
        <span role="status" className="muted">
          {done && "Password changed. Other sessions were signed out."}
        </span>
      </div>
    </form>
  );
}

function UsernameForm() {
  const change = useChangeUsername();
  const [current, setCurrent] = useState("");
  const [name, setName] = useState("");
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [done, setDone] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    setDone(false);
    setErrs({});
    change.mutate(
      { current_password: current, username: name },
      {
        onSuccess: () => {
          setCurrent("");
          setName("");
          setDone(true);
        },
        onError: (x) => setErrs(errorsOf(x)),
      },
    );
  }
  return (
    <form className="fields" onSubmit={submit} noValidate>
      <h3 className="label token-new-head">Change username</h3>
      <div className="pair">
        <Field label="New username" error={errs.username}>
          {(a) => <input {...a} autoComplete="username" value={name} onChange={(e) => setName(e.target.value)} />}
        </Field>
        <Field label="Current password" error={errs.current_password}>
          {(a) => <input {...a} type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />}
        </Field>
      </div>
      {errs.form && !errs.username && !errs.current_password && (
        <p className="error" role="alert">
          {errs.form}
        </p>
      )}
      <div className="actions">
        <button className="btn primary" disabled={!current || !name.trim() || change.isPending}>
          Change username
        </button>
        <span role="status" className="muted">
          {done && "Username changed."}
        </span>
      </div>
    </form>
  );
}

export function AccountCard() {
  const logout = useLogout();
  const user = useQueryClient().getQueryData<User>(["me"]);
  return (
    <Card label="Account">
      <p>Signed in as {user?.username}.</p>
      <PasswordForm />
      <UsernameForm />
      <div className="actions token-new-head">
        <button className="btn" onClick={() => logout.mutate()}>
          <LogOut size={18} aria-hidden="true" /> Sign out
        </button>
      </div>
    </Card>
  );
}
