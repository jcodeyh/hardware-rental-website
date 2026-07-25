# my-app (frontend)

Minimal React frontend: Login page (with a Sign up link/page) + a protected Dashboard placeholder.

## Run it

```bash
npm install
npm run dev
```

Opens at http://localhost:5173. It expects a backend at http://localhost:8000
(see vite.config.js — /api calls are proxied there in dev).

## Structure

```
my-app/
  index.html
  vite.config.js
  package.json
  src/
    main.jsx            # React entry point
    App.jsx             # Routes: /login, /signup, /dashboard
    index.css            # Bare-bones global styles
    context/
      AuthContext.jsx    # Holds token in state + localStorage, login()/logout()
    api/
      api.js              # fetch wrappers for /api/auth/login, /api/auth/signup
    components/
      ProtectedRoute.jsx  # Redirects to /login if not authenticated
    pages/
      Login.jsx
      Signup.jsx
      Dashboard.jsx       # placeholder — add real content later
```

## Backend contract (whatever Python framework you use — Flask/FastAPI)

- `POST /api/auth/login`  { email, password } -> { token }
- `POST /api/auth/signup` { email, password } -> { token }

Any error should return a JSON body with a `detail` or `message` field and a
non-2xx status code; the frontend reads that and shows it under the form.

## Adding more pages later

1. Create a new file in `src/pages/`.
2. Add a `<Route>` for it in `App.jsx` (wrap in `<ProtectedRoute>` if it
   requires login).
3. If it needs backend data, add a function in `src/api/api.js`.
