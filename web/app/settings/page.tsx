'use client';

import { useEffect, useState } from 'react';
import { auth, gmail } from '@/lib/api';

// ---------------------------------------------------------------------------
// Gmail Integration Card
// ---------------------------------------------------------------------------

function GmailCard() {
  const [status, setStatus] = useState<{ connected: boolean; email: string | null } | null>(null);
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const fetchStatus = () => {
    gmail.status().then(setStatus).catch(() => setStatus({ connected: false, email: null }));
  };

  useEffect(() => {
    fetchStatus();
    // If returning from OAuth callback, refresh status
    const params = new URLSearchParams(window.location.search);
    if (params.get('gmail') === 'connected') {
      window.history.replaceState({}, '', '/settings');
    }
  }, []);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await gmail.saveCredentials(clientId, clientSecret);
      const { url } = await gmail.getAuthUrl();
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start OAuth flow');
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnect = async () => {
    setError('');
    try {
      await gmail.disconnect();
      setStatus({ connected: false, email: null });
      setClientId('');
      setClientSecret('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect');
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-900">Gmail Integration</h2>
        {status?.connected ? (
          <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Connected{status.email ? ` — ${status.email}` : ''}
          </span>
        ) : (
          <span className="text-xs font-medium text-slate-400 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-full">
            Not connected
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {status?.connected ? (
        <div className="space-y-3">
          <p className="text-sm text-slate-500">
            Gmail tools are available to agents. Agents can read, send, label, and manage emails.
          </p>
          <button
            onClick={handleDisconnect}
            className="px-4 py-2 rounded-lg border border-red-200 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
          >
            Disconnect Gmail
          </button>
        </div>
      ) : (
        <form onSubmit={handleConnect} className="space-y-4">
          <p className="text-sm text-slate-500">
            Paste your Google OAuth credentials from{' '}
            <span className="font-mono text-xs bg-slate-100 px-1 py-0.5 rounded">
              console.cloud.google.com
            </span>
            . The redirect URI to register is{' '}
            <span className="font-mono text-xs bg-slate-100 px-1 py-0.5 rounded">
              http://localhost:8000/api/gmail/callback
            </span>
            .
          </p>
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Client ID</label>
            <input
              type="text"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="input font-mono text-sm"
              placeholder="123456789-abc.apps.googleusercontent.com"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Client Secret</label>
            <input
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              className="input font-mono text-sm"
              placeholder="GOCSPX-..."
            />
          </div>
          <button
            type="submit"
            disabled={saving || !clientId || !clientSecret}
            className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Opening Google…' : 'Save & Connect Gmail'}
          </button>
        </form>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Change Password Card
// ---------------------------------------------------------------------------

function PasswordCard() {
  const [current, setCurrent] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPw !== confirm) {
      setError('New passwords do not match.');
      return;
    }
    if (newPw.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setSaving(true);
    try {
      await auth.login(current);
      await auth.changePassword(newPw);
      setSuccess('Password changed successfully.');
      setCurrent('');
      setNewPw('');
      setConfirm('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to change password');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h2 className="font-semibold text-slate-900 mb-4">Change Password</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {success && (
          <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
            {success}
          </div>
        )}
        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700">Current Password</label>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            className="input"
            placeholder="••••••••"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700">New Password</label>
          <input
            type="password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            className="input"
            placeholder="••••••••"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700">Confirm New Password</label>
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="input"
            placeholder="••••••••"
          />
        </div>
        <button
          type="submit"
          disabled={saving || !current || !newPw || !confirm}
          className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving…' : 'Change Password'}
        </button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-lg">
      <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
      <GmailCard />
      <PasswordCard />
    </div>
  );
}
