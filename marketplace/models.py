# marketplace/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import os

def user_template_upload_to(instance, filename):
    return f"user_templates/{instance.user.id}/{filename}"

class UserTemplate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_template_upload_to)
    created_at = models.DateTimeField(auto_now_add=True)



class Category(models.Model):
    """Template categories"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='fa-folder')
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Tags for templates"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


from django.db import models
from django.contrib.auth.models import User

class Template(models.Model):
    """Main template model"""

    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    # --------------------
    # Basic Info
    # --------------------
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=250)

    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=300, blank=True)

    # --------------------
    # Categorization
    # --------------------
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        related_name='templates'
    )

    tags = models.ManyToManyField(
        'Tag',
        blank=True,
        related_name='templates'
    )

    # --------------------
    # Pricing
    # --------------------
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_free = models.BooleanField(default=False)

    # --------------------
    # Media
    # --------------------
    thumbnail = models.ImageField(upload_to='templates/thumbnails/', blank=True, null=True)
    preview_images = models.JSONField(default=list, blank=True)
    demo_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    fallback_image = models.ImageField(
        upload_to='fallbacks/',
        blank=True,
        null=True
    )

    # --------------------
    # Files
    # --------------------
    folder_name = models.CharField(max_length=200)
    zip_file = models.FileField(upload_to='templates/zips/', blank=True, null=True)
    file_size = models.CharField(max_length=50, blank=True)

    # --------------------
    # Ownership & Metadata
    # --------------------
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_templates',
        null=True,
        blank=True
    )

    version = models.CharField(max_length=20, default='1.0')
    last_updated = models.DateTimeField(auto_now=True)

    # --------------------
    # Features
    # --------------------
    features = models.JSONField(default=list, blank=True)
    technologies = models.JSONField(default=list, blank=True)
    includes = models.JSONField(default=list, blank=True)

    # --------------------
    # Stats
    # --------------------
    views = models.IntegerField(default=0)
    downloads = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_reviews = models.IntegerField(default=0)

    # --------------------
    # Status
    # --------------------
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_card_image(self):
        """Returns thumbnail, fallback, or None"""
        if self.thumbnail:
            return self.thumbnail.url
        if self.fallback_image:
            return self.fallback_image.url
        return None
    
    def get_display_image(self):
        """Get image to display - thumbnail, fallback, or default"""
        if self.thumbnail:
            return self.thumbnail.url
        if self.fallback_image:
            return self.fallback_image.url
        
        # Default images pool
        default_images = [
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1483058712412-4245e9b90334?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1551650975-87deedd944c3?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1558655146-364adaf1fcc9?w=800&h=600&fit=crop",
        ]
        
        # Use template ID to pick consistent default image
        return default_images[self.id % len(default_images)]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.short_description:
            self.short_description = self.description[:297] + '...' if len(self.description) > 300 else self.description
        super().save(*args, **kwargs)
    
    def get_discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0
    
    def update_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.rating = round(avg, 2)
            self.total_reviews = reviews.count()
            self.save()


class Purchase(models.Model):
    """Track template purchases"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='purchases')
    
    # Payment
    order_id = models.CharField(max_length=200, blank=True)
    payment_id = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    paid = models.BooleanField(default=False)
    
    # License
    license_key = models.CharField(
        max_length=255,
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    
    
    purchased_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'template')
        ordering = ['-purchased_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name}"


class Review(models.Model):
    """Template reviews"""
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    helpful_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('template', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name} ({self.rating}★)"


class CartItem(models.Model):
    """Shopping cart items"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'template')
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name}"
    
    def get_total(self):
        return self.template.price * self.quantity


class UserTemplate(models.Model):
    """User's customized templates"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_templates')
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    
    # Files
    uploaded_zip = models.FileField(upload_to='user_templates/uploads/', blank=True)
    extracted_path = models.CharField(max_length=500, blank=True)
    
    # Customization
    custom_name = models.CharField(max_length=200, blank=True)
    custom_colors = models.JSONField(default=dict, blank=True)  # Color scheme
    custom_fonts = models.JSONField(default=dict, blank=True)
    custom_settings = models.JSONField(default=dict, blank=True)
    
    # Publishing
    published = models.BooleanField(default=False)
    published_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name}"
    
    def get_extract_dir(self):
        return os.path.join('media', 'user_templates', str(self.id))


class UserProduct(models.Model):
    """Products for e-commerce templates"""
    user_template = models.ForeignKey(UserTemplate, on_delete=models.CASCADE, related_name='products')
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='user_products/', blank=True)
    image_data = models.TextField(blank=True)  # Base64 for export
    
    category = models.CharField(max_length=100, blank=True)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return self.name


class Workspace(models.Model):
    """Team workspaces"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_workspaces')
    members = models.ManyToManyField(User, through='WorkspaceMember', related_name='workspaces')
    
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class WorkspaceMember(models.Model):
    """Workspace membership with roles"""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('workspace', 'user')
    
    def __str__(self):
        return f"{self.user.username} - {self.workspace.name} ({self.role})"


class TemplateAnalytics(models.Model):
    """Daily analytics for templates"""
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(auto_now_add=True)
    
    views = models.IntegerField(default=0)
    unique_views = models.IntegerField(default=0)
    downloads = models.IntegerField(default=0)
    purchases = models.IntegerField(default=0)
    cart_additions = models.IntegerField(default=0)
    
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ('template', 'date')
        ordering = ['-date']


class Subscription(models.Model):
    """User subscriptions"""
    PLAN_CHOICES = [
        ('basic', 'Basic - 5 templates/month'),
        ('pro', 'Pro - 20 templates/month'),
        ('unlimited', 'Unlimited'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basic')
    
    # Razorpay subscription
    subscription_id = models.CharField(max_length=200, blank=True)
    
    downloads_limit = models.IntegerField(default=5)
    downloads_used = models.IntegerField(default=0)
    
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    auto_renew = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan}"
    
    def can_download(self):
        if self.plan == 'unlimited':
            return True
        return self.downloads_used < self.downloads_limit


class Wishlist(models.Model):
    """User wishlists"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'template')
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name}"


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    
    # Contact
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Social
    github = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    
    # Settings
    email_notifications = models.BooleanField(default=True)
    newsletter = models.BooleanField(default=True)
    
    # Stats
    total_purchases = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user.username


class TemplateComponent(models.Model):
    """Reusable components"""
    CATEGORY_CHOICES = [
        ('header', 'Header'),
        ('footer', 'Footer'),
        ('hero', 'Hero Section'),
        ('card', 'Card'),
        ('form', 'Form'),
        ('nav', 'Navigation'),
        ('button', 'Button'),
        ('gallery', 'Gallery'),
        ('testimonial', 'Testimonial'),
        ('pricing', 'Pricing Table'),
        ('faq', 'FAQ'),
        ('cta', 'Call to Action'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='components/thumbnails/', blank=True)
    
    html_code = models.TextField()
    css_code = models.TextField(blank=True)
    js_code = models.TextField(blank=True)
    
    is_premium = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)




