from django.contrib import admin
from .models import Book, Author, Member, BookLoan, Review

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'isbn', 'available_copies', 'status')
    search_fields = ('title', 'isbn')
    list_filter = ('status',)

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name')
    search_fields = ('first_name', 'last_name')

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'library_card_number', 'status')
    search_fields = ('user__username', 'library_card_number')
    list_filter = ('status',)

@admin.register(BookLoan)
class BookLoanAdmin(admin.ModelAdmin):
    list_display = ('book', 'member', 'checkout_date', 'due_date', 'status')
    list_filter = ('status',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('book', 'member', 'rating', 'date_posted')
    list_filter = ('rating',)