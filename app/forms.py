from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, Post, Comment
from django import forms


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Elektron pochta kiriting")

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'avatar', 'bio']
        labels = {
            'username': 'Foydalanuvchi nomi',
            'avatar': 'Profil rasmi',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Parol'
        self.fields['password2'].label = 'Parolni tasdiqlang'


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Foydalanuvchi nomi", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="Parol", widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone_number', 'bio', 'avatar']
        labels = {
            'username': 'Foydalanuvchi nomi',
            'email': 'Elektron pochta',
            'phone_number': 'Telefon raqam',
            'bio': 'Biografiya',
            'avatar': 'Profil rasmi',
        }

        widgets = {
            'username': forms.TextInput(attrs={
                "class": "form-control"
            }),
            'email': forms.EmailInput(attrs={
                "class": "form-control"
            }),
            'phone_number': forms.TextInput(attrs={
                "class": "form-control"
            }),
            'bio': forms.Textarea(attrs={
                "class": "form-control"
            }),
            'avatar': forms.FileInput(attrs={
                "class": "form-control"
            }),
        }


class PostCreateForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'desc', 'img', 'video']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sarlavha (ixtiyoriy)'}),
            'desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Fikringizni yozing...'}),
            'img': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'video': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.TextInput(attrs={
                'class': 'form-control form-control-sm', 
                'placeholder': 'Fikringizni qoldiring...'
            }),
        }