
from urllib.parse import unquote
from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator

from .models import (
    Template, Purchase, UserTemplate, CartItem, Review, 
    Category, Tag, Wishlist, TemplateAnalytics, UserProfile
)

# Try to import UserProduct (optional)
try:
    from .models import UserProduct
except ImportError:
    UserProduct = None

# Razorpay client
try:
    import razorpay
    razorpay_client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
except Exception:
    razorpay_client = None


# =============================================
# AUTHENTICATION
# =============================================

def register(request):
    """User registration"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', password)
        
        if not username or not email or not password:
            messages.error(request, 'All fields are required')
            return redirect('marketplace:register')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return redirect('marketplace:register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
            return redirect('marketplace:register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return redirect('marketplace:register')
        
        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user)
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('marketplace:login')
    
    return render(request, 'marketplace/register.html')


def user_login(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            next_url = request.GET.get('next', 'marketplace:home')
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('marketplace:login')
    
    return render(request, 'marketplace/login.html')


def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('marketplace:home')


# =============================================
# HOME & LISTING
# =============================================

from django.db.models import Count, Q
from django.contrib.auth.models import User
from .models import Template, Category, CartItem

def home(request):
    """Homepage"""

    featured_templates = Template.objects.filter(
        is_published=True,
        is_featured=True
    )[:6]

    default_images = [
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1483058712412-4245e9b90334?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800&h=600&fit=crop",
    ]

    for i, template in enumerate(featured_templates):

     if template.thumbnail:
        template.preview_image_url = template.thumbnail.url
     elif template.fallback_image:
        template.preview_image_url = template.fallback_image.url
     else:
        template.preview_image_url = default_images[i % len(default_images)]


    categories = Category.objects.annotate(
        template_count=Count('templates', filter=Q(templates__is_published=True))
    ).filter(template_count__gt=0)[:8]

    total_templates = Template.objects.filter(is_published=True).count()
    total_users = User.objects.count()

    cart_count = 0
    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).count()

    context = {
        'featured_templates': featured_templates,
        'categories': categories,
        'total_templates': total_templates,
        'total_users': total_users,
        'cart_count': cart_count,
    }

    return render(request, 'marketplace/home.html', context)



def template_list(request):
    """Template listing with filters"""
    templates = Template.objects.filter(is_published=True)
    
    # Search
    query = request.GET.get('q', '')
    if query:
        templates = templates.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()
    
    # Category filter
    category_slug = request.GET.get('category')
    if category_slug:
        templates = templates.filter(category__slug=category_slug)
    
    # Price filter
    price_filter = request.GET.get('price')
    if price_filter == 'free':
        templates = templates.filter(is_free=True)
    elif price_filter == 'paid':
        templates = templates.filter(is_free=False)
    
    # Rating filter
    min_rating = request.GET.get('rating')
    if min_rating:
        templates = templates.filter(rating__gte=float(min_rating))
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    valid_sorts = {
        'popular': '-views',
        'rating': '-rating',
        'price_low': 'price',
        'price_high': '-price',
        'newest': '-created_at',
    }
    templates = templates.order_by(valid_sorts.get(sort, '-created_at'))
    
    # Pagination
    paginator = Paginator(templates, 12)
    page = request.GET.get('page', 1)
    templates_page = paginator.get_page(page)
    
    context = {
        'templates': templates_page,
        'categories': Category.objects.all(),
        'query': query,
        'current_category': category_slug,
        'current_sort': sort,
    }
    return render(request, 'marketplace/template_list.html', context)


def template_detail(request, slug):
    """Template detail page"""
    template = get_object_or_404(Template, slug=slug, is_published=True)
    
    # Increment views
    template.views += 1
    template.save(update_fields=['views'])
    
    # Track analytics
    today = timezone.now().date()
    analytics, _ = TemplateAnalytics.objects.get_or_create(
        template=template, 
        date=today
    )
    analytics.views += 1
    analytics.save()
    
    # Check purchase/cart/wishlist status
    purchased = False
    in_cart = False
    in_wishlist = False
    user_review = None
    
    if request.user.is_authenticated:
        purchased = Purchase.objects.filter(
            user=request.user, 
            template=template, 
            paid=True
        ).exists()
        
        in_cart = CartItem.objects.filter(
            user=request.user, 
            template=template
        ).exists()
        
        in_wishlist = Wishlist.objects.filter(
            user=request.user, 
            template=template
        ).exists()
        
        try:
            user_review = Review.objects.get(
                template=template, 
                user=request.user
            )
        except Review.DoesNotExist:
            pass
    
    # Get reviews
    reviews = template.reviews.all().select_related('user')[:10]
    
    # Similar templates
    similar_templates = Template.objects.filter(
        category=template.category,
        is_published=True
    ).exclude(id=template.id)[:4]
    
    # Add default images for main template
    default_images = [
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1483058712412-4245e9b90334?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800&h=600&fit=crop",
    ]
    
    # Set preview image for main template
    try:
        if template.thumbnail:
            template.preview_image_url = template.thumbnail.url
        else:
            template.preview_image_url = default_images[0]
    except Exception:
        template.preview_image_url = default_images[0]
    
    # Set preview images for similar templates
    for i, sim_template in enumerate(similar_templates):
        try:
            if sim_template.thumbnail:
                sim_template.preview_image_url = sim_template.thumbnail.url
            else:
                sim_template.preview_image_url = default_images[i % len(default_images)]
        except Exception:
            sim_template.preview_image_url = default_images[i % len(default_images)]
    
    context = {
        'template': template,
        'purchased': purchased,
        'in_cart': in_cart,
        'in_wishlist': in_wishlist,
        'user_review': user_review,
        'reviews': reviews,
        'similar_templates': similar_templates,
    }
    return render(request, 'marketplace/template_detail.html', context)

def themes_page(request):
    templates = Template.objects.filter(is_published=True).order_by('-created_at')
    categories = Category.objects.all()
    
    category_slug = request.GET.get('category')
    if category_slug:
        templates = templates.filter(category__slug=category_slug)
    
    paginator = Paginator(templates, 12)
    page = request.GET.get('page', 1)
    templates_page = paginator.get_page(page)
    
    # Add default/fallback images
    default_images = [
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1483058712412-4245e9b90334?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1551650975-87deedd944c3?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1558655146-364adaf1fcc9?w=800&h=600&fit=crop",
    ]
    
    # Convert to list and set preview_image_url
    template_list = list(templates_page.object_list)
    for i, template in enumerate(template_list):
        if template.thumbnail:
            template.preview_image_url = template.thumbnail.url
        else:
            template.preview_image_url = default_images[i % len(default_images)]
    
    # Update the page object with modified templates
    templates_page.object_list = template_list

    context = {
        'templates': templates_page,
        'categories': categories,
        'current_category': category_slug,
    }
    return render(request, 'marketplace/themes.html', context)


# =============================================
# PREVIEW
# =============================================

from django.shortcuts import render, get_object_or_404, redirect

def preview_template(request, slug):
    """Preview template safely"""
    template = get_object_or_404(Template, slug=slug, is_published=True)

    # If template has a demo URL, redirect to it
    if template.demo_url:
        return redirect(template.demo_url)

    # Check if folder_name is provided
    if template.folder_name:
        template_path = f'marketplace/themes/{template.folder_name}/index.html'
        context = {
            'template': template,
            'is_preview': True,
        }

        try:
            return render(request, template_path, context)
        except Exception as e:
            # Failed to render the template from folder
            return render(request, 'marketplace/preview_placeholder.html', {
                'template': template,
                'error': f"Failed to load template from folder: {template_path}\nError: {str(e)}"
            })
    else:
        # folder_name missing → show placeholder
        return render(request, 'marketplace/preview_placeholder.html', {
    'template': template,
    'error': f"Failed to load template from folder: {template_path}\nError: {str(e)}",
    'is_preview': True,
})




def preview_template_fullscreen(request, slug):
    """Fullscreen preview"""
    template = get_object_or_404(Template, slug=slug, is_published=True)
    
    context = {
        "template": template,
        "preview_url": f"/themes/{template.folder_name}/index.html" if template.folder_name else "#",
        "title": template.name,
        "price": template.price,
        "author": template.owner.username,
    }
    
    return render(request, "marketplace/fullscreen_preview.html", context)


# =============================================
# SEARCH & CATEGORIES
# =============================================

def search(request):
    """Search templates"""
    query = request.GET.get('q', '')
    
    if not query:
        return redirect('marketplace:template_list')
    
    templates = Template.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(tags__name__icontains=query) |
        Q(category__name__icontains=query)
    ).filter(is_published=True).distinct()
    
    context = {
        'templates': templates,
        'query': query,
        'result_count': templates.count(),
    }
    return render(request, 'marketplace/search_results.html', context)


def category_templates(request, slug):
    """Templates by category"""
    category = get_object_or_404(Category, slug=slug)
    
    templates = Template.objects.filter(
        category=category,
        is_published=True
    ).order_by('-created_at')
    
    paginator = Paginator(templates, 12)
    page = request.GET.get('page', 1)
    templates_page = paginator.get_page(page)
    
    context = {
        'category': category,
        'templates': templates_page,
    }
    return render(request, 'marketplace/category_templates.html', context)


# =============================================
# CART
# =============================================

@login_required
def add_to_cart(request, template_id):
    """Add to cart"""
    template = get_object_or_404(Template, id=template_id)
    
    # Check if already purchased
    if Purchase.objects.filter(
        user=request.user, 
        template=template, 
        paid=True
    ).exists():
        messages.warning(request, 'You already own this template!')
        return redirect('marketplace:template_detail', slug=template.slug)
    
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user, 
        template=template
    )
    
    if created:
        messages.success(request, f'{template.name} added to cart!')
    else:
        messages.info(request, 'Template already in cart')
    
    return redirect('marketplace:cart_view')


@login_required
def cart_view(request):
    """View cart"""
    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('template')
    
    total = sum(item.get_total() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_items.count(),
    }
    return render(request, 'marketplace/cart.html', context)


@login_required
def remove_from_cart(request, template_id):
    """Remove from cart"""
    CartItem.objects.filter(
        user=request.user, 
        template_id=template_id
    ).delete()
    
    messages.success(request, 'Item removed from cart')
    return redirect('marketplace:cart_view')


# =============================================
# CHECKOUT & PAYMENT
# =============================================

@login_required
def checkout(request):
    """Checkout page"""
    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('template')
    
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('marketplace:cart_view')
    
    total = sum(item.get_total() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'marketplace/checkout.html', context)


@login_required
def create_order(request):
    """Create Razorpay order"""
    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('template')
    
    if not cart_items.exists():
        return JsonResponse({'error': 'Cart is empty'}, status=400)
    
    total = sum(item.get_total() for item in cart_items)
    amount_paise = int(total * 100)
    
    if not razorpay_client:
        return JsonResponse({'error': 'Payment gateway not configured'}, status=500)
    
    order = razorpay_client.order.create({
        'amount': amount_paise,
        'currency': 'INR',
        'receipt': f'order_{request.user.id}_{timezone.now().timestamp()}',
        'payment_capture': 1
    })
    
    template_ids = list(cart_items.values_list('template_id', flat=True))
    
    return JsonResponse({
        'order_id': order['id'],
        'key': settings.RAZORPAY_KEY_ID,
        'amount': amount_paise,
        'template_ids': template_ids,
    })

from django.urls import reverse
@csrf_exempt
@login_required
def verify_payment(request):
    """Verify payment"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
    
    payment_id = request.POST.get('razorpay_payment_id')
    order_id = request.POST.get('razorpay_order_id')
    signature = request.POST.get('razorpay_signature')
    
    if not all([payment_id, order_id, signature]):
        return JsonResponse({'status': 'missing_data'}, status=400)
    
    try:
        # Verify signature
        razorpay_client.utility.verify_payment_signature({
            'razorpay_payment_id': payment_id,
            'razorpay_order_id': order_id,
            'razorpay_signature': signature
        })
        
        # Get cart items
        cart_items = CartItem.objects.filter(
            user=request.user
        ).select_related('template')
        
        # Create purchases
        for item in cart_items:
            purchase, created = Purchase.objects.get_or_create(
                user=request.user,
                template=item.template,
                defaults={
                    'order_id': order_id,
                    'payment_id': payment_id,
                    'amount': item.template.price,
                    'paid': True,
                }
            )
            
            if not created:
                purchase.paid = True
                purchase.order_id = order_id
                purchase.payment_id = payment_id
                purchase.save()
            
            # Update stats
            item.template.downloads += 1
            item.template.save(update_fields=['downloads'])
        
        # Clear cart
        cart_items.delete()
        
        return JsonResponse({
    'status': 'success',
    'redirect': reverse('marketplace:purchase-success')
})
        
    except Exception as e:
        return JsonResponse({
            'status': 'failed', 
            'error': str(e)
        }, status=400)


@login_required
def purchase_success(request):
    """Purchase success page"""
    recent_purchases = Purchase.objects.filter(
        user=request.user,
        paid=True
    ).select_related('template').order_by('-purchased_at')[:5]
    
    context = {
        'purchases': recent_purchases,
    }
    return render(request, 'marketplace/purchase_success.html', context)


@login_required
def my_purchases(request):
    """My purchases"""
    purchases = Purchase.objects.filter(
        user=request.user,
        paid=True
    ).select_related('template').order_by('-purchased_at')
    
    paginator = Paginator(purchases, 20)
    page = request.GET.get('page', 1)
    purchases_page = paginator.get_page(page)
    
    context = {
        'purchases': purchases_page,
    }
    return render(request, 'marketplace/my_purchases.html', context)


# =============================================
# DOWNLOAD
# =============================================

@login_required
def download_template(request, template_id):
    """Download template"""
    template = get_object_or_404(Template, id=template_id)
    
    # Check purchase
    if not Purchase.objects.filter(
        user=request.user, 
        template=template, 
        paid=True
    ).exists():
        messages.error(request, 'You need to purchase this template first')
        return redirect('marketplace:template_detail', slug=template.slug)
    
    # Serve ZIP file
    if template.zip_file:
        response = FileResponse(
            template.zip_file.open('rb'), 
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{template.slug}.zip"'
        return response
    
    messages.error(request, 'Download file not available')
    return redirect('marketplace:my_purchases')


# =============================================
# REVIEWS
# =============================================

@login_required
@require_http_methods(['POST'])
def add_review(request, template_id):
    """Add review"""
    template = get_object_or_404(Template, id=template_id)
    
    # Check purchase
    if not Purchase.objects.filter(
        user=request.user, 
        template=template, 
        paid=True
    ).exists():
        return JsonResponse({'error': 'Purchase required'}, status=403)
    
    rating = int(request.POST.get('rating', 5))
    comment = request.POST.get('comment', '').strip()
    
    review, created = Review.objects.update_or_create(
        template=template,
        user=request.user,
        defaults={
            'rating': rating,
            'comment': comment,
        }
    )
    
    # Update template rating
    template.update_rating()
    
    messages.success(request, 'Review submitted successfully!')
    return redirect('marketplace:template_detail', slug=template.slug)


@login_required
@require_http_methods(['POST'])
def delete_review(request, review_id):
    """Delete review"""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    template = review.template
    review.delete()
    
    template.update_rating()
    
    messages.success(request, 'Review deleted')
    return redirect('marketplace:template_detail', slug=template.slug)


# =============================================
# WISHLIST
# =============================================

@login_required
def add_to_wishlist(request, template_id):
    """Add to wishlist"""
    template = get_object_or_404(Template, id=template_id)
    
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        template=template
    )
    
    if created:
        messages.success(request, 'Added to wishlist!')
    else:
        messages.info(request, 'Already in wishlist')
    
    return redirect('marketplace:template_detail', slug=template.slug)


@login_required
def remove_from_wishlist(request, template_id):
    """Remove from wishlist"""
    Wishlist.objects.filter(
        user=request.user, 
        template_id=template_id
    ).delete()
    
    messages.success(request, 'Removed from wishlist')
    return redirect('marketplace:wishlist_view')


@login_required
def wishlist_view(request):
    """View wishlist"""
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('template').order_by('-added_at')
    
    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'marketplace/wishlist.html', context)


# =============================================
# USER PROFILE
# =============================================

@login_required
def profile_view(request):
    """User profile"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    purchases = Purchase.objects.filter(user=request.user, paid=True)
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    
    context = {
        'profile': profile,
        'purchase_count': purchases.count(),
        'wishlist_count': wishlist_count,
        'recent_purchases': purchases[:5],
    }
    return render(request, 'marketplace/profile.html', context)


@login_required
def update_profile(request):
    """Update profile"""
    if request.method == 'POST':
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        profile.bio = request.POST.get('bio', '')
        profile.phone = request.POST.get('phone', '')
        profile.website = request.POST.get('website', '')
        
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('marketplace:profile_view')
    
    return redirect('marketplace:profile_view')


# =============================================
# DASHBOARD
# =============================================

@login_required
def template_dashboard(request, template_id):
    """Template dashboard"""
    template = get_object_or_404(Template, id=template_id)
    
    # Check purchase
    if not Purchase.objects.filter(
        user=request.user, 
        template=template, 
        paid=True
    ).exists():
        messages.error(request, 'You need to purchase this template first')
        return redirect('marketplace:template_detail', slug=template.slug)
    
    user_template, _ = UserTemplate.objects.get_or_create(
        user=request.user,
        template=template
    )
    
    context = {
        'template': template,
        'user_template': user_template,
    }
    return render(request, 'marketplace/dashboard.html', context)


@login_required
def upload_template_view(request, template_id):
    """Upload template"""
    template = get_object_or_404(Template, id=template_id)
    
    # Check purchase
    if not Purchase.objects.filter(
        user=request.user, 
        template=template, 
        paid=True
    ).exists():
        messages.error(request, 'Purchase required')
        return redirect('marketplace:template_detail', slug=template.slug)
    
    if request.method == 'POST' and request.FILES.get('uploaded_zip'):
        user_template, _ = UserTemplate.objects.get_or_create(
            user=request.user,
            template=template
        )
        
        user_template.uploaded_zip = request.FILES['uploaded_zip']
        user_template.save()
        
        messages.success(request, 'Template uploaded successfully!')
        return redirect('marketplace:template_dashboard', template_id=template.id)
    
    return render(request, 'marketplace/upload.html', {'template': template}) 
