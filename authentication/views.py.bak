"""
OAuth authentication views.

Provides views for OAuth authorization and callback handling.
"""
import secrets
import logging
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.core.cache import cache
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount
from tenants.models import Tenant, TenantUser
from api.models import Project

logger = logging.getLogger(__name__)

# State expiration time (5 minutes)
STATE_EXPIRATION = 300


class OAuthBaseView(APIView):
    """Base class for OAuth views.

    Provides common functionality for OAuth authorization and callback handling.
    """

    permission_classes = [AllowAny]

    def generate_state(self) -> str:
        """Generate a secure state parameter for CSRF protection.

        Returns:
            `str`:
                A secure random state token.
        """
        state = secrets.token_urlsafe(32)
        cache.set(f"oauth_state:{state}", "valid", STATE_EXPIRATION)
        return state

    def validate_state(self, state: str) -> bool:
        """Validate the state parameter.

        Args:
            state (`str`):
                The state parameter from the callback.

        Returns:
            `bool`:
                True if the state is valid, False otherwise.
        """
        if not state:
            return False
        key = f"oauth_state:{state}"
        if cache.get(key):
            cache.delete(key)
            return True
        return False

    def get_or_create_user(
        self,
        provider: str,
        provider_uid: str,
        user_info: dict
    ) -> tuple:
        """Get existing user or create new user from social account.

        Args:
            provider (`str`):
                The OAuth provider name.
            provider_uid (`str`):
                The unique user ID from the provider.
            user_info (`dict`):
                User information from the provider.

        Returns:
            `tuple`:
                (user, social_account, is_new_user)
        """
        # Check if social account exists
        try:
            social_account = SocialAccount.objects.select_related('user').get(
                provider=provider,
                provider_uid=provider_uid
            )
            return social_account.user, social_account, False
        except SocialAccount.DoesNotExist:
            pass

        # Check for WeChat union_id matching
        union_id = user_info.get('unionid')
        if union_id and provider == SocialAccount.Provider.WECHAT:
            try:
                social_account = SocialAccount.objects.select_related('user').get(
                    provider=provider,
                    union_id=union_id
                )
                # Update provider_uid if different
                if social_account.provider_uid != provider_uid:
                    social_account.provider_uid = provider_uid
                    social_account.save(update_fields=['provider_uid', 'updated_at'])
                return social_account.user, social_account, False
            except SocialAccount.DoesNotExist:
                pass

        # Create new user and social account
        with transaction.atomic():
            # Generate unique username
            base_username = self._get_username_from_info(user_info, provider)
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            # Create user
            user = User.objects.create_user(
                username=username,
                email=user_info.get('email') or '',
                first_name=(user_info.get('name') or user_info.get('nickname') or '')[:30],
            )

            # Create social account
            social_account = SocialAccount.objects.create(
                user=user,
                provider=provider,
                provider_uid=provider_uid,
                union_id=union_id,
                extra_data=user_info,
            )

            # Create default tenant for new user
            tenant = Tenant.objects.create(
                name=f"{username}'s Workspace",
                slug=username.lower().replace(' ', '-').replace('_', '-')[:50],
            )
            TenantUser.objects.create(
                tenant=tenant,
                user=user,
                role=TenantUser.Role.OWNER,
            )

            # Create default project for new user
            Project.objects.create(
                tenant=tenant,
                name="My First Project",
                description="Welcome to your first project!",
                status=Project.Status.DRAFT,
            )

            logger.info(
                f"Created new user via OAuth: provider={provider}, "
                f"user_id={user.id}, username={username}"
            )

            return user, social_account, True

    def _get_username_from_info(self, user_info: dict, provider: str) -> str:
        """Extract username from user info.

        Args:
            user_info (`dict`):
                User information from the provider.
            provider (`str`):
                The OAuth provider name.

        Returns:
            `str`:
                A suitable username.
        """
        # Try different fields based on provider
        if provider == SocialAccount.Provider.GITHUB:
            return user_info.get('login', 'github_user')
        elif provider == SocialAccount.Provider.WECHAT:
            nickname = user_info.get('nickname', 'wechat_user')
            # WeChat nicknames may contain special characters
            return ''.join(c for c in nickname if c.isalnum() or c == '_')[:30] or 'wechat_user'
        elif provider == SocialAccount.Provider.QQ:
            nickname = user_info.get('nickname', 'qq_user')
            return ''.join(c for c in nickname if c.isalnum() or c == '_')[:30] or 'qq_user'
        return 'user'

    def get_tokens(self, user: User) -> dict:
        """Generate JWT tokens for user.

        Args:
            user (`User`):
                The Django user.

        Returns:
            `dict`:
                Dictionary containing access and refresh tokens.
        """
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class GitHubAuthorizeView(OAuthBaseView):
    """Get GitHub OAuth authorization URL."""

    def get(self, request):
        """Get GitHub authorization URL.

        Returns:
            Response with auth_url and state.
        """
        if not settings.GITHUB_CLIENT_ID:
            return Response(
                {'error': 'GitHub OAuth not configured'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        state = self.generate_state()
        params = {
            'client_id': settings.GITHUB_CLIENT_ID,
            'redirect_uri': settings.GITHUB_REDIRECT_URI,
            'scope': 'user:email read:user',
            'state': state,
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"

        return Response({
            'auth_url': auth_url,
            'state': state,
        })


class GitHubCallbackView(OAuthBaseView):
    """Handle GitHub OAuth callback."""

    def get(self, request):
        """Handle GitHub OAuth callback.

        Exchanges authorization code for access token and creates/retrieves user.

        Returns:
            Response with JWT tokens and user info.
        """
        code = request.query_params.get('code')
        state = request.query_params.get('state')

        if not code:
            return Response(
                {'error': 'Authorization code not provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not self.validate_state(state):
            return Response(
                {'error': 'Invalid or expired state parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Exchange code for access token
            token_response = requests.post(
                'https://github.com/login/oauth/access_token',
                data={
                    'client_id': settings.GITHUB_CLIENT_ID,
                    'client_secret': settings.GITHUB_CLIENT_SECRET,
                    'code': code,
                    'redirect_uri': settings.GITHUB_REDIRECT_URI,
                },
                headers={'Accept': 'application/json'},
                timeout=10,
            )
            token_data = token_response.json()

            if 'error' in token_data:
                logger.warning(f"GitHub token exchange failed: {token_data}")
                return Response(
                    {'error': token_data.get('error_description', 'Token exchange failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            access_token = token_data['access_token']

            # Get user info
            user_response = requests.get(
                'https://api.github.com/user',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json',
                },
                timeout=10,
            )
            user_info = user_response.json()

            # Get or create user
            user, social_account, is_new = self.get_or_create_user(
                provider=SocialAccount.Provider.GITHUB,
                provider_uid=str(user_info['id']),
                user_info=user_info,
            )

            # Update access token
            social_account.access_token = access_token
            social_account.save(update_fields=['access_token', 'updated_at'])

            # Generate JWT tokens
            tokens = self.get_tokens(user)

            return Response({
                'tokens': tokens,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
                'is_new_user': is_new,
            })

        except requests.RequestException as e:
            logger.error(f"GitHub OAuth request failed: {e}")
            return Response(
                {'error': 'Failed to communicate with GitHub'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.exception(f"GitHub OAuth unexpected error: {e}")
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WeChatAuthorizeView(OAuthBaseView):
    """Get WeChat OAuth authorization URL."""

    def get(self, request):
        """Get WeChat authorization URL.

        Returns:
            Response with auth_url and state.
        """
        if not settings.WECHAT_APP_ID:
            return Response(
                {'error': 'WeChat OAuth not configured'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        state = self.generate_state()
        params = {
            'appid': settings.WECHAT_APP_ID,
            'redirect_uri': settings.WECHAT_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'snsapi_login',
            'state': state,
        }
        auth_url = f"https://open.weixin.qq.com/connect/qrconnect?{urlencode(params)}#wechat_redirect"

        return Response({
            'auth_url': auth_url,
            'state': state,
        })


class WeChatCallbackView(OAuthBaseView):
    """Handle WeChat OAuth callback."""

    def get(self, request):
        """Handle WeChat OAuth callback.

        Exchanges authorization code for access token and creates/retrieves user.

        Returns:
            Response with JWT tokens and user info.
        """
        code = request.query_params.get('code')
        state = request.query_params.get('state')

        if not code:
            return Response(
                {'error': 'Authorization code not provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not self.validate_state(state):
            return Response(
                {'error': 'Invalid or expired state parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Exchange code for access token
            token_response = requests.get(
                'https://api.weixin.qq.com/sns/oauth2/access_token',
                params={
                    'appid': settings.WECHAT_APP_ID,
                    'secret': settings.WECHAT_APP_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                },
                timeout=10,
            )
            token_data = token_response.json()

            if 'errcode' in token_data:
                logger.warning(f"WeChat token exchange failed: {token_data}")
                return Response(
                    {'error': token_data.get('errmsg', 'Token exchange failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            access_token = token_data['access_token']
            openid = token_data['openid']
            unionid = token_data.get('unionid')

            # Get user info
            user_response = requests.get(
                'https://api.weixin.qq.com/sns/userinfo',
                params={
                    'access_token': access_token,
                    'openid': openid,
                },
                timeout=10,
            )
            user_info = user_response.json()
            user_info['unionid'] = unionid

            # Use unionid if available, otherwise openid
            provider_uid = unionid or openid

            # Get or create user
            user, social_account, is_new = self.get_or_create_user(
                provider=SocialAccount.Provider.WECHAT,
                provider_uid=provider_uid,
                user_info=user_info,
            )

            # Update tokens
            social_account.access_token = access_token
            social_account.refresh_token = token_data.get('refresh_token')
            social_account.save(update_fields=['access_token', 'refresh_token', 'updated_at'])

            tokens = self.get_tokens(user)

            return Response({
                'tokens': tokens,
                'user': {
                    'id': user.id,
                    'username': user.username,
                },
                'is_new_user': is_new,
            })

        except requests.RequestException as e:
            logger.error(f"WeChat OAuth request failed: {e}")
            return Response(
                {'error': 'Failed to communicate with WeChat'},
                status=status.HTTP_502_BAD_GATEWAY
            )


class QQAuthorizeView(OAuthBaseView):
    """Get QQ OAuth authorization URL."""

    def get(self, request):
        """Get QQ authorization URL.

        Returns:
            Response with auth_url and state.
        """
        if not settings.QQ_APP_ID:
            return Response(
                {'error': 'QQ OAuth not configured'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        state = self.generate_state()
        params = {
            'client_id': settings.QQ_APP_ID,
            'redirect_uri': settings.QQ_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'get_user_info',
            'state': state,
        }
        auth_url = f"https://graph.qq.com/oauth2.0/authorize?{urlencode(params)}"

        return Response({
            'auth_url': auth_url,
            'state': state,
        })


class QQCallbackView(OAuthBaseView):
    """Handle QQ OAuth callback."""

    def get(self, request):
        """Handle QQ OAuth callback.

        Exchanges authorization code for access token and creates/retrieves user.

        Returns:
            Response with JWT tokens and user info.
        """
        code = request.query_params.get('code')
        state = request.query_params.get('state')

        if not code:
            return Response(
                {'error': 'Authorization code not provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not self.validate_state(state):
            return Response(
                {'error': 'Invalid or expired state parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Exchange code for access token
            token_response = requests.get(
                'https://graph.qq.com/oauth2.0/token',
                params={
                    'client_id': settings.QQ_APP_ID,
                    'client_secret': settings.QQ_APP_SECRET,
                    'code': code,
                    'redirect_uri': settings.QQ_REDIRECT_URI,
                    'grant_type': 'authorization_code',
                    'fmt': 'json',
                },
                timeout=10,
            )
            token_data = token_response.json()

            if 'error' in token_data:
                logger.warning(f"QQ token exchange failed: {token_data}")
                return Response(
                    {'error': token_data.get('error_description', 'Token exchange failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            access_token = token_data['access_token']

            # Get OpenID
            openid_response = requests.get(
                'https://graph.qq.com/oauth2.0/me',
                params={
                    'access_token': access_token,
                    'fmt': 'json',
                },
                timeout=10,
            )
            openid_data = openid_response.json()
            openid = openid_data['openid']

            # Get user info
            user_response = requests.get(
                'https://graph.qq.com/user/get_user_info',
                params={
                    'access_token': access_token,
                    'oauth_consumer_key': settings.QQ_APP_ID,
                    'openid': openid,
                },
                timeout=10,
            )
            user_info = user_response.json()
            user_info['openid'] = openid

            # Get or create user
            user, social_account, is_new = self.get_or_create_user(
                provider=SocialAccount.Provider.QQ,
                provider_uid=openid,
                user_info=user_info,
            )

            # Update access token
            social_account.access_token = access_token
            social_account.save(update_fields=['access_token', 'updated_at'])

            tokens = self.get_tokens(user)

            return Response({
                'tokens': tokens,
                'user': {
                    'id': user.id,
                    'username': user.username,
                },
                'is_new_user': is_new,
            })

        except requests.RequestException as e:
            logger.error(f"QQ OAuth request failed: {e}")
            return Response(
                {'error': 'Failed to communicate with QQ'},
                status=status.HTTP_502_BAD_GATEWAY
            )


class SocialAccountListView(APIView):
    """List user's bound social accounts."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of social accounts bound to current user.

        Returns:
            List of social account info.
        """
        accounts = SocialAccount.objects.filter(user=request.user)
        data = [
            {
                'provider': account.provider,
                'provider_name': account.get_provider_display(),
                'created_at': account.created_at.isoformat(),
            }
            for account in accounts
        ]
        return Response(data)


class SocialAccountUnbindView(APIView):
    """Unbind social account from user."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, provider):
        """Unbind a social account.

        Args:
            provider: The OAuth provider to unbind.

        Returns:
            Success message or error.
        """
        # Check if this is the only login method
        social_count = SocialAccount.objects.filter(user=request.user).count()
        has_password = request.user.has_usable_password()

        if social_count <= 1 and not has_password:
            return Response(
                {'error': 'Cannot unbind the only login method'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            account = SocialAccount.objects.get(
                user=request.user,
                provider=provider,
            )
            account.delete()
            logger.info(
                f"Unbound social account: provider={provider}, "
                f"user_id={request.user.id}"
            )
            return Response({'message': 'Account unbound successfully'})
        except SocialAccount.DoesNotExist:
            return Response(
                {'error': 'Social account not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PhoneLoginView(APIView):
    """Phone number + verification code login.

    POST /api/v1/auth/phone/login/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Login with phone number and verification code.

        Args:
            phone: Phone number (required)
            code: Verification code (required)

        Returns:
            JWT tokens and user info on success.
        """
        phone = request.data.get('phone', '').strip()
        code = request.data.get('code', '').strip()

        # Validate input
        if not phone or not code:
            return Response(
                {'error': '请填写手机号和验证码'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate phone format (Chinese mobile)
        import re
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return Response(
                {'error': '请输入正确的手机号码'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 测试阶段：138开头手机号 + 验证码202601 直接通过
        # TODO: 正式环境需要对接短信验证码服务
        if phone.startswith('138') and code == '202601':
            # Get or create user by phone
            username = f'phone_{phone}'
            user, is_new = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': phone[-4:],  # 用手机号后4位作为昵称
                }
            )

            # Create tenant and project for new user
            if is_new:
                with transaction.atomic():
                    # 生成唯一的 slug
                    base_slug = f'phone-{phone}'
                    slug = base_slug
                    counter = 1
                    while Tenant.objects.filter(slug=slug).exists():
                        slug = f'{base_slug}-{counter}'
                        counter += 1

                    tenant = Tenant.objects.create(
                        name=f'{phone}的工作空间',
                        slug=slug,
                    )
                    TenantUser.objects.create(
                        tenant=tenant,
                        user=user,
                        role=TenantUser.Role.OWNER,
                    )
                    Project.objects.create(
                        tenant=tenant,
                        name='默认项目',
                        description='自动创建的默认项目',
                    )
                logger.info(f"Created new user via phone login: {phone}")

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            tokens = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }

            return Response({
                'tokens': tokens,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'phone': phone,
                },
                'is_new_user': is_new,
            })
        else:
            return Response(
                {'error': '验证码错误'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class SendVerificationCodeView(APIView):
    """Send verification code to phone.

    POST /api/v1/auth/phone/send-code/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Send verification code to phone number.

        Args:
            phone: Phone number (required)

        Returns:
            Success message.
        """
        phone = request.data.get('phone', '').strip()

        # Validate phone format
        import re
        if not phone or not re.match(r'^1[3-9]\d{9}$', phone):
            return Response(
                {'error': '请输入正确的手机号码'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 测试阶段：不实际发送验证码
        # TODO: 正式环境需要对接短信服务
        logger.info(f"[TEST] Verification code for {phone}: 202601")

        return Response({
            'message': '验证码已发送',
            # 测试阶段返回提示
            'hint': '测试阶段：138开头手机号使用验证码 202601',
        })
