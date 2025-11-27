from django.urls import path
from . import views

urlpatterns = [
    # Main Feed
    path("", views.feed, name="feed"),

    # Auth
    path("signup/", views.signup, name="signup"),

    # Posts
    path("create/", views.create_post, name="create_post"),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),

    # Profiles
    path("profile/<str:username>/", views.profile, name="profile"),
    path("follow/<str:username>/", views.follow_toggle, name="follow_toggle"),

    # Chat
    path("chat/<str:username>/", views.chat_room, name="chat_room"),
    path("send-message/<str:username>/", views.send_message, name="send_message"),
    path("delete-message/<int:message_id>/<str:action>/", 
         views.delete_message, name="delete_message"),
]
