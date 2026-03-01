"""Checks whether the site is secure against common attacks."""

"""
1. HTTPS / SSL -> Check valid HTTPS certificate.
2. Security Headers -> HSTS, CSP, X-Frame-Options,
                    X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
3. Cookies -> HttpOnly, Secure, SameSite attributes.
4. Mixed Content -> Detect HTTP resources on HTTPS page.
5. Basic Vulnerabilities -> Look for exposed forms, inline scripts, etc.
"""
