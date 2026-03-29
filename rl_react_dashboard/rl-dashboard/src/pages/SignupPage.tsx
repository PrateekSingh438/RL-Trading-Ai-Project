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
    <div className="flex min-h-screen items-center justify-center bg-neutral-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-xl font-semibold text-neutral-100">Create account</h1>
          <p className="mt-1 text-sm text-neutral-500">Start trading with RL agents</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          {error && (
            <div className="rounded-md bg-red-500/10 border border-red-500/20 px-3 py-2 text-xs text-red-400">
              {error}
            </div>
          )}

          <input type="text" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required
            className="rounded-md bg-neutral-900 border border-neutral-800 px-3 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 outline-none focus:border-neutral-600 transition-colors" />
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required
            className="rounded-md bg-neutral-900 border border-neutral-800 px-3 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 outline-none focus:border-neutral-600 transition-colors" />
          <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required
            className="rounded-md bg-neutral-900 border border-neutral-800 px-3 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 outline-none focus:border-neutral-600 transition-colors" />

          <button type="submit" disabled={loading}
            className="rounded-md bg-emerald-600 py-2.5 text-sm font-medium text-white hover:bg-emerald-500 transition-colors disabled:opacity-50">
            {loading ? "Creating..." : "Create account"}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-neutral-600">
          Already have an account?{" "}
          <Link to="/login" className="text-emerald-500 hover:text-emerald-400">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
