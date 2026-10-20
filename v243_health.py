"""Read-only provider state tracking for Control Center's live dashboard.

READY means uncontacted, not proven operational. A HTTP 200 is *not* an
accepted lyrics match; only verified 'LRC_FOUND' counts as a verified save.
"""
from __future__ import annotations
from datetime import datetime
import re

_LINE = re.compile(r'^\s*([A-Za-z][A-Za-z0-9_+ -]{0,45}):\s*([A-Z][A-Z0-9_]+)\s*\|\s*(.*?)\s*\|', re.ASCII)

class ProviderHealth:
    STATES = {'LRC_FOUND': 'Lyrics returned (not yet saved)', 'LRC_INSTALLED': 'Verified LRC saved', 'NO_MATCH': 'Working (no match)',
              'REVIEW_AVAILABLE': 'Working (review)',
              'TIMEOUT': 'Timed out', 'TEMPORARY_HTTP_503': 'Temporarily unavailable',
              'ERROR': 'Error', 'UNEXPECTED_ERROR': 'Error',
              'SKIPPED': 'Skipped / recovering', 'UNAVAILABLE': 'Unavailable',
              'HTTP_429_DISABLED': 'Blocked / rate limited',
              'CACHED_NO_MATCH': 'Cached (not contacted)',
              'ONLINE_BLOCKED_OFFLINE_CHECKED': 'Blocked (offline checked)',
              'LRC_FOUND_OFFLINE': 'Working (offline match)'}

    def __init__(self, providers=()):
        self.rows = {name: {'status': 'Not contacted', 'last_verified': '',
                            'last_event': '', 'last_http_success': '', 'detail': '', 'verified_count': 0}
                     for name in providers}

    def observe(self, line, now=None):
        match = _LINE.match(line)
        if not match:
            return None
        name, code, detail = match.groups()
        if code not in self.STATES or name not in self.rows:
            return None
        row = self.rows[name]
        row['status'] = self.STATES[code]
        row['last_event'] = now or datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
        row['detail'] = detail[:160]
        if re.search(r'\bHTTP 2\d\d\b', line):
            row['last_http_success'] = row['last_event']
        if code=='LRC_INSTALLED':
            row['last_verified'] = row['last_event']
            row['verified_count'] += 1
        return name
