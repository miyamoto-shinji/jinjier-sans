# Security and CDN deployment

## Release integrity

- Verify `SHA256SUMS` before installing desktop or Web font files.
- Publish immutable, versioned paths such as `/jinjer-sans/1.0.0/`; never overwrite a released URL.
- Keep `jinjer-sans.css` and its relative `w/` directory together.

## HTTP response headers

The release includes `specimen/_headers` for hosts that support the common static `_headers` format. For other CDNs, configure the equivalent response headers at the edge:

```text
Content-Security-Policy: default-src 'self'; base-uri 'none'; connect-src 'none'; font-src 'self'; form-action 'none'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'
Permissions-Policy: camera=(), geolocation=(), microphone=(), payment=(), usb=()
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

Serve CSS as `text/css`, WOFF2 as `font/woff2`, and TTF as `font/ttf`. Restrict `Access-Control-Allow-Origin` to approved product and corporate origins when operationally possible.

## Repository controls

- Changes to `main` must use a pull request and pass the required CI check.
- GitHub Actions must use full commit SHAs and minimum token permissions.
- Dependabot, secret scanning with push protection, and CodeQL must remain enabled.
