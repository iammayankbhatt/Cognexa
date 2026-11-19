# Cognexa — Phase 0: Account & Tool Setup Guide

Do this before Phase 1. It takes about 2–3 hours, mostly waiting for things to provision. Every service here is **free**. Dashboard menu names change often, so if a label differs slightly, look for the closest match.

**Where to put this file:** `docs/PHASE0_SETUP.md` in your repo.

---

## Step 0 — Ground rules (10 min)

1. **Create one shared team Google account**, e.g. `cognexa.team@gmail.com`. Turn on 2-step verification. Use it to sign up for every service below, so the project doesn't depend on one student's personal account. Then invite each teammate's personal account wherever the free plan allows.
2. **Get a password manager.** Bitwarden's free plan works. Make a shared folder "Cognexa" with one entry per service. Every key, password and connection string goes there.
3. **Never** paste keys into WhatsApp, chat with AI tools, screenshots or git commits. If a key leaks, rotate it (delete it and create a new one) immediately.
4. Keep a **secrets worksheet** in the password manager (template in Step 12). It maps each value to the environment variable it will become.

---

## Step 1 — Local tools on every teammate's laptop (30–45 min)

| Tool | Install | Check it works |
|---|---|---|
| Git | git-scm.com | `git --version` |
| Docker Desktop | docker.com (Windows: enable the **WSL 2** backend) | `docker run hello-world` |
| Node.js **LTS** | nodejs.org (or `nvm`) | `node -v` and `npm -v` |
| Python **3.12** | python.org (or `pyenv`) | `python3.12 --version` (Windows: `py -3.12 --version`) |
| uv | docs.astral.sh/uv, see "Installation" | `uv --version` |
| Claude Code | follow the official install guide at docs.claude.com (Claude Code section) | `claude --version` |
| VS Code (optional) | code.visualstudio.com | — |

**Windows users:** do all development inside **WSL 2 (Ubuntu)**. Clone the repo inside the Linux filesystem (`~/cognexa`), not `/mnt/c/...`. Docker, Python tooling and file watching are all much more reliable there.

Set your Git identity (each person, with the email linked to their GitHub account so commits count toward them):
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

---

## Step 2 — GitHub (15 min)

1. Each teammate needs a GitHub account. Apply for the **GitHub Student Developer Pack** (education.github.com) with your university email. It's free and includes extra perks; check the current offers.
2. Create an organisation (free), e.g. `cognexa-team`, and add all four members as owners.
3. Create the repository `cognexa` in the org:
   - **Public** gets unlimited free Actions minutes. **Private** has a monthly free quota, enough for this project if the eval workflow stays manual. Choose public unless your university requires private.
   - No README or .gitignore. Phase 1 creates those.
4. On your machine: create the `cognexa` folder, put `CLAUDE.md` and `progressfile.md` in the root, and `COGNEXA_PROMPTS.md` and this file in `docs/`. Then:
   ```bash
   git init -b main
   git add . && git commit -m "chore: initial commit with CLAUDE.md, progressfile.md and build prompts"
   git remote add origin https://github.com/cognexa-team/cognexa.git
   git push -u origin main
   ```
5. **Protect main (light):** Repo → Settings → Rules → Rulesets (or Branches → Branch protection) → target `main` → **block force pushes and branch deletion only.** Do **not** require pull requests or required status checks: the team commits directly to `main` (DEC-012), and those rules would reject direct pushes. Instead, watch the CI run after every push and fix a red build before any new work.

---

## Step 3 — Supabase, two projects (30 min)

Make **two** projects: `cognexa-dev` (for building and testing) and `cognexa-prod` (real users). The free plan allows 2 active projects.

For **each** project:
1. Go to supabase.com → sign in with the team account (GitHub login is easiest) → **New organization** "Cognexa" (Free plan) → **New project**.
2. Name: `cognexa-dev` (then `cognexa-prod`). **Database password:** click *Generate* and save it to the password manager immediately. Region: **South Asia (Mumbai)**, the nearest to you. Wait for it to finish provisioning (2–3 minutes).
3. **Enable pgvector:** Database → Extensions → search `vector` → enable.
4. **Collect keys:** Project Settings → **API Keys**. Copy:
   - Project URL (`https://<project-ref>.supabase.co`). Note the `<project-ref>`, you'll need it for Google OAuth.
   - **Publishable key** (newer projects) or **anon** key (legacy tab). This one is public and goes to the frontend.
   - **Secret key** or **service_role** key (legacy tab). Backend only, **never** in frontend code.
5. **Collect connection strings:** click **Connect** at the top of the project. Copy, replacing `[YOUR-PASSWORD]`:
   - **Transaction pooler** (port 6543): the backend `DATABASE_URL`.
   - **Session pooler** or **Direct connection** (port 5432): for running migrations.
6. **Auth settings:**
   - Authentication → Sign In / Providers → **Email**: enabled, **Confirm email: ON**.
   - Authentication → URL Configuration → **Site URL**: `http://localhost:3000` (dev project). For prod, set the Vercel URL in Phase 15. **Redirect URLs:** add `http://localhost:3000/**`.
7. **Add teammates:** Organization Settings → Team → invite the three other personal emails. This matters because Supabase's built-in email sender **only delivers to team members** and only about 2 emails an hour. So during development, test sign-ups with teammates' addresses. Real users need Step 10.

---

## Step 4 — Google login (OAuth) (20 min)

1. Go to console.cloud.google.com (team account) → create a project **"Cognexa"**.
2. Open **Google Auth Platform**, or *APIs & Services → OAuth consent screen* in the older UI:
   - App name **Cognexa**, user support email = team email, audience **External**, developer contact = team email.
   - Scopes: keep the defaults (`openid`, `email`, `profile`). Don't add sensitive scopes.
   - While the app is in **Testing** mode, only listed **test users** can sign in. Add all four team emails now. Before the user study or launch, click **Publish app**. Apps that use only these basic scopes usually go live without a lengthy review.
3. **Clients → Create client → Web application**, name "Cognexa Supabase":
   - **Authorized JavaScript origins:** `http://localhost:3000` (add the Vercel URL in Phase 15).
   - **Authorized redirect URIs:** add both
     `https://<dev-project-ref>.supabase.co/auth/v1/callback`
     `https://<prod-project-ref>.supabase.co/auth/v1/callback`
     (The exact URL is also shown in Supabase → Authentication → Providers → Google. Copy it from there.)
   - Save the **Client ID** and **Client Secret**.
4. In **both** Supabase projects: Authentication → Sign In / Providers → **Google** → enable → paste the Client ID + Secret → Save.

---

## Step 5 — Neo4j AuraDB Free (15 min)

1. Go to console.neo4j.io → sign in with the team account.
2. **New instance → AuraDB Free.** Pick the region closest to India that's offered (Mumbai or Singapore). Name: `cognexa-prod`.
3. **The password is shown only once.** Download the credentials `.txt` file the moment it appears, and copy `NEO4J_URI` (`neo4j+s://xxxx.databases.neo4j.io`), `NEO4J_USERNAME` and `NEO4J_PASSWORD` into the password manager. If you miss it, you'll have to delete and recreate the instance.
4. Wait until the status is **Running**. Open **Query** and run `RETURN 1` to confirm it works.
5. Know these limits: one free instance only, and it **auto-pauses after 72 hours of inactivity**. If that happens, click **Resume** in the console. Phase 15's daily keep-alive prevents this. Local development uses Neo4j in Docker, so you won't burn the cloud instance while building.

---

## Step 6 — Groq API key (5 min)

1. Go to console.groq.com → sign in with the team account.
2. **API Keys → Create API Key** → name `cognexa-dev`. Copy it once into the password manager. Create a second key `cognexa-prod` for the deployed backend.
3. Open the **Limits** page and note the per-model requests/minute and requests/day for the free plan.
4. Open **Models** and note the model ID you'll use as the primary chat model: a capable general instruction-tuned model with JSON/structured output support. Phase 5 reads it from `LLM_PRIMARY_MODEL`.

## Step 7 — Gemini API key (5 min)

1. Go to aistudio.google.com → sign in with the team account → **Get API key → Create API key**. Choose "create in new project" or select the "Cognexa" Cloud project.
2. Save it. If you can, make a second key for prod.
3. In AI Studio, check the **rate limits** shown for your project. Note one **Flash**-class model ID (fallback chat + judge) and the current **embedding** model ID and its output dimension (this becomes `EMBEDDING_DIM`).
4. Be aware that on the free tier, Google may use prompts to improve its products. Cognexa only sends questions and course content, never names or emails.

**Quick key test** (optional; run in a terminal; don't paste keys anywhere else):
```bash
curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY" | head -c 300
curl -s "https://generativelanguage.googleapis.com/v1beta/models" -H "x-goog-api-key: $GEMINI_API_KEY" | head -c 300
```
Seeing a JSON list of models means the key works.

---

## Step 8 — Vercel (5 min)

1. Go to vercel.com → **Sign up with GitHub** (team account) → **Hobby** plan.
2. Allow it to access the `cognexa-team` org repos when asked.
3. **Don't import the project yet.** That happens in Phase 15.
4. Note: Hobby is for personal/non-commercial use (fine for an academic project) and is single-user, so deploy from the team account.

## Step 9 — Render (5 min)

1. Go to render.com → **Sign up with GitHub** (team account).
2. Allow access to the `cognexa` repo.
3. **Don't create a service yet.** Phase 15 uses the `render.yaml` blueprint. When you do, choose instance type **Free** and region **Singapore** (closest to India and to your Supabase region).
4. If it asks for card verification, the **Free** instance type itself costs $0. Just make sure you never select a paid instance type.

---

## Step 10 — Email sending for real users (custom SMTP) (20 min, needed before Phase 15 / user study)

Supabase's default sender only emails team members, about 2 per hour, and on new free projects you can't even edit the email templates until custom SMTP is set up. Pick one option:

| Option | Cost | Needs a domain? | Daily limit (approx.) | Notes |
|---|---|---|---|---|
| **A. Gmail SMTP** with an app password | Free | No | ~500/day | Easiest. Team Gmail → Google Account → Security → 2-Step Verification ON → **App passwords** → create one for "Supabase". Host `smtp.gmail.com`, port `465` (SSL) or `587`, user = team Gmail, password = app password |
| **B. Resend** | Free tier | Yes (verify 1 domain) | 100/day, 3,000/month | Best deliverability. Use a free domain from the GitHub Student Pack if one is offered |
| **C. Brevo** | Free tier | Recommended | ~300/day | Has a Supabase SMTP guide |

Then in **each** Supabase project: Authentication → **Emails → SMTP Settings** → enable custom SMTP → fill in host/port/user/password, sender email, and sender name **"Cognexa"** → save. Then go to Authentication → **Rate Limits** and check the email limit (it rises to about 30/hour after custom SMTP; set it no higher than your provider allows). Send yourself a test sign-up.

For a study with 40–100 students, option A or B is plenty.

---

## Step 11 — Optional: error tracking

**Sentry** (sentry.io) has a free Developer plan. Create a project for Python (FastAPI) and one for Next.js, and save both DSNs. It's off by default in the build (Phase 13), so you can skip this.

---

## Step 12 — Secrets worksheet (fill in the password manager, not in git)

| Env variable | Value comes from | dev | prod |
|---|---|---|---|
| `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL` | Supabase → Project Settings → API Keys (Project URL) | ☐ | ☐ |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Publishable / anon key | ☐ | ☐ |
| `SUPABASE_SERVICE_ROLE_KEY` | Secret / service_role key (backend only) | ☐ | ☐ |
| `DATABASE_URL` | Connect → Transaction pooler (6543) | ☐ | ☐ |
| `DATABASE_URL_DIRECT` | Connect → Session pooler / direct (5432), for migrations | ☐ | ☐ |
| `SUPABASE_JWKS_URL` | `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` (Phase 4 confirms) | ☐ | ☐ |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Aura credentials file (prod); dev uses Docker defaults from Phase 1 | — | ☐ |
| `GROQ_API_KEY` | Groq console | ☐ | ☐ |
| `GEMINI_API_KEY` | Google AI Studio | ☐ | ☐ |
| `LLM_PRIMARY_MODEL`, `LLM_FALLBACK_MODEL`, `LLM_JUDGE_MODEL` | Model IDs noted in Steps 6–7 | ☐ | ☐ |
| `EMBEDDING_MODEL`, `EMBEDDING_DIM` | Gemini embedding model ID + its dimension | ☐ | ☐ |
| Google OAuth Client ID / Secret | Google Cloud → Clients (goes into Supabase, not .env) | ☐ | ☐ |
| SMTP host / user / password | Step 10 (goes into Supabase, not .env) | ☐ | ☐ |
| `SENTRY_DSN` (optional) | Sentry | ☐ | ☐ |

In Phase 1, Claude Code creates `apps/api/.env.example` and `apps/web/.env.example`. You copy them to `.env` / `.env.local` and fill in the **dev** column yourself. The **prod** column goes into the Render and Vercel dashboards in Phase 15.

---

## Step 13 — Done? Final checklist

- [ ] All 4 laptops: `git`, `docker run hello-world`, `node -v`, `python3.12 --version`, `uv --version`, `claude --version` all work
- [ ] GitHub org + repo created, all 4 members added, initial commit pushed, `main` protected
- [ ] Supabase `cognexa-dev` + `cognexa-prod`: pgvector on, email auth with confirm, URL config, teammates invited
- [ ] Google OAuth client created with both Supabase callback URLs; Google enabled in both Supabase projects; test users added
- [ ] Neo4j Aura Free running; credentials saved; `RETURN 1` works
- [ ] Groq + Gemini keys created (dev + prod), model IDs and limits noted
- [ ] Vercel + Render accounts connected to GitHub (no projects yet)
- [ ] Custom SMTP planned (required before Phase 15)
- [ ] Secrets worksheet filled in the password manager
- [ ] Phase 0 rows ticked in `progressfile.md` → commit `docs(progress): phase 00 complete`

Next: open Claude Code in the repo folder and paste **Phase 1**.
