from django.conf import settings
from store.models import Product
from orders.models import Coupon
import decimal
from decimal import Decimal

class Cart:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def __iter__(self):
        """Iterador que obtiene los productos pero NO los guarda en la sesión"""
        product_ids = self.cart.keys()

        # Obtener productos existentes
        products = Product.objects.filter(id__in=product_ids)
        product_dict = {str(product.id): product for product in products}

        # NO crear una copia del carrito, trabajar directamente con los datos
        items = []

        for product_id, item_data in self.cart.items():
            # VERIFICAR Y CORREGIR ESTRUCTURA DEL ITEM
            if 'price' not in item_data:
                # Si no tiene precio, intentar obtenerlo del producto
                if product_id in product_dict:
                    item_data['price'] = str(product_dict[product_id].price)
                else:
                    item_data['price'] = '0.00'

            # Asegurar que quantity existe
            if 'quantity' not in item_data:
                item_data['quantity'] = 1

            # Crear un nuevo diccionario para el item (NO modificar self.cart directamente)
            item = {
                'product_id': product_id,
                'quantity': item_data['quantity'],
                'price': item_data['price']
            }

            # Añadir información del producto y disponibilidad
            if product_id in product_dict:
                product = product_dict[product_id]
                item['product'] = product  # Esto es temporal para la iteración, no se guarda
                item['available'] = product.can_add_to_cart(item_data['quantity'])
                # Calcular precio total por item
                try:
                    item['total_price'] = item_data['quantity'] * float(item_data['price'])
                except (ValueError, TypeError):
                    item['total_price'] = 0.0
            else:
                # Si el producto no existe, marcarlo como no disponible
                item['product'] = None
                item['available'] = False
                item['total_price'] = 0

            # Solo añadir items con productos válidos
            if product_id in product_dict:
                items.append(item)

        # Devolver los items procesados
        for item in items:
            yield item

    def __len__(self):
        """Retorna el número total de items en el carrito"""
        try:
            return sum(item['quantity'] for item in self.cart.values())
        except KeyError:
            # Si hay algún problema con la estructura, limpiar el carrito
            self._clean_corrupted_cart()
            return 0

    def add(self, product, quantity=1, override_quantity=False):
        """Añadir producto al carrito con validación de stock"""
        product_id = str(product.id)

        # VERIFICAR STOCK ANTES DE AÑADIR
        if not product.can_add_to_cart(quantity):
            print(f"❌ No se puede añadir {product.name} - Stock insuficiente")
            return False

        if product_id in self.cart:
            # VERIFICAR QUE EL ITEM EXISTENTE TENGA LA ESTRUCTURA CORRECTA
            if 'quantity' not in self.cart[product_id]:
                self.cart[product_id]['quantity'] = 0
            if 'price' not in self.cart[product_id]:
                self.cart[product_id]['price'] = str(product.price)

            if override_quantity:
                self.cart[product_id]['quantity'] = quantity
            else:
                # Verificar stock para la nueva cantidad total
                new_quantity = self.cart[product_id]['quantity'] + quantity
                if product.can_add_to_cart(new_quantity):
                    self.cart[product_id]['quantity'] = new_quantity
                else:
                    print(f"❌ Stock insuficiente para {product.name}")
                    return False
        else:
            # CREAR NUEVO ITEM CON ESTRUCTURA COMPLETA (SOLO DATOS SERIALIZABLES)
            self.cart[product_id] = {
                'quantity': quantity,
                'price': str(product.price)  # Solo strings, números, etc.
            }

        self.save()
        print(f"✅ Producto añadido: {product.name} x{quantity}")
        return True

    def save(self):
        """Guardar el carrito en la sesión (solo datos serializables)"""
        # Antes de guardar, limpiar items corruptos y asegurar que solo hay datos serializables
        self._clean_corrupted_cart()
        self._ensure_serializable_data()
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def remove(self, product):
        """Remover producto del carrito"""
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        """Limpiar el carrito"""
        self.session[settings.CART_SESSION_ID] = {}
        self.session.modified = True

    def get_total_price(self):
        """Calcular el precio total del carrito"""
        from decimal import Decimal
        total = Decimal('0')

        for product_id, item in self.cart.items():
            try:
                if 'price' in item and 'quantity' in item:
                    price = Decimal(str(item['price']))
                    quantity = int(item['quantity'])
                    total += price * quantity
            except (ValueError, TypeError, KeyError):
                continue

        return total
    def check_stock_availability(self):
        """Verificar que todos los productos tengan stock suficiente"""
        errors = []
        warnings = []

        for item in self:  # Esto usa __iter__ que ya obtiene los productos
            # VERIFICAR SI EL ITEM TIENE PRODUCTO
            if 'product' not in item or item['product'] is None:
                errors.append("Producto no encontrado o eliminado")
                continue

            product = item['product']
            quantity = item['quantity']

            if product.stock_quantity <= 0:
                errors.append(f"'{product.name}' está agotado")
            elif product.stock_quantity < quantity:
                errors.append(
                    f"Stock insuficiente para '{product.name}'. "
                    f"Disponible: {product.stock_quantity}, "
                    f"Solicitado: {quantity}"
                )
            elif product.stock_quantity < 5:
                warnings.append(
                    f"Quedan pocas unidades de '{product.name}' "
                    f"(solo {product.stock_quantity} disponibles)"
                )

        return errors, warnings

    def get_available_items(self):
        """Obtener solo los items con stock disponible"""
        available_items = []
        for item in self:  # Esto usa __iter__
            if item['product'] and item['product'].stock_quantity >= item['quantity']:
                available_items.append(item)
        return available_items

    def cleanup_nonexistent_products(self):
        """Eliminar productos que ya no existen en la base de datos"""
        cleaned = False
        product_ids = list(self.cart.keys())

        for product_id in product_ids:
            try:
                Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                # Producto no existe, eliminarlo del carrito
                if product_id in self.cart:
                    del self.cart[product_id]
                    cleaned = True
                    print(f"🧹 Producto eliminado (no existe): {product_id}")

        if cleaned:
            self.save()

        return cleaned

    def update_quantities_based_on_stock(self):
        """Actualizar cantidades basado en stock disponible - VERSIÓN SEGURA"""
        updated = False

        for product_id, item in list(self.cart.items()):
            try:
                product = Product.objects.get(id=product_id)

                # Asegurar que el item tenga la estructura correcta
                if 'quantity' not in item:
                    item['quantity'] = 1
                if 'price' not in item:
                    item['price'] = str(product.price)

                current_quantity = item['quantity']

                if current_quantity > product.stock_quantity:
                    if product.stock_quantity > 0:
                        # Ajustar cantidad al stock disponible
                        self.cart[product_id]['quantity'] = product.stock_quantity
                        updated = True
                        print(f"⚠️ Cantidad ajustada: {product.name} ({current_quantity} → {product.stock_quantity})")
                    else:
                        # Eliminar producto agotado
                        del self.cart[product_id]
                        updated = True
                        print(f"🗑️ Producto eliminado: {product.name} (agotado)")

            except Product.DoesNotExist:
                # Eliminar producto que ya no existe en la base de datos
                if product_id in self.cart:
                    del self.cart[product_id]
                    updated = True
                    print(f"🗑️ Producto no encontrado, eliminado: {product_id}")

        if updated:
            self.save()

        return updated

    def _clean_corrupted_cart(self):
        """Método interno para limpiar items corruptos del carrito"""
        corrupted_items = []

        for product_id, item in self.cart.items():
            # Verificar que item sea un diccionario
            if not isinstance(item, dict):
                corrupted_items.append(product_id)
                continue

            # Verificar que tenga quantity
            if 'quantity' not in item:
                corrupted_items.append(product_id)
                continue

            # Verificar que quantity sea un número válido
            try:
                quantity = int(item['quantity'])
                if quantity <= 0:
                    corrupted_items.append(product_id)
            except (ValueError, TypeError):
                corrupted_items.append(product_id)

        # Eliminar items corruptos
        for product_id in corrupted_items:
            if product_id in self.cart:
                del self.cart[product_id]
                print(f"🧹 Item corrupto eliminado: {product_id}")

    def _ensure_serializable_data(self):
        """Asegurar que todos los datos en el carrito sean serializables"""
        for product_id, item in self.cart.items():
            # Remover cualquier objeto que no sea serializable
            if hasattr(item, '__dict__'):
                # Si es un objeto, convertirlo a diccionario básico
                basic_item = {
                    'quantity': getattr(item, 'quantity', 1),
                    'price': str(getattr(item, 'price', '0.00'))
                }
                self.cart[product_id] = basic_item

    def get_item_count(self):
        """Obtener el número total de items (para el contador del navbar)"""
        try:
            return sum(item.get('quantity', 1) for item in self.cart.values())
        except:
            return 0

    def is_empty(self):
        """Verificar si el carrito está vacío"""
        return len(self.cart) == 0

    def get_item(self, product_id):
        """Obtener un item específico del carrito"""
        product_id_str = str(product_id)
        if product_id_str in self.cart:
            return self.cart[product_id_str]
        return None

    def get_product_ids(self):
        """Obtener lista de IDs de productos en el carrito"""
        return list(self.cart.keys())

    # =============================================
    # MÉTODOS DE CUPONES - DENTRO DE LA CLASE CART
    # =============================================

    def get_coupon(self):
        """Obtener el cupón aplicado desde la sesión"""
        coupon_data = self.session.get('applied_coupon')
        if coupon_data:
            try:
                from orders.models import Coupon
                coupon = Coupon.objects.get(
                    id=coupon_data['id'],
                    is_active=True
                )
                return coupon
            except (Coupon.DoesNotExist, KeyError):
                # Si el cupón ya no existe, limpiarlo
                self.remove_coupon()
        return None

    def apply_coupon(self, coupon_code):
        """Aplicar un cupón al carrito"""
        try:
            from orders.models import Coupon
            from decimal import Decimal

            coupon = Coupon.objects.get(
                code__iexact=coupon_code.strip(),
                is_active=True
            )

            # Guardar en sesión (convertir a string para evitar problemas)
            self.session['applied_coupon'] = {
                'id': coupon.id,
                'code': coupon.code,
                'discount_value': str(coupon.discount_value),  # ← GUARDAR COMO STRING
                'discount_type': coupon.discount_type
            }
            self.session.modified = True
            return True, coupon

        except Coupon.DoesNotExist:
            return False, None

    def remove_coupon(self):
        """Remover cupón aplicado"""
        if 'applied_coupon' in self.session:
            del self.session['applied_coupon']
            self.session.modified = True

    def has_discount(self):
        """Verificar si hay un cupón aplicado"""
        return 'applied_coupon' in self.session

    def get_discount_amount(self):
        """Calcular el monto del descuento"""
        if not self.has_discount():
            return Decimal('0')  # ✅ Ahora Decimal está importado

        try:
            total = self.get_total_price()
            discount_value = Decimal(str(self.session['applied_coupon']['discount_value']))
            discount_type = self.session['applied_coupon']['discount_type']

            # ✅ CORREGIDO: 'PERCENTAGE' en mayúsculas
            if discount_type == 'PERCENTAGE':
                return total * (discount_value / Decimal('100'))
            else:  # FIXED_AMOUNT
                return min(discount_value, total)

        except (KeyError, ValueError, TypeError) as e:
            print(f"❌ Error calculando descuento: {e}")
            return Decimal('0')

    def get_total_with_discount(self):
        """Obtener el total después de aplicar descuento"""
        from decimal import Decimal
        total = self.get_total_price()

        if self.has_discount():
            discount_amount = self.get_discount_amount()
            return max(total - discount_amount, Decimal('0'))

        return total