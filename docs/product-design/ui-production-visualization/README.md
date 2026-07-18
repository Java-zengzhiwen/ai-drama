# UI Baseline Production Visualization

This directory is the review package for applying the frozen M1–M3 Product Design baseline to the real React frontend. M6D is included only as an adjacent, already-implemented management surface whose visual tokens were aligned with the same shell.

The sprint changed frontend presentation, responsive composition, accessibility semantics, and frontend tests. It did not change backend contracts, database schema, migrations, providers, pollers, credentials, or real generation behavior.

## Review order

1. `current-frontend-audit.md`
2. `route-and-screen-coverage.md`
3. `api-and-mock-boundary.md`
4. `design-fidelity-report.md`
5. `responsive-qa.md`
6. `accessibility-qa.md`
7. `test-and-verification-report.md`
8. `final-handoff.md`

The `assets/` directory contains 17 production, responsive, drawer, and source-versus-production screenshots. The four `comparison-*-source-vs-production.png` files are the fastest visual review entry points.

## Runtime used for manual review

- Frontend: `http://127.0.0.1:15174`
- API boundary: local loopback backend proxied through `/api`
- Real provider requests: none

No commit or push was performed.
