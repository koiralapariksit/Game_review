"""
Middleware for culer project.
Catches Ratelimited exceptions and returns a clean HTTP 429 Too Many Requests response.
"""
from django.http import HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django_ratelimit.exceptions import Ratelimited


class RatelimitMiddleware(MiddlewareMixin):
    """
    Catches Ratelimited exception from django-ratelimit and returns
    an HTTP 429 Too Many Requests response.
    """
    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            accept_header = request.headers.get('accept', '')
            if 'application/json' in accept_header or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'Too Many Requests',
                    'detail': 'Rate limit exceeded. Please try again later.'
                }, status=429)

            html_content = (
                "<!DOCTYPE html>"
                "<html><head><title>429 Too Many Requests</title>"
                "<style>"
                "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; "
                "text-align: center; padding: 100px 20px; background: #0f172a; color: #f8fafc; }"
                "h1 { font-size: 3rem; margin-bottom: 1rem; color: #ef4444; }"
                "p { font-size: 1.25rem; color: #94a3b8; max-width: 500px; margin: 0 auto 2rem; }"
                "a { color: #38bdf8; text-decoration: none; font-weight: 500; }"
                "a:hover { text-decoration: underline; }"
                "</style></head>"
                "<body>"
                "<h1>429 - Too Many Requests</h1>"
                "<p>You have made too many requests in a short period. Please wait a moment and try again.</p>"
                "<a href='/'>&larr; Return to Homepage</a>"
                "</body></html>"
            )
            return HttpResponse(html_content, status=429, content_type='text/html')
        return None

