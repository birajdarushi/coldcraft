import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { useAuth } from "../lib/auth.jsx";
import { LogoMark } from "../components/Logo.jsx";
import { Button, Input, Banner } from "../components/ui.jsx";

export default function Login() {
  const { login } = useAuth();
  const [step, setStep] = useState("email"); // "email" | "code"
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const codeRef = useRef(null);

  useEffect(() => {
    if (step === "code") codeRef.current?.focus();
  }, [step]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  async function sendCode(e) {
    e?.preventDefault();
    setError("");
    setNotice("");
    const addr = email.trim();
    if (!addr.includes("@")) {
      setError("Enter a valid email address.");
      return;
    }
    setBusy(true);
    try {
      await api.requestOtp(addr);
      setStep("code");
      setNotice(`Code sent to ${addr}. Check your inbox.`);
      setCooldown(30);
    } catch (err) {
      setError(err.detail || "Could not send the code. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function verify(e) {
    e?.preventDefault();
    setError("");
    if (code.trim().length < 6) {
      setError("Enter the 6-digit code.");
      return;
    }
    setBusy(true);
    try {
      const res = await api.verifyOtp(email.trim(), code.trim());
      login(res.token, res.email); // unmounts this screen
    } catch (err) {
      setError(err.detail || "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 grid-bg bg-background text-foreground flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <LogoMark size={48} />
          <div className="font-sans font-extrabold tracking-tighter uppercase text-2xl mt-4">
            Coldcraft
          </div>
          <div className="font-mono text-[9px] tracking-[0.35em] text-muted-foreground mt-1">
            GTM·ENGINE
          </div>
        </div>

        <div className="border border-border bg-surface p-6">
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground mb-4">
            {step === "email" ? "SIGN IN · EMAIL CODE" : "ENTER VERIFICATION CODE"}
          </div>

          {error && <Banner tone="error" testId="login-error">{error}</Banner>}
          {!error && notice && <Banner tone="success" testId="login-notice">{notice}</Banner>}

          {step === "email" ? (
            <form onSubmit={sendCode} className="mt-4 space-y-3">
              <Input
                type="email"
                autoFocus
                inputMode="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="login-email"
              />
              <Button
                type="submit"
                variant="primary"
                className="w-full"
                disabled={busy}
                data-testid="login-send"
              >
                {busy ? "Sending…" : "Send code"}
              </Button>
            </form>
          ) : (
            <form onSubmit={verify} className="mt-4 space-y-3">
              <Input
                ref={codeRef}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                placeholder="000000"
                className="text-center tracking-[0.5em] text-lg"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                data-testid="login-code"
              />
              <Button
                type="submit"
                variant="primary"
                className="w-full"
                disabled={busy}
                data-testid="login-verify"
              >
                {busy ? "Verifying…" : "Verify & enter"}
              </Button>
              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={() => { setStep("email"); setCode(""); setError(""); setNotice(""); }}
                  className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground hover:text-foreground"
                >
                  ← Change email
                </button>
                <button
                  type="button"
                  disabled={cooldown > 0 || busy}
                  onClick={sendCode}
                  className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground hover:text-foreground disabled:opacity-40"
                >
                  {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="font-mono text-[9px] tracking-[0.2em] text-muted-foreground/60 text-center mt-6 uppercase">
          Passwordless · codes expire in 10 min
        </div>
      </div>
    </div>
  );
}
