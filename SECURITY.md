# Security Policy

## Supported Versions

This project is actively maintained. The latest version should be used.

| Version | Supported          |
| ------- | ------------------ |
| latest  | ✅                |

## Reporting a Vulnerability

We take the security of this project seriously. If you believe you have found a security vulnerability, please report it to us promptly.

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please open a **private security advisory** on GitHub:

1. Go to the [Security Advisories page](https://github.com/peva3/SmarterRouter/security/advisories) (you'll need to be logged in)
2. Click "New draft security advisory"
3. Fill in the details about the vulnerability
4. Our team will review and respond within 48 hours

We follow a **90-day disclosure policy**. Once a vulnerability is reported:
- We will acknowledge receipt within 48 hours
- We will work to validate and patch the issue
- We will coordinate public disclosure after a fix is ready
- We will credit the reporter (if desired) in the changelog

## Security Best Practices

When using this project:

1. **Keep dependencies updated** - Regularly run `pip install --upgrade` in your environment
2. **Use secret management** - Do not hardcode API keys; use environment variables or secret managers
3. **Run in isolated environment** - The Docker container should have minimal privileges
4. **Monitor logs** - Check for unusual activity or errors
5. **Validate database integrity** - Use `python -m router.provider_db.cli health` to check for corruption

## Known Limitations

- The builder makes HTTP requests to public benchmark sites. Rate limiting is in place but may be adjusted based on source requirements.
- No authentication is required to access the database file; treat it as public data.
- The database contains aggregated benchmark scores only; no sensitive user data is stored.

## Credits

We thank the security researchers who have responsibly disclosed vulnerabilities to us.
