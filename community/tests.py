from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError
from django.utils import timezone
from django_ratelimit.exceptions import Ratelimited

from community.models import CommunityPost, Comment, Reaction, ContentReport
from matches.models import Competition, Team, Match
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
            'content': '<p>Here is preview</p><script>alert("xss")</script>',
            'category': CommunityPost.CATEGORY_MATCH_DISCUSSION,
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


class CommunityModerationAndReactionsTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='culer1', password='password123')
        self.user2 = User.objects.create_user(username='culer2', password='password123')
        self.user3 = User.objects.create_user(username='culer3', password='password123')
        self.staff_user = User.objects.create_user(username='staffmod', password='adminpassword', is_staff=True)

        self.post = CommunityPost.objects.create(
            title="Tactical High Defensive Line Analysis",
            content="<p>An in-depth debate on tactical offside traps.</p>",
            category=CommunityPost.CATEGORY_TACTICAL_DEBATE,
            author=self.user1,
            moderation_status=CommunityPost.MODERATION_STATUS_ACTIVE
        )

        self.comp = Competition.objects.create(name="La Liga", code="PD")
        self.barca = Team.objects.create(name="FC Barcelona", short_name="Barça", tla="FCB", provider_id=81)
        self.madrid = Team.objects.create(name="Real Madrid CF", short_name="Real Madrid", tla="RMA", provider_id=86)
        self.match = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=self.madrid,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            match_date=timezone.now()
        )

    def test_duplicate_reactions_by_same_user_prevented(self):
        """UniqueConstraint on [post, user, reaction_type] blocks duplicate DB records."""
        Reaction.objects.create(
            post=self.post,
            user=self.user1,
            reaction_type=Reaction.TYPE_UPVOTE
        )
        with self.assertRaises(IntegrityError):
            Reaction.objects.create(
                post=self.post,
                user=self.user1,
                reaction_type=Reaction.TYPE_UPVOTE
            )

    def test_toggle_reaction_endpoint(self):
        """toggle_reaction adds reaction on first click and removes it on second click."""
        self.client.login(username='culer1', password='password123')
        url = reverse('community:toggle_reaction', kwargs={'post_id': self.post.id})

        # 1. Toggle ON
        res1 = self.client.post(url, {'reaction_type': 'UPVOTE'}, HTTP_HX_REQUEST='true')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(self.post.reactions.filter(reaction_type='UPVOTE').count(), 1)
        self.assertContains(res1, 'active')

        # 2. Toggle OFF
        res2 = self.client.post(url, {'reaction_type': 'UPVOTE'}, HTTP_HX_REQUEST='true')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(self.post.reactions.filter(reaction_type='UPVOTE').count(), 0)

    def test_three_user_reports_automatically_flags_post(self):
        """Receiving 3 unresolved user reports transitions moderation_status to FLAGGED."""
        self.assertEqual(self.post.moderation_status, CommunityPost.MODERATION_STATUS_ACTIVE)

        # User 1 reports
        self.client.login(username='culer1', password='password123')
        self.client.post(reverse('community:report_content', kwargs={'post_id': self.post.id}), {
            'reason': 'SPAM',
            'details': 'Spam post 1'
        })
        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_status, CommunityPost.MODERATION_STATUS_ACTIVE)

        # User 2 reports
        self.client.login(username='culer2', password='password123')
        self.client.post(reverse('community:report_content', kwargs={'post_id': self.post.id}), {
            'reason': 'ABUSE',
            'details': 'Harassment'
        })
        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_status, CommunityPost.MODERATION_STATUS_ACTIVE)

        # User 3 reports -> threshold reached!
        self.client.login(username='culer3', password='password123')
        self.client.post(reverse('community:report_content', kwargs={'post_id': self.post.id}), {
            'reason': 'MISINFORMATION',
            'details': 'False injury rumor'
        })
        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_status, CommunityPost.MODERATION_STATUS_FLAGGED)
        self.assertEqual(self.post.reports.count(), 3)

    def test_hidden_posts_do_not_appear_in_public_community_feeds(self):
        """Posts with moderation_status='HIDDEN' must not render in post_list or match detail."""
        hidden_post = CommunityPost.objects.create(
            title="Banned Harmful Content",
            content="<p>This should never be seen.</p>",
            author=self.user2,
            moderation_status=CommunityPost.MODERATION_STATUS_HIDDEN,
            is_published=True
        )

        response = self.client.get(reverse('community:post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.post, response.context['page_obj'])
        self.assertNotIn(hidden_post, response.context['page_obj'])
        self.assertContains(response, self.post.title)
        self.assertNotContains(response, hidden_post.title)

        # Detail view returns 404 for regular users
        detail_res = self.client.get(reverse('community:post_detail', kwargs={'pk': hidden_post.pk}))
        self.assertEqual(detail_res.status_code, 404)

    def test_locked_post_prevents_new_comments(self):
        """When is_locked=True, further comments cannot be submitted."""
        self.post.is_locked = True
        self.post.save()

        res = self.client.post(reverse('community:add_comment', kwargs={'pk': self.post.pk}), {
            'name': 'Fan',
            'content': 'Attempted comment on locked thread'
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.post.comments.count(), 0)
        self.assertContains(res, 'locked')

    def test_match_detail_embeds_match_discussion_threads(self):
        """Match detail page renders linked supporter discussion threads."""
        match_post = CommunityPost.objects.create(
            title="Spotify Camp Nou Tactical Review Discussion",
            content="<p>Discuss the pressing and xG of this Clásico.</p>",
            category=CommunityPost.CATEGORY_MATCH_DISCUSSION,
            related_match=self.match,
            author=self.user1
        )

        res = self.client.get(reverse('matches:match_detail', kwargs={'match_id': self.match.id}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Match Discussion Threads")
        self.assertContains(res, match_post.title)

    def test_staff_moderation_actions_in_customadmin(self):
        """Staff admins can 1-click approve, hide, lock, or delete flagged posts."""
        self.client.login(username='staffmod', password='adminpassword')
        self.post.moderation_status = CommunityPost.MODERATION_STATUS_FLAGGED
        self.post.save()

        mod_url = reverse('customadmin:moderate_post', kwargs={'post_id': self.post.id})

        # 1. Hide post
        self.client.post(mod_url, {'action': 'hide'})
        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_status, CommunityPost.MODERATION_STATUS_HIDDEN)

        # 2. Approve post
        self.client.post(mod_url, {'action': 'approve'})
        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_status, CommunityPost.MODERATION_STATUS_ACTIVE)

        # 3. Lock post
        self.client.post(mod_url, {'action': 'lock'})
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_locked)

        # 4. Delete post
        self.client.post(mod_url, {'action': 'delete'})
        self.assertFalse(CommunityPost.objects.filter(id=self.post.id).exists())


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
