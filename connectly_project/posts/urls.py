from django.urls import path
from .views import UserListCreate, PostListCreate, CommentListCreate
from rest_framework_simplejwt.views import (TokenRefreshView, TokenObtainPairView)
from .views import ProtectedView, NewsFeedView

urlpatterns = [
    path('users/', UserListCreate.as_view(), name='user-list-create'),
    path('', PostListCreate.as_view()),
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('protected/', ProtectedView.as_view(), name='protected-view'),
    path('feed/', NewsFeedView.as_view(), name='news-feed'),
]


# from django.urls import path
# from . import views

# urlpatterns = [
#     path('users/', views.get_users, name='get_users'),
#     path('users/create/', views.create_user, name='create_user'),
#     path('users/update/<int:id>/', views.update_user, name='update_user'),
#     path('users/delete/<int:id>/', views.delete_user, name='delete_user'),
# ]