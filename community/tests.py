from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django_ratelimit.exceptions import Ratelimited
from community.models import CommunityPost, Comment
from culer.sanitizers import sanitize_plain_text, sanitize_rich_text
from culer.middleware import RatelimitMiddleware


class XSSSanitizationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testbarcafan', password='testpassword123')

    def test_sanitize_plain_text_strips_all_html(self):
        malicious = "<script>alert('XSS')</script><b>Hello Barça!</b>"
        cleaned = sanitize_plain_text(malicious)
        self.assertNotIn('<script>', cleaned)
        self.assertNotIn('alert', cleaned)
        self.assertNotIn('<b>', cleaned)
        self.assertEqual(cleaned, 'Hello Barça!')

    def test_sanitize_rich_text_strips_scripts_and_event_handlers(self):
        malicious = (
            "<p>Great match!</p>"
            "<script>document.cookie</script>"
            "<img src='x' onerror='alert(1)'>"
            "<b style='color:red;'>Visca el Barça</b>"
            "<i>Mes que un club</i>"
            "<a href='javascript:alert(1)'>Click me</a>"
        )
        cleaned = sanitize_rich_text(malicious)
        self.assertNotIn('<script>', cleaned)
        self.assertNotIn('onerror', cleaned)
        self.assertNotIn('document.cookie', cleaned)
        self.assertNotIn('style=', cleaned)
        self.assertNotIn('javascript:', cleaned)
        self.assertIn('<p>Great match!</p>', cleaned)
        self.assertIn('<b>Visca el Barça</b>', cleaned)
        self.assertIn('<i>Mes que un club</i>', cleaned)

    def test_community_post_model_sanitizes_on_save(self):
        post = CommunityPost.objects.create(
            title="<script>alert('hacked')</script>Title with <b>HTML</b>",
            content="<p>Safe paragraph</p><script>alert('xss')</script><img src=x onerror=alert(1)>",
            author=self.user
        )
        # Title is plain text - stripped of all tags
        self.assertNotIn('<script>', post.title)
        self.assertNotIn('<b>', post.title)
        self.assertEqual(post.title, 'Title with HTML')

        # Content is rich text - safe tags kept, script/onerror stripped
        self.assertNotIn('<script>', post.content)
        self.assertNotIn('onerror', post.content)
        self.assertIn('<p>Safe paragraph</p>', post.content)

    def test_comment_model_sanitizes_on_save(self):
        post = CommunityPost.objects.create(
            title="Discussion Post",
            content="<p>Discussion content</p>",
            author=self.user
        )
        comment = Comment.objects.create(
            post=post,
            name="<script>alert('author')</script>Fan123",
            content="<script>evil()</script><b>Força Barça!</b>",
            author=self.user
        )
        self.assertNotIn('<script>', comment.name)
        self.assertEqual(comment.name, 'Fan123')
        self.assertNotIn('<script>', comment.content)
        self.assertIn('<b>Força Barça!</b>', comment.content)

    def test_post_creation_view_sanitization(self):
        self.client.login(username='testbarcafan', password='testpassword123')
        response = self.client.post(reverse('community:post_create'), {
            'title': '<script>alert("pwnd")</script>Match Preview',
            'content': '<p>Here is preview</p><script>alert("xss")</script>'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        created_post = CommunityPost.objects.latest('id')
        self.assertEqual(created_post.title, 'Match Preview')
        self.assertNotIn('<script>', created_post.content)
        self.assertIn('<p>Here is preview</p>', created_post.content)

    def test_comment_submission_view_sanitization(self):
        post = CommunityPost.objects.create(
            title="Comment Test Post",
            content="<p>Content</p>",
            author=self.user
        )
        response = self.client.post(reverse('community:add_comment', kwargs={'pk': post.pk}), {
            'name': '<script>alert(1)</script>Inigo',
            'content': '<b>Viva Pedri!</b><script>alert("xss")</script>'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        latest_comment = Comment.objects.latest('id')
        self.assertEqual(latest_comment.name, 'Inigo')
        self.assertNotIn('<script>', latest_comment.content)
        self.assertIn('<b>Viva Pedri!</b>', latest_comment.content)


class RateLimitingAndMiddlewareTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ratelimituser', password='password123')
        self.post = CommunityPost.objects.create(
            title="Rate limit test post",
            content="<p>Test content</p>",
            author=self.user
        )

    def test_ratelimit_middleware_returns_429_on_ratelimited_exception(self):
        middleware = RatelimitMiddleware(get_response=lambda r: None)
        request = Client().get('/').wsgi_request
        exception = Ratelimited()
        response = middleware.process_exception(request, exception)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"429 - Too Many Requests", response.content)

    def test_ratelimit_middleware_returns_json_for_ajax_or_json_request(self):
        middleware = RatelimitMiddleware(get_response=lambda r: None)
        request = Client().get('/', HTTP_ACCEPT='application/json').wsgi_request
        exception = Ratelimited()
        response = middleware.process_exception(request, exception)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"Too Many Requests", response.content)
