import { AuthForm } from "./AuthForm";

export const Login = () => (
  <AuthForm title="Sign in" hint="Your garage, your logbook." submit="Sign in" path="/auth/login" />
);
