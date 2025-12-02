from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Post, Message

# ---------------------- SIGNUP FORM ----------------------
class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "profile_image", "bio")


# ---------------------- POST FORM ----------------------
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("image", "caption")
        widgets = {
            "caption": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Write a caption...",
                "class": "caption-input"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get("image")
        caption = cleaned_data.get("caption")

        # Ensure either image or caption is provided
        if not image and not caption:
            raise forms.ValidationError("You must provide an image or a caption.")
        return cleaned_data


# ---------------------- MESSAGE FORM ----------------------
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("content", "image", "audio")
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Type your message..."
            }),
        }
