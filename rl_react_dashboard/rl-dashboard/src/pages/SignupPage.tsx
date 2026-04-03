import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api, endpoints, setAccessToken } from "../services/api";
import { useAuthStore } from "../store";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setUser } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const { data } = await api.post(endpoints.auth.signup, { name, email, password });
      setAccessToken(data.data.accessToken);
      setUser(data.data.user);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 dark:bg-neutral-950 px-4 transition-colors relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-emerald-500/5 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-teal-500/5 blur-3xl" />
      </div>

      <div className="w-full max-w-sm relative">
        <div className="mb-10 text-center">
          <div className="inline-flex h-12 w-12 rounded-xl bg-emerald-500 items-center justify-center mb-4 shadow-lg shadow-emerald-500/20">
            <span className="text-white text-sm font-black">RL</span>
          </div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Create account</h1>
          <p className="mt-1.5 text-sm text-neutral-500">Start trading with RL agents</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          {error && (
            <div className="rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 px-4 py-3 text-[12px] text-red-600 dark:text-red-400 font-medium">
              {error}
            </div>
          )}

          <div>
            <label className="block text-[11px] font-semibold text-neutral-500 mb-1.5 uppercase tracking-wider">Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} required
              className="w-full rounded-xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 px-4 py-3 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all" />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-neutral-500 mb-1.5 uppercase tracking-wider">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
              className="w-full rounded-xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 px-4 py-3 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all" />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-neutral-500 mb-1.5 uppercase tracking-wider">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              className="w-full rounded-xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 px-4 py-3 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all" />
          </div>

          <button type="submit" disabled={loading}
            className="mt-2 rounded-xl bg-emerald-500 py-3 text-sm font-bold text-white hover:bg-emerald-600 transition-all disabled:opacity-50 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 active:scale-[0.98]">
            {loading ? "Creating..." : "Create account"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-[11px]">
            Already have an account?{" "}
            <Link to="/login" className="text-emerald-600 dark:text-emerald-400 font-semibold hover:text-emerald-500">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
