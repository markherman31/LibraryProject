from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.BookListView.as_view(), name='book-list'),
    path('book/<int:pk>/', views.BookDetailView.as_view(), name='book-detail'),
    path('book/new/', views.BookCreateView.as_view(), name='book-create'),
    path('book/<int:pk>/borrow/', views.LoanBookView.as_view(), name='borrow-book'),
    path('loan/<int:pk>/return/', views.ReturnBookView.as_view(), name='return-book'),
    path('dashboard/', views.MemberDashboardView.as_view(), name='member-dashboard'),
    path('book/<int:pk>/review/', views.ReviewCreateView.as_view(), name='create-review'),
    path('authors/', views.AuthorListView.as_view(), name='author-list'),
    path('author/<int:pk>/', views.AuthorDetailView.as_view(), name='author-detail'),
    path('reports/loans/', views.LoanReportView.as_view(), name='loan-report'),
]