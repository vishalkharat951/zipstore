# Deployment Checklist

## Pre-Deployment

### Environment
- [ ] Generate a strong `SECRET_KEY` via:
      `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] Copy `.env.example` to `.env` and fill all values
- [ ] Set `DEBUG=False`
- [ ] Set `ALLOWED_HOSTS` to your domain(s)
- [ ] `addition of logs/ directory to .gitignore` already done

### Database
- [ ] Run `python manage.py migrate`
- [ ] Run `python manage.py createsuperuser`
- [ ] Load initial data if any (`python manage.py loaddata ...`)
- [ ] Verify stock integrity: no negative stock values
- [ ] Run `python manage.py check --deploy` and fix any warnings

### Static & Media Files
- [ ] Run `python manage.py collectstatic --noinput`
- [ ] Verify WhiteNoise serves static files correctly
- [ ] Set up external media storage (S3, DO Spaces, etc.) or configure nginx/apache to serve `/media/`
- [ ] Set `MEDIA_ROOT` permissions (web server must be able to write)

### PhonePe Payment Gateway
- [ ] Update `PhonePeSettings` in admin with production credentials
- [ ] Set callback URL to `https://yourdomain.com/payments/callback/`
- [ ] Enable `active` toggle
- [ ] Test a transaction in UAT environment first
- [ ] Switch `PHONEPE_ENVIRONMENT` to `production` after UAT sign-off

### Security
- [ ] Enable HTTPS (Let's Encrypt / Cloudflare / AWS ACM)
- [ ] Configure web server to redirect HTTP → HTTPS
- [ ] Set `SECURE_SSL_REDIRECT=True`
- [ ] Ensure `CSRF_COOKIE_SECURE` and `SESSION_COOKIE_SECURE` are `True`
- [ ] Set `X_FRAME_OPTIONS = 'DENY'`
- [ ] Set `SECURE_HSTS_SECONDS` to at least `31536000` after initial SSL validation
- [ ] Set `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] Set `SECURE_BROWSER_XSS_FILTER = True`

### Logging
- [ ] Verify `logs/` directory exists and is writable
- [ ] Configure log rotation (already set up via `RotatingFileHandler`)
- [ ] Set up email for `ADMINS` to receive error notifications

## Deployment

### Application Server
- [ ] Choose WSGI server: `gunicorn` (recommended) or `uwsgi`
- [ ] Run: `gunicorn ecom.wsgi:application --bind 0.0.0.0:8000 --workers 4 --access-logfile - --error-logfile -`
- [ ] Or use a process manager: `supervisor` / `systemd`

### Web Server (reverse proxy)
- [ ] Configure nginx or Caddy to proxy to gunicorn
- [ ] Serve media files directly via web server (or use S3)
- [ ] Example nginx config:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location /static/ {
        alias /path/to/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /path/to/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service (optional)
```ini
[Unit]
Description=Zip Store Django App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/ecom
Environment=DJANGO_SETTINGS_MODULE=ecom.settings.production
ExecStart=/path/to/venv/bin/gunicorn ecom.wsgi:application --workers 4 --bind 127.0.0.1:8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Post-Deployment

### Verification
- [ ] Visit `https://yourdomain.com/` — home page loads
- [ ] Browse products, add to cart, complete checkout
- [ ] Run a test payment (use PhonePe UAT until confident)
- [ ] Verify callback URL works with PhonePe
- [ ] Check `logs/ecom.log` for any errors
- [ ] Verify admin dashboard stats render
- [ ] Run `python manage.py check --deploy` again

### Monitoring
- [ ] Set up uptime monitoring (e.g., UptimeRobot, Pingdom)
- [ ] Set up error tracking (Sentry recommended)
- [ ] Configure database backups (daily cron job)
- [ ] Monitor disk space for logs and media

## Rollback Plan
1. Keep previous release directory on server
2. Symlink `current` → previous if new release fails
3. Restore database from backup if migration caused issues
4. Keep the backup `ecom/settings_old.py.bak` as reference
