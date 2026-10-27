import { AuthForm } from "./AuthForm";

export const Setup = () => (
  <AuthForm
    title="Set up your account"
    hint="First run. This creates the only account."
    submit="Create account"
    path="/setup"
    newPassword
  />
);
