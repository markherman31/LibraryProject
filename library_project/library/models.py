from django.db import models, connection
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta

class Book(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    isbn = models.CharField(max_length=13, unique=True)
    published_date = models.DateField()
    publisher = models.CharField(max_length=200)
    language = models.CharField(max_length=50)
    page_count = models.IntegerField()
    available_copies = models.IntegerField(default=0)
    
    BOOK_STATUS = (
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('maintenance', 'Under Maintenance'),
        ('lost', 'Lost'),
    )
    status = models.CharField(max_length=20, choices=BOOK_STATUS, default='available')
    
    def __str__(self):
        return f"{self.title} ({self.isbn})"
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'available_copies']), 
        ]

    @classmethod
    def find_similar_books(cls, title_keyword, min_rating=3.0):
        with connection.cursor() as cursor:
            query = """
                SELECT b.id, b.title, b.isbn, 
                       AVG(r.rating) as avg_rating,
                       COUNT(r.id) as review_count
                FROM library_book b
                LEFT JOIN library_review r ON b.id = r.book_id
                WHERE b.title LIKE %s
                GROUP BY b.id, b.title, b.isbn
                HAVING AVG(r.rating) >= %s OR AVG(r.rating) IS NULL
                ORDER BY avg_rating DESC NULLS LAST;
            """
            cursor.execute(query, [f'%{title_keyword}%', min_rating])
            columns = [col[0] for col in cursor.description]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

    @classmethod
    def get_book_statistics(cls, book_id):
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    b.title,
                    COALESCE(COUNT(DISTINCT bl.id), 0) as total_loans,
                    COALESCE(COUNT(DISTINCT CASE WHEN bl.status = 'ongoing' THEN bl.id END), 0) as active_loans,
                    COALESCE(AVG(r.rating), 0) as average_rating,
                    COALESCE(COUNT(DISTINCT r.id), 0) as review_count
                FROM library_book b
                LEFT JOIN library_bookloan bl ON b.id = bl.book_id
                LEFT JOIN library_review r ON b.id = r.book_id
                WHERE b.id = %s
                GROUP BY b.id, b.title;
            """
            cursor.execute(query, [book_id])
            result = cursor.fetchone()
            if result is None:
                return {
                    'title': '',
                    'total_loans': 0,
                    'active_loans': 0,
                    'average_rating': 0.0,
                    'review_count': 0
                }
            return {
                'title': result[0],
                'total_loans': result[1],
                'active_loans': result[2],
                'average_rating': float(result[3]) if result[3] else 0.0,
                'review_count': result[4]
            }

class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    biography = models.TextField(blank=True)
    books = models.ManyToManyField(Book, related_name='authors')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    class Meta:
        ordering = ['last_name', 'first_name']

class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    library_card_number = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    date_joined = models.DateField(auto_now_add=True)
    
    MEMBERSHIP_STATUS = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    )
    status = models.CharField(max_length=20, choices=MEMBERSHIP_STATUS, default='active')
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.library_card_number})"

class BookLoan(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    checkout_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)
    
    LOAN_STATUS = (
        ('ongoing', 'Ongoing'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
    )
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='ongoing')
    
    class Meta:
        indexes = [
            models.Index(fields=['checkout_date']),  
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=14)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.book.title} - {self.member.user.get_full_name()}"
    
class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review for {self.book.title} by {self.member.user.get_full_name()}"
    
    class Meta:
        indexes = [
            models.Index(fields=['book', 'rating']),  
            models.Index(fields=['date_posted']),  
        ]