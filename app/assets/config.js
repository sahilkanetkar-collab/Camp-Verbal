// ─────────────────────────────────────────────────────────────
//  Camp Verbal app settings — the only file you edit after setup.
//  Both values come from Supabase → Project Settings → API Keys.
//  The publishable key is designed to be public; security is enforced by
//  the database rules, not by hiding this key.
// ─────────────────────────────────────────────────────────────
window.CV_CONFIG = {
  supabaseUrl: 'https://kgxjdzeciiajlgierjpn.supabase.co',
  supabaseAnonKey: 'sb_publishable_butl8cOHsMdBPeTAauXM9Q_J9jh0J1E',
  // Where "Get access" buttons send students for now (until payments are added).
  accessUrl: '/#enquiry',
  // Must match Supabase → Authentication → Sign In / Providers → Email → "Email OTP Length".
  otpLength: 8
};
