from django.core.management.base import BaseCommand
from store.models import Product, ProductImage
import cloudinary.uploader
import os

class Command(BaseCommand):
    help = 'Migrate local image files to Cloudinary if not already uploaded'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting migration to Cloudinary...'))

        def upload_image(instance, field_name, folder, prefix):
            image_field = getattr(instance, field_name)
            if not image_field:
                return False

            # Try to get local path
            try:
                image_path = image_field.path
            except Exception:
                # Fall back to image_field.url if path not available
                image_path = image_field.url if hasattr(image_field, 'url') else None

            if not image_path or image_path.startswith('http'):
                self.stdout.write(self.style.WARNING(f"  ⚠️ Skipping (already cloud-based): {instance}"))
                return False

            if os.path.exists(image_path):
                try:
                    result = cloudinary.uploader.upload(
                        image_path,
                        folder=folder,
                        public_id=f"{prefix}_{instance.id}",
                        overwrite=True
                    )
                    setattr(instance, field_name, result['public_id'])
                    instance.save()
                    return True
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Error: {e}"))
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠️ File not found: {image_path}"))
            return False

        # --- Products ---
        products = Product.objects.all()
        total_products = products.count()
        success_products = 0

        for i, p in enumerate(products, 1):
            self.stdout.write(f"Processing {i}/{total_products}: {p.name}")
            if upload_image(p, 'image', 'products', 'product'):
                success_products += 1

        # --- Gallery ---
        gallery = ProductImage.objects.all()
        total_gallery = gallery.count()
        success_gallery = 0

        for i, g in enumerate(gallery, 1):
            self.stdout.write(f"Processing gallery {i}/{total_gallery}")
            if upload_image(g, 'image', 'products/gallery', 'gallery'):
                success_gallery += 1

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"✅ Migration complete!"))
        self.stdout.write(self.style.SUCCESS(f"Products uploaded: {success_products}/{total_products}"))
        self.stdout.write(self.style.SUCCESS(f"Gallery uploaded: {success_gallery}/{total_gallery}"))
        self.stdout.write("="*50)
