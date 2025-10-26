# Security Policy

## Supported Versions

Currently supported versions with security updates:

| Version | Supported          |
| ------- | ----------------- |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security bugs seriously. We appreciate your efforts to responsibly disclose your findings.

To report a security issue, email sp22-bcs-003@cuivehari.edu.pk and include:

1. Type of issue (e.g. buffer overflow, SQL injection, or cross-site scripting)
2. Full paths of source file(s) related to the manifestation of the issue
3. The location of the affected source code (tag/branch/commit or direct URL)
4. Any special configuration required to reproduce the issue
5. Step-by-step instructions to reproduce the issue
6. Proof-of-concept or exploit code (if possible)
7. Impact of the issue, including how an attacker might exploit it

We'll respond within 48 hours with next steps.

## Security Features

PhotoVault implements several security measures:

1. **Authentication**
   - JWT-based authentication
   - Session management
   - Password hashing with strong algorithms

2. **Data Protection**
   - Encrypted storage
   - Secure file handling
   - CORS protection

3. **Sharing Security**
   - One-time passwords
   - Time-limited access
   - QR code verification

4. **Infrastructure**
   - HTTPS enforced
   - Security headers
   - Rate limiting

## Best Practices

When contributing, please ensure:

1. All passwords are hashed
2. User input is sanitized
3. File uploads are validated
4. API endpoints are protected
5. Dependencies are up to date