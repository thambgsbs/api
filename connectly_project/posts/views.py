import bcrypt
import django_filters.rest_framework
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, filters
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import ListAPIView
from .models import User, Post, Comment, PasswordSingleton, PasswordClass, PasswordFactory
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from django.contrib.auth.hashers import make_password, check_password 
from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


class UserListCreate(APIView):

    def get(self, request):
        # Check if cached data exists
        users = cache.get('all_users')
        
        if not users:
            # If not in cache, fetch from the database and store in cache
            users = User.objects.all()
            cache.set('all_users', users, timeout=60 * 15)  # Cache for 15 minutes
        
        serializer = UserSerializer(users, many=True)
        
        # Log Singleton and Factory output for debugging
        passwordSingleton1 = PasswordSingleton("mypassword123")
        passwordSingleton2 = PasswordSingleton("mypassword1234")
        print('First singleton password is: ', passwordSingleton1.password)
        print('Second singleton password is: ', passwordSingleton2.password)
        print('Are they the same? ', passwordSingleton1 is passwordSingleton1)         

        factory = PasswordFactory()
        factory.register_class('password', PasswordClass)

        firstPassword = factory.create_instance('password', 'mypassword123')
        secondPassword = factory.create_instance('password', 'mypassword123456')
        print('First password from factory is: ', firstPassword.password)
        print('Second password from factory is: ', secondPassword.password)
        print('Are they the same? ', firstPassword is secondPassword)
        
        hashed_password = make_password("mypassword123")
        #print(hashed_password)  # Outputs a hashed version of the password


        # Verifying the hashed password
        isPasswordValid = check_password("mypassword123", hashed_password)
        print('Is the password valid? ', isPasswordValid)  # Outputs True if the password matches

        #Salting
        password = b'password1234'
        salt = bcrypt.gensalt()
        #hashWithSaltPassword = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        hashWithSaltPassword = bcrypt.hashpw(password, salt)
        print('Hash with salt password is: ', hashWithSaltPassword)
        # Verify a password
        passwordToVerify = b'password1234'

        # if bcrypt.checkpw(passwordToVerify, hashWithSaltPassword):
        #     print("Password is correct")
        # else:
        #     print("Invalid password")

        return Response(serializer.data)


    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostListCreate(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['id', 'content']
    search_fields = ['id', 'content']
    ordering_fields = ['id', 'content', 'created_at']

    def perform_create(self, serializer):
        # Automatically assign the current user as the author of the post
        serializer.save(author=self.request.user)

    def get_queryset(self):
        """
        Limit post access based on the user's permission.
        Users can only see posts that they have permission to view.
        """
        cache_key = f'user_{self.request.user.id}_posts'
        posts = cache.get(cache_key)
        
        if not posts:
            # If not in cache, fetch from the database and store in cache
            user = self.request.user
            if user.is_authenticated:
                posts = Post.objects.filter(author=user) | Post.objects.all()
            else:
                posts = Post.objects.all()
            cache.set(cache_key, posts, timeout=60 * 15)  # Cache for 15 minutes
        
        return posts

    def put(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        # Ensure the user can edit their own post or has permission to edit
        if post.author != request.user and not request.user.has_perm('can_edit_post'):
            raise PermissionDenied("You do not have permission to edit this post.")
        serializer = PostSerializer(post, data=request.data)
        if serializer.is_valid():
            serializer.save()
            cache.delete(f'post_{post.pk}') # Clear the cache for the specific post after update
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        # Ensure the user can delete their own post or has permission to delete
        if post.author != request.user and not request.user.has_perm('can_delete_post'):
            raise PermissionDenied("You do not have permission to delete this post.")
        post.delete()
        cache.delete(f'post_{post.pk}') # Clear the cache for the specific post after deletion
        return Response({"detail": "Post deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class CommentListCreate(APIView):
    def get(self, request):
        # Return only comments the user is authorized to view
        comments = Comment.objects.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Ensure user can only create a comment if they are authenticated
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to create a comment.")
        
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            # Assign the logged-in user as the author of the comment
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        # Ensure the user can edit their own comment or has permission to edit
        if comment.author != request.user and not request.user.has_perm('can_edit_comment'):
            raise PermissionDenied("You do not have permission to edit this comment.")
        serializer = CommentSerializer(comment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        # Ensure the user can delete their own comment or has permission to delete
        if comment.author != request.user and not request.user.has_perm('can_delete_comment'):
            raise PermissionDenied("You do not have permission to delete this comment.")
        comment.delete()
        return Response({"detail": "Comment deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


# The new ProtectedView class that requires authentication with TokenAuthentication
class ProtectedView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request):
        return Response({"message": "Authenticated!"})

# For the newsfeed feature
class NewsFeedView(ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None 

    def get_queryset(self):
        user = self.request.user
        cache_key = f'user_{user.id}_feed'
        posts = cache.get(cache_key)

        if not posts:
            posts = Post.objects.all().order_by('-created_at')  # Sorted by date (newest first)
            cache.set(cache_key, posts, timeout=60 * 5)  # cache for 5 minutes

        return posts


# Create your views here.
# def get_users(request):
#     try:
#         users = list(User.objects.values('id', 'username', 'email', 'created_at'))
#         return JsonResponse(users, safe=False)
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)

# @csrf_exempt
# def create_user(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             user = User.objects.create_user(username="new_user", password="secure_pass123")
#             print(user.password)  # Outputs a hashed password
#             return JsonResponse({'id': user.id, 'message': 'User created successfully'}, status=201)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=400)

# @csrf_exempt
# def update_user(request, id):
#     if request.method == 'PUT':
#         try:
#             data = json.loads(request.body)
#             email = data['email']
#             user = User.objects.filter(id=id).first()
#             # data = UserSerializer(isinstance=user, data=request.data)
#             user.email = email
#             user.save()
#             return JsonResponse({'message': 'User updated successfully'}, status=201)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=400)

# @csrf_exempt
# def delete_user(request, id):
#     if request.method == 'DELETE':
#         try:
#             user = User.objects.filter(id=id).first()
#             user.delete()
#             #User.objects.delete(id=id)
#             return JsonResponse({'message': 'User deleted successfully'}, status=200)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=400)


