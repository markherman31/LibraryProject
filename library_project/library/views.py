from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Book, Author, Member, BookLoan, Review
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, F, ExpressionWrapper, DurationField, Q
from datetime import datetime, timedelta
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, F, ExpressionWrapper, DurationField
from django.utils import timezone
from django.db import transaction

class BookListView(ListView):
    model = Book
    template_name = 'library/book_list.html'
    context_object_name = 'books'
    paginate_by = 10
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Book.objects.filter(title__icontains=query).select_related()
        return Book.objects.all().select_related()

class BookDetailView(DetailView):
    model = Book
    template_name = 'library/book_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews'] = self.object.review_set.all()
        if self.request.user.is_authenticated:
            context['user_review'] = self.object.review_set.filter(
                member=self.request.user.member
            ).first()
        return context

class BookCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Book
    template_name = 'library/book_form.html'
    fields = ['title', 'isbn', 'published_date', 'publisher', 'language', 
              'page_count', 'available_copies', 'status']
    success_url = reverse_lazy('book-list')
    
    def test_func(self):
        return self.request.user.is_staff

class LoanBookView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            with transaction.atomic():
                book = Book.objects.select_for_update().get(pk=pk)
                if book.available_copies > 0:
                    loan = BookLoan.objects.create(
                        book=book,
                        member=request.user.member
                    )
                    book.available_copies -= 1
                    book.save()
                    messages.success(request, f'Successfully borrowed {book.title}')
                else:
                    messages.error(request, 'This book is currently unavailable')
            
            return redirect('library:book-list')
                    
        except Book.DoesNotExist:
            messages.error(request, 'Book not found')
        except Exception as e:
            messages.error(request, 'An error occurred while processing your request')
            
        return redirect('library:book-list')

class ReturnBookView(LoginRequiredMixin, View):
    def post(self, request, pk):
        loan = get_object_or_404(BookLoan, pk=pk, member=request.user.member, status='ongoing')
        
        loan.return_date = timezone.now()
        loan.status = 'returned'
        loan.save()
        
        book = loan.book
        book.available_copies += 1
        book.save()
        
        messages.success(request, f'Successfully returned "{book.title}"')
        return redirect('library:member-dashboard')
    
class MemberDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        member = request.user.member
        context = {
            'current_loans': BookLoan.objects.filter(
                member=member, 
                status='ongoing'
            ),
            'past_loans': BookLoan.objects.filter(
                member=member, 
                status='returned'
            ),
            'reviews': Review.objects.filter(member=member)
        }
        return render(request, 'library/member_dashboard.html', context)
    
class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    template_name = 'library/review_form.html'
    fields = ['rating', 'comment']
    
    def form_valid(self, form):
        book = get_object_or_404(Book, pk=self.kwargs['pk'])
        existing_review = Review.objects.filter(
            book=book,
            member=self.request.user.member
        ).exists()
        
        if existing_review:
            messages.error(self.request, 'You have already reviewed this book.')
            return redirect('library:book-detail', pk=book.pk)
        
        form.instance.book = book
        form.instance.member = self.request.user.member
        messages.success(self.request, 'Your review has been submitted successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['book'] = get_object_or_404(Book, pk=self.kwargs['pk'])
        return context
    
    def get_success_url(self):
        return reverse_lazy('library:book-detail', kwargs={'pk': self.kwargs['pk']})
    
class AuthorListView(ListView):
    model = Author
    template_name = 'library/author_list.html'
    context_object_name = 'authors'
    paginate_by = 12
    
    def get_queryset(self):
        return Author.objects.all().prefetch_related('books').order_by('last_name', 'first_name')

class AuthorDetailView(DetailView):
    model = Author
    template_name = 'library/author_detail.html'

class LoanReportView(LoginRequiredMixin, TemplateView):
    template_name = 'library/loan_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        author_id = self.request.GET.get('author')

        selected_columns = self.request.GET.getlist('columns')
        if not selected_columns and self.request.GET:  
            selected_columns = []  
        elif not selected_columns:  
            selected_columns = ['book_title', 'author', 'member', 'checkout_date', 
                              'due_date', 'return_date', 'status']  
        
        context['selected_columns'] = selected_columns

        loans = BookLoan.objects.all()

        if start_date:
            loans = loans.filter(checkout_date__gte=start_date)
        if end_date:
            loans = loans.filter(checkout_date__lte=end_date)
        if author_id:
            loans = loans.filter(book__authors__id=author_id)

        if self.request.GET:
            total_loans = loans.count()
            active_loans = loans.filter(status='ongoing').count()
            returned_loans = loans.filter(status='returned')
            
            if returned_loans.exists():
                avg_duration = 0
                for loan in returned_loans:
                    if loan.return_date and loan.checkout_date:
                        duration = (loan.return_date.date() - loan.checkout_date.date()).days
                        avg_duration += duration
                avg_duration = avg_duration / returned_loans.count()
            else:
                avg_duration = 0

            return_rate = (returned_loans.count() / total_loans * 100) if total_loans > 0 else 0

            context['stats'] = {
                'total_loans': total_loans,
                'active_loans': active_loans,
                'avg_duration': round(avg_duration),
                'return_rate': return_rate,
            }

            context['loans'] = loans.select_related(
                'book', 'member__user'
            ).prefetch_related('book__authors')

        context['authors'] = Author.objects.all().order_by('last_name', 'first_name')
        
        return context