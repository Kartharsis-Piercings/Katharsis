from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_session import Session
import json
import webbrowser
import os
import urllib.parse
import uuid
import re
import hashlib
import time
import requests
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta
from functools import lru_cache
import random
import gspread
from copy import deepcopy # deepcopy puede ser útil en algunas actualizaciones complejas
from google.auth.transport.requests import Request
#from google.oauth2.service_account import Credentials as ServiceAccountCredentials

# --- 1. INICIALIZACIÓN Y CONFIGURACIÓN ---

def format_content_text(text):
    """
    Convierte un bloque de texto con una notación simple a HTML.
    - Las líneas que empiezan con '## ' se convierten en subtítulos (<h4>).
    - El resto de líneas se envuelven en párrafos (<p>).
    """
    if not text:
        return ""
        
    html_output = []
    # Divide el texto en párrafos separados por una o más líneas en blanco
    paragraphs = re.split(r'\n\s*\n', text.strip())
    
    for para in paragraphs:
        # Elimina espacios extra al principio/final de cada párrafo
        clean_para = para.strip()
        if clean_para.startswith('## '):
            # Es un subtítulo. Le quitamos el '## ' y lo envolvemos en <h4>
            subtitle_text = clean_para[3:]
            html_output.append(f'<h4>{subtitle_text}</h4>')
        elif clean_para:
            # Es un párrafo normal. Lo envolvemos en <p>
            # Reemplazamos los saltos de línea simples por <br> para mantenerlos
            paragraph_html = clean_para.replace('\n', '<br>')
            html_output.append(f'<p>{paragraph_html}</p>')
            
    return "\n".join(html_output)

# Añadimos las definiciones que faltaban
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GUIDE_CARDS_FILE = os.path.join(BASE_DIR, 'guide_cards.json')
PORTFOLIO_FILE = os.path.join(BASE_DIR, 'portfolio.json') # <-- NUEVO
FEATURES_FILE = os.path.join(BASE_DIR, 'features.json')   # <-- NUEVO
INVENTORY_FILE = os.path.join(BASE_DIR, 'inventory.json')
APPOINTMENTS_FILE = os.path.join(BASE_DIR, 'appointments.json')
SERVICES_FILE = os.path.join(BASE_DIR, 'services.json')

def load_json_data(filepath, default_value=None):
    """Carga datos desde un archivo JSON de forma segura."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # CORRECCIÓN: Si no se especifica un valor por defecto, devolvemos una LISTA vacía,
        # que es lo que la mayoría de las funciones esperan.
        return default_value if default_value is not None else []
    
def save_json_data(filepath, data):
    """Guarda datos en un archivo JSON de forma segura."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error crítico al guardar en {filepath}: {e}")
# --- FIN DE LA CORRECCIÓN ---


app = Flask(__name__)

# Configuración SEGURA y PERSISTENTE de sesiones (Flask-Session)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key_for_dev')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'session_data')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=3)
# NOTA: Si desarrollas en local con HTTP (no HTTPS), la siguiente línea debe ser False.
# En producción (con HTTPS) debe ser True.
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
#app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=0)
# Inicializar Flask-Session
Session(app)

# Configuración de la aplicación
app.config['PRODUCTS_PER_PAGE'] = 12
app.config['PRODUCTS_FILE'] = 'products.json'
app.config['COUPONS_FILE'] = 'coupons.json'
app.jinja_env.filters['format_text'] = format_content_text

# --- LÓGICA DE CITAS ---

def load_appointments():
    """Carga la lista de citas."""
    return load_json_data(APPOINTMENTS_FILE, [])

def save_appointments(data):
    """Guarda la lista de citas."""
    save_json_data(APPOINTMENTS_FILE, data)

# Configuración de Servicios Disponibles
# Aquí definimos que la SEÑA siempre es 20 soles.
# Configuración de Servicios Disponibles
# Ahora incluimos el campo 'image' apuntando a la carpeta que creaste.

def load_services():
    """Carga los servicios desde el archivo JSON local."""
    try:
        with open(SERVICES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Advertencia: No se encontró services.json. Usando diccionario vacío.")
        return {}
    except json.JSONDecodeError:
        print("Error: services.json está corrupto.")
        return {}

# Cargamos los servicios al iniciar la app
SERVICES = load_services()


# --- 2. FILTROS Y FUNCIONES DE AYUDA ---


@app.template_filter('number_format')
def number_format(value):
    """
    Formatea un número a un string con dos decimales.
    Ej: 43 -> "43.00", 39.9 -> "39.90"
    """
    return f"{float(value):.2f}"

@lru_cache(maxsize=1)
def load_products_cached():
    try:
        with open(app.config['PRODUCTS_FILE'], 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_products(products):
    with open(app.config['PRODUCTS_FILE'], 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

@lru_cache(maxsize=1)
def load_coupons():
    try:
        with open(app.config['COUPONS_FILE'], 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@lru_cache(maxsize=1)
def load_inventory_cached():
    """Carga el archivo maestro de inventario (tops y bases)."""
    try:
        with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {} # Devuelve un dict vacío si no existe

def get_product_stock_levels(product, full_inventory):
    """
    Toma un producto del catálogo y le añade el diccionario 'stock'
    basado en el inventario real (Sistema Híbrido Avanzado).
    """
    
    # --- Sistema 1: Pieza Única (Aros, Nostrils, Navels) ---
    # Si el producto NO tiene 'gauge' o 'base_type', usa su propio 'stock'.
    if 'gauge' not in product or 'base_type' not in product:
        # El producto ya tiene su 'stock' (ej: {"8mm": 5, "10mm": 3})
        return product

    try:
        gauge = product['gauge']             # ej: "16G"
        base_type = product['base_type']     # ej: "labret"
        
        # Obtener el inventario de bases para este tipo
        available_bases = full_inventory.get(gauge, {}).get('bases', {}).get(base_type, {})
        new_stock_dict = {}

        # --- Sistema 2: Componente 1-Top (Labrets) ---
        if 'inventory_top_id' in product:
            top_id = product['inventory_top_id'] # ej: "top_16g_perla_3mm"
            top_stock = full_inventory.get(gauge, {}).get('tops', {}).get(top_id, {}).get('stock', 0)

            if top_stock <= 0:
                # Si el TOP está agotado, todas las bases están agotadas para este producto
                for base in available_bases.values():
                    new_stock_dict[base['size_label']] = 0
            else:
                # Si hay Tops, ver el stock de las BASES
                for base in available_bases.values():
                    available = min(top_stock, base.get('stock', 0))
                    new_stock_dict[base['size_label']] = available

        # --- Sistema 3: Componente 2-Tops (Bananas, Herraduras, Barras) ---
        elif 'inventory_top_ids' in product:
            top_ids = product.get('inventory_top_ids', []) # ej: ["top_16g_bola_4mm", "top_16g_bola_4mm"]
            
            # Contar cuántos de cada top se necesitan
            top_needs = {}
            for t_id in top_ids:
                top_needs[t_id] = top_needs.get(t_id, 0) + 1
            
            # Encontrar el stock limitante de los tops
            # ej: si necesitas 2 "top_bola" y hay 5 en stock, puedes hacer 5 / 2 = 2 joyas
            top_stock_limit = 999
            for top_id, count_needed in top_needs.items():
                stock_of_this_top = full_inventory.get(gauge, {}).get('tops', {}).get(top_id, {}).get('stock', 0)
                possible_sets = stock_of_this_top // count_needed
                if possible_sets < top_stock_limit:
                    top_stock_limit = possible_sets
            
            # Ahora, comprobar contra las bases
            for base in available_bases.values():
                # El stock es el mínimo entre los sets de tops y las bases
                available = min(top_stock_limit, base.get('stock', 0))
                new_stock_dict[base['size_label']] = available
                
        product['stock'] = new_stock_dict
        
    except Exception as e:
        print(f"Error al procesar stock para producto {product.get('id')}: {e}")
        product['stock'] = {}

    return product

# --- Meta ads API ---
def send_meta_capi_event(event_name, user_data_raw, custom_data):
    """
    Envía un evento del lado del servidor a la API de Conversiones de Meta.
    """
    access_token = os.environ.get("META_CAPI_ACCESS_TOKEN")
    pixel_id = os.environ.get("META_PIXEL_ID")

    if not access_token or not pixel_id:
        print("ERROR: Credenciales de la API de Conversiones de Meta no configuradas.")
        return

    url = f"https://graph.facebook.com/v19.0/{pixel_id}/events"
    
    # Prepara los datos del usuario, hasheando la información personal (PII)
    # Esto es un requisito de Meta para proteger la privacidad.
    user_data_hashed = {
        # Hasheamos todos los campos de texto
        "fn": hashlib.sha256(user_data_raw.get("first_name", "").encode()).hexdigest(),
        "ln": hashlib.sha256(user_data_raw.get("last_name", "").encode()).hexdigest(),
        "ph": hashlib.sha256(user_data_raw.get("phone", "").encode()).hexdigest(),
        "ct": hashlib.sha256(user_data_raw.get("city", "").lower().replace(" ", "")).hexdigest(),
        "st": hashlib.sha256(user_data_raw.get("state", "").lower().replace(" ", "")).hexdigest(),
        # El IP y User Agent no se hashean
        "client_ip_address": request.remote_addr,
        "client_user_agent": request.headers.get("User-Agent")
    }

    # Construye el payload final del evento
    event_payload = {
        "data": [
            {
                "event_name": event_name,
                "event_time": int(time.time()),
                "action_source": "website",
                "event_id": str(uuid.uuid4()), # ID único para evitar duplicados
                "user_data": user_data_hashed,
                "custom_data": custom_data
            }
        ],
        "access_token": access_token
    }

    try:
        response = requests.post(url, json=event_payload)
        response.raise_for_status()
        print(f"Evento '{event_name}' enviado a Meta CAPI con éxito.")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar evento a Meta CAPI: {e}")
        print("Respuesta del servidor:", response.text)

# --- Telegram Bot para ventas ---
def send_order_notification(message):
    """
    Envía un mensaje a un chat de Telegram a través de un Bot.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("ERROR: Credenciales de Telegram no configuradas en el archivo .env")
        return

    # La URL de la API de Telegram para enviar mensajes
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # El contenido del mensaje
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'  # Usaremos formato Markdown para que se vea mejor
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Lanza un error si la petición falla (ej. 4xx o 5xx)
        print("Notificación de Telegram enviada con éxito.")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar la notificación de Telegram: {e}")


# --- AQUÍ VAN TODAS TUS FUNCIONES DE LÓGICA (get_categories, etc.) ---
def get_categories(products):
    categories = sorted(set(product['category'] for product in products))
    return [{"id": cat, "name": cat.capitalize()} for cat in categories]

def get_body_parts(products):
    all_parts = set()
    for product in products:
        if 'body_parts' in product:
            for part in product['body_parts']:
                all_parts.add(part)
    return [{"id": part, "name": part.capitalize()} for part in sorted(all_parts)]

def get_materials(products):
    materials = sorted(set(product['material'] for product in products))
    return [{"id": mat, "name": mat.capitalize()} for mat in materials]

def get_filtered_products(products, filters):
    """
    Filtra los productos y maneja inteligentemente las incompatibilidades de filtros.
    """
    # 1. Aplicar todos los filtros iniciales
    filtered = list(products) # Usamos una copia para no modificar la lista original
    
    # Filtrar por precio primero, ya que siempre se aplica
    min_price = float(filters.get('min_price', 0))
    max_price = float(filters.get('max_price', 300))
    filtered = [p for p in filtered if min_price <= p.get('sale_price', p.get('price', 0)) <= max_price]
    
    # Aplicar filtro de categoría
    category_filter = filters.get('category')
    if category_filter and category_filter != 'all':
        filtered = [p for p in filtered if p['category'] == category_filter]
        
    # Aplicar filtro de zona del cuerpo
    body_part_filter = filters.get('body_part')
    if body_part_filter and body_part_filter != 'all':
        # Guardamos los resultados con el filtro de categoría antes de aplicar el de zona
        results_before_body_part = list(filtered) 
        
        filtered = [p for p in filtered if body_part_filter in p.get('body_parts', [])]
        
        # --- ¡AQUÍ ESTÁ LA LÓGICA INTELIGENTE! ---
        # Si después de aplicar el filtro de zona no hay resultados,
        # y antes sí los había, asumimos una incompatibilidad.
        if not filtered and results_before_body_part:
            # Anulamos el filtro de categoría y volvemos a filtrar desde el principio
            # solo por la zona del cuerpo (la última selección del usuario).
            temp_filtered = list(products) # Empezamos de nuevo con todos los productos
            temp_filtered = [p for p in temp_filtered if min_price <= p.get('sale_price', p.get('price', 0)) <= max_price]
            filtered = [p for p in temp_filtered if body_part_filter in p.get('body_parts', [])]
            
            # Actualizamos el diccionario de filtros para que el frontend sepa del cambio
            filters['category'] = 'all'

    # (Puedes aplicar la misma lógica inversa si filtras primero por zona y luego por categoría)
    
    # Aplicar filtro de material
    material_filter = filters.get('material')
    if material_filter and material_filter != 'all':
        filtered = [p for p in filtered if p['material'] == material_filter]

    return filtered

def sort_products(products, sort_by):
    """
    Ordena los productos según el criterio especificado.
    Usa 'sale_price' solo si el producto está en oferta ('on_sale' es true).
    """
    if sort_by == 'price_asc':
        # ¡LÓGICA CORREGIDA!
        return sorted(products, key=lambda p: p['sale_price'] if p.get('on_sale') else p['price'])
    elif sort_by == 'price_desc':
        # ¡LÓGICA CORREGIDA!
        return sorted(products, key=lambda p: p['sale_price'] if p.get('on_sale') else p['price'], reverse=True)
    elif sort_by == 'newest':
        # Se asume que los IDs más altos son los más nuevos
        return sorted(products, key=lambda p: p.get('id', 0), reverse=True)
    else: # 'popular' por defecto
        return sorted(products, key=lambda p: p.get('popularity', 0), reverse=True)

def initialize_cart():
    if 'cart' not in session:
        session['cart'] = {
            'id': str(uuid.uuid4()),
            'created_at': datetime.now().isoformat(),
            'cart_items': [],
            'coupon': None,
            'shipping_cost': 0,
            'shipping_region': None
        }
    return session['cart']

@app.route('/apply_coupon', methods=['POST'])
def apply_coupon():
    cart = initialize_cart()
    data = request.get_json()
    coupon_code = data.get('coupon_code', '').upper() # Convertimos a mayúsculas

    if not coupon_code:
        return jsonify({'error': 'Por favor, introduce un código de cupón.'}), 400

    all_coupons = load_coupons()
    coupon_to_apply = next((c for c in all_coupons if c['code'].upper() == coupon_code), None)

    # --- Validaciones del cupón ---
    if not coupon_to_apply:
        flash('El código del cupón no es válido.', 'danger')
        return jsonify({'error': 'Cupón no válido'}), 404

    if not coupon_to_apply.get('active', False):
        flash('Este cupón ya no está activo.', 'danger')
        return jsonify({'error': 'Cupón inactivo'}), 403

    if 'expiration' in coupon_to_apply:
        try:
            expiration_date = datetime.strptime(coupon_to_apply['expiration'], '%Y-%m-%d').date()
            if expiration_date < datetime.now().date():
                flash('Este cupón ha expirado.', 'danger')
                return jsonify({'error': 'Cupón expirado'}), 403
        except ValueError:
            pass # Ignora si el formato de fecha es incorrecto

    # Si pasa todas las validaciones, lo guardamos en la sesión
    cart['coupon'] = coupon_to_apply['code']
    session.modified = True
    flash(f"¡Cupón '{coupon_to_apply['code']}' aplicado con éxito!", 'success')
    
    return jsonify({'status': 'success'})

def get_cart_total(cart):
    # 1. Calcula el subtotal inicial
    subtotal = sum(item.get('price', 0) * item.get('quantity', 0) for item in cart.get('cart_items', []))

    # 2. Aplica el descuento del cupón al subtotal, si existe
    if cart.get('coupon'):
        coupons = load_coupons()
        coupon_data = next((c for c in coupons if c['code'] == cart['coupon']), None)
        if coupon_data:
            if coupon_data['type'] == 'percentage':
                subtotal -= subtotal * (coupon_data['discount'] / 100)
            elif coupon_data['type'] == 'fixed':
                subtotal -= coupon_data['discount']

    # 3. Calcula el costo de envío basado en el subtotal (ya con posible descuento)
    shipping_info = calculate_shipping(subtotal, cart.get('shipping_region'))
    cart['shipping_cost'] = shipping_info['cost']
    session.modified = True
    
    # 4. Calcula el total final. Esta línea ahora está fuera del 'if' y se ejecuta siempre.
    total = subtotal + cart['shipping_cost']
    
    return total
@lru_cache(maxsize=1)
def load_shipping_rules():
    """Carga las reglas de envío desde el archivo JSON."""
    try:
        with open('shipping.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Devuelve una estructura por defecto si el archivo no existe
        return {"promotions": [], "costs_by_region": {"default": 20.00}}
    

def calculate_shipping(cart_total, region=None):
    """Calcula el costo de envío basado en reglas de shipping.json.
    Prioridad: Promociones activas > Costo por región.
    """
    rules = load_shipping_rules()
    
    # 1. Revisar promociones activas
    for promo in rules.get("promotions", []):
        if promo.get("active") and cart_total >= promo.get("conditions", {}).get("min_cart_total", 0):
            if promo.get("type") == "free_shipping":
                # ¡Devolvemos el mensaje de la promo!
                return {'cost': 0, 'promo_message': promo.get('name', '¡Envío Gratis Aplicado!')}

    # 2.Si no hay promos, calculamos el costo normal
    cost = rules["costs_by_region"].get(region, rules["costs_by_region"]["default"]) if region else rules["costs_by_region"]["default"]
    return {'cost': cost, 'promo_message': None}
    
    # Si no se ha seleccionado región, devuelve el costo por defecto
    return rules["costs_by_region"]["default"]

# --- NUEVA FUNCIÓN 1: Cargar la información de piercings ---
@lru_cache(maxsize=1)
def load_piercings_info():
    """Carga los datos informativos de piercings desde el archivo JSON."""
    try:
        with open('piercings_info.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Devuelve una estructura vacía si el archivo no existe para evitar errores
        return {"body_zones": [], "important_info": []}

# --- NUEVA FUNCIÓN 2: Encontrar productos recomendados ---
def find_recommended_products(tags, all_products, limit=3):
    """
    Encuentra productos que coincidan con una lista de etiquetas.
    Prioriza los productos que coinciden con más etiquetas.
    (Versión corregida con lógica case-insensitive)
    """
    if not tags:
        return []

    scored_products = []
    for product in all_products:
        score = 0
        
        # LÍNEA MODIFICADA: .lower() para ignorar mayúsculas/minúsculas
        product_category = product.get('category', '').lower()
        product_material = product.get('material', '').lower()

        # Comprobar coincidencias en categoría y material
        if product_category in tags:
            score += 1
        if product_material in tags:
            score += 1
            
        # Comprobar coincidencias en zonas del cuerpo
        for part in product.get('body_parts', []):
            if part in tags:
                score += 1
                break 

        if score > 0:
            scored_products.append({'product': product, 'score': score})

    # Ordenar por puntuación (de mayor a menor) y luego por popularidad
    scored_products.sort(key=lambda x: (x['score'], x['product'].get('popularity', 0)), reverse=True)

    # Devolver solo los diccionarios de productos, hasta el límite especificado
    return [item['product'] for item in scored_products[:limit]]

# --- ¡NUEVA FUNCIÓN PARA CATEGORÍAS DESTACADAS! ---
def get_featured_categories(all_products, num_categories=7):
    """
    Selecciona las categorías más populares basadas en la popularidad de sus productos.
    """
    category_popularity = {}
    category_info = {}

    for product in all_products:
        category = product.get('category')
        if not category:
            continue

        popularity = product.get('popularity', 0)
        category_popularity[category] = category_popularity.get(category, 0) + popularity

        # Guardar info de la categoría (nombre, primera imagen encontrada, producto más popular)
        if category not in category_info:
            category_info[category] = {
                'name': category,
                'image': product.get('images', [''])[0],
                'most_popular_product_image': product.get('images', [''])[0],
                'max_popularity': popularity,
                'price_range': [product.get('price')]
            }
        else:
            category_info[category]['price_range'].append(product.get('price'))
            if popularity > category_info[category]['max_popularity']:
                category_info[category]['max_popularity'] = popularity
                category_info[category]['most_popular_product_image'] = product.get('images', [''])[0]

    # Ordenar categorías por popularidad total
    sorted_categories = sorted(category_popularity.items(), key=lambda item: item[1], reverse=True)
    
    featured = []
    for category_name, _ in sorted_categories[:num_categories]:
        info = category_info[category_name]
        # Calcular rango de precios
        prices = [p for p in info['price_range'] if p is not None]
        if prices:
            min_price = min(prices)
            info['price_string'] = f"Desde S/{min_price:.2f}"
        else:
            info['price_string'] = ""
        
        featured.append(info)

    return featured

# --- 3. RUTAS DE LA APLICACIÓN ---

@app.route('/')
def index():
    # Cargar todos los datos necesarios para la página de inicio
    all_products = load_products_cached()
    guide_cards_data = load_json_data(GUIDE_CARDS_FILE, {"cards": []})
    portfolio_data = load_json_data(PORTFOLIO_FILE, {"gallery_items": []})
    features_data = load_json_data(FEATURES_FILE, {"features": []})

    # Seleccionar las categorías destacadas dinámicamente
    featured_categories = get_featured_categories(all_products, num_categories=7)

    # Aleatorizar la galería de trabajos
    gallery_items = portfolio_data.get('gallery_items', [])
    random.shuffle(gallery_items)
    
    return render_template('index.html', 
                           guide_cards=guide_cards_data.get('cards', []),
                           gallery_items=gallery_items,
                           features=features_data.get('features', []),
                           featured_categories=featured_categories)

@app.route('/piercings')
def piercings():
    """
    Muestra la página informativa de piercings, enriquecida con productos recomendados.
    """
    # 1. Cargar ambos archivos de datos
    piercings_data = load_piercings_info()
    all_products = load_products_cached()

    # 2. Enriquecer los datos de piercings con productos recomendados
    # Se itera sobre 'guides' (la clave correcta) en lugar de 'body_zones'
    for guide in piercings_data.get('guides', []):
        # Se comprueba que la guía sea de tipo 'zone' antes de buscar piercings
        if guide.get('type') == 'zone':
            for piercing in guide.get('piercings', []):
                tags = piercing.get('recommended_product_tags', [])
                # Llama a la función para encontrar productos y los añade al diccionario del piercing
                piercing['recommended_products'] = find_recommended_products(tags, all_products)

    # 3. Enviar los datos completos a la plantilla
    return render_template('piercings.html', piercings_data=piercings_data)

def format_content_text(text):
    if not text:
        return ""

    html_output = []
    paragraphs = re.split(r'\n\s*\n', text.strip()) # Split by blank lines
    in_list = False

    for para in paragraphs:
        clean_para = para.strip()
        lines = clean_para.split('\n') # Split paragraph into lines

        # --- APPLY INLINE FORMATTING *BEFORE* JOINING/WRAPPING ---
        # Apply bold and underline to the raw paragraph text first
        formatted_para = clean_para # Start with the clean paragraph
        formatted_para = re.sub(r'\*(.*?)\*', r'<b>\1</b>', formatted_para, flags=re.DOTALL) # DOTALL allows matching across newlines within a paragraph
        formatted_para = re.sub(r'_(.*?)_', r'<u>\1</u>', formatted_para, flags=re.DOTALL) # DOTALL here too

        # Now re-split the *formatted* paragraph into lines for further processing
        lines = formatted_para.split('\n')

        # 1. Detect Subtítulos (using the first line of the formatted paragraph)
        if lines[0].strip().startswith('## '):
            if in_list:
                html_output.append('</ul>')
                in_list = False
            # Get subtitle text *after* ##, apply inline format again (safe, won't double format)
            subtitle_text = lines[0].strip()[3:]
            html_output.append(f'<h4>{subtitle_text}</h4>') # The text already has b/u tags

        # 2. Detect Listas (check if *original* lines started with '- ')
        elif all(original_line.strip().startswith('- ') for original_line in para.strip().split('\n') if original_line.strip()):
             if not in_list:
                 html_output.append('<ul>')
                 in_list = True
             # Iterate through the *formatted* lines now
             for line in lines:
                 if line.strip().startswith('- '): # Check the formatted line starts with '-'
                     item_text = line.strip()[2:] # Remove '- '
                     html_output.append(f'<li>{item_text}</li>') # item_text already has b/u tags

        # 3. Párrafos Normales
        elif formatted_para: # Use the formatted paragraph
            if in_list:
                html_output.append('</ul>')
                in_list = False
            # Join lines with <br>, the b/u tags are already present
            paragraph_html = '<br>'.join(lines)
            html_output.append(f'<p>{paragraph_html}</p>')

    if in_list:
        html_output.append('</ul>')

    return "\n".join(html_output)

# Ensure filter registration:
app.jinja_env.filters['format_text'] = format_content_text


@app.route('/servicios')
def servicios():
    return render_template('servicios.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    """
    Recibe los datos del formulario de contacto y envía una notificación a Telegram.
    """
    if not request.is_json:
        return jsonify({"status": "error", "message": "Formato de solicitud no válido."}), 400

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    subject = data.get('subject')
    message = data.get('message')

    # Validación básica en el servidor
    if not all([name, email, phone, subject, message]):
        return jsonify({"status": "error", "message": "Faltan campos por rellenar."}), 400

    # Formatear el mensaje para Telegram (usando formato HTML)
    telegram_message = (
        f"*📬 Nuevo Mensaje desde la Web*\n\n"
        f"*De:* {name}\n"
        f"*Email:* {email}\n"
        f"*Teléfono:* {phone}\n"
        f"*Asunto:* {subject}\n\n"
        f"*Mensaje:*\n {message}\n\n"
    )

    # Reutilizamos la función que ya debes tener para enviar notificaciones
    # Si no la tienes, asegúrate de que exista y funcione.
    send_contact_notification(telegram_message)
    
    return jsonify({"status": "success", "message": "¡Mensaje enviado con éxito! Te responderé pronto."})

# Asegúrate de que tu función send_telegram_notification exista
# Si no la tienes de antes, aquí está:
def send_contact_notification(message_text):
    """Envía un mensaje a un chat de Telegram específico."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN_2')  # Usamos un segundo token para evitar conflictos
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("ERROR: Variables de entorno de Telegram no configuradas.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message_text,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status() # Lanza un error si la petición falla
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar notificación a Telegram: {e}")
        return False

# --- AQUÍ ESTÁN TODAS TUS RUTAS QUE FALTABAN ---

@app.route('/joyas')
def joyas():
    all_products = load_products_cached()
    
    # --- LA CORRECCIÓN ESTÁ EN LA LÍNEA 'page' ---
    filters = {
        'category': request.args.get('category', 'all'),
        'body_part': request.args.get('body_part', 'all'),
        'material': request.args.get('material', 'all'),
        'min_price': request.args.get('min_price') or '0',
        'max_price': request.args.get('max_price') or '300',
        'sort_by': request.args.get('sort_by', 'popular'),
        'page': request.args.get('page', 1, type=int) # ¡CORREGIDO! El 1 ya no tiene comillas.
    }
    
    # Creamos un diccionario de filtros para la lógica, convirtiendo precios a números
    logic_filters = filters.copy()
    logic_filters['min_price'] = float(logic_filters['min_price'])
    logic_filters['max_price'] = float(logic_filters['max_price'])

    filtered_products = get_filtered_products(all_products, logic_filters)
    sorted_products = sort_products(filtered_products, filters['sort_by'])
    
    full_inventory = load_inventory_cached()
    enriched_products_list = []
    for product in sorted_products:
        # Esta función añade el stock real de 'inventory.json'
        enriched_products_list.append(
            get_product_stock_levels(product, full_inventory)
        )

    per_page = app.config['PRODUCTS_PER_PAGE']
    total_products = len(sorted_products)
    total_pages = (total_products + per_page - 1) // per_page
    
    # Esta línea ahora funcionará porque 'page' siempre será un entero
    page = max(1, min(filters['page'], total_pages)) if total_pages > 0 else 1
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    products_page = sorted_products[start_idx:end_idx]
    
    return render_template('joyas.html',
                           products=products_page,
                           categories=get_categories(all_products),
                           body_parts=get_body_parts(all_products),
                           materials=get_materials(all_products),
                           current_filters=filters, # Pasamos los filtros originales a la plantilla
                           page=page,
                           total_pages=total_pages,
                           total_products=total_products,
                           wishlist=session.get('wishlist', [])) # <-- AÑADIR ESTO

# --- ¡NUEVA RUTA API PARA ACTUALIZACIÓN DINÁMICA! ---
@app.route('/api/filter_products')
def api_filter_products():
    """
    Endpoint API que ahora soporta paginación.
    Devuelve los productos para una página específica y el total de páginas.
    """
    all_products = load_products_cached()
    
    # Recolecta los filtros, incluyendo el número de página
    page = request.args.get('page', 1, type=int)
    per_page = app.config['PRODUCTS_PER_PAGE']
    
    filters = {
        'category': request.args.get('category', 'all'),
        'body_part': request.args.get('body_part', 'all'),
        'material': request.args.get('material', 'all'),
        'min_price': float(request.args.get('min_price', 0)),
        'max_price': float(request.args.get('max_price', 300)),
        'sort_by': request.args.get('sort_by', 'popular')
    }

    # 1. Filtrar y ordenar productos (sin cambios)
    filtered_products = get_filtered_products(all_products, filters)
    sorted_products = sort_products(filtered_products, filters['sort_by'])
    
    #2. Enriquecer con niveles de stock reales
    full_inventory = load_inventory_cached()
    enriched_products_list = []
    for product in sorted_products:
        enriched_products_list.append(
            get_product_stock_levels(product, full_inventory)
        )
    
    # 3. Lógica de paginación
    total_products = len(sorted_products)
    total_pages = (total_products + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    products_for_page = sorted_products[start_idx:end_idx]
    
    sanitized_products = []
    for p in products_for_page:
        # Creamos una copia para no afectar la caché del servidor
        p_clean = p.copy()
        # Borramos el costo si existe
        p_clean.pop('costo', None) 
        # También podemos borrar otros datos internos si quieres
        p_clean.pop('inventory_top_id', None)
        p_clean.pop('inventory_top_ids', None)
        sanitized_products.append(p_clean)
    
    # 4. Devolver un objeto JSON con los productos Y la información de paginación
    return jsonify({
        'products': products_for_page,
        'total_pages': total_pages,
        'current_page': page
    })

@app.route('/api/product/<int:product_id>')
def api_get_product(product_id):
    products = load_products_cached()
    product = next((p for p in products if p['id'] == product_id), None)

    if product:

        product_clean = product.copy()
        product_clean.pop('costo', None) 
        # Si se encuentra el producto, devuélvelo como JSON
        return jsonify(product)
    else:
        # Si no se encuentra, devuelve un error 404 con un mensaje JSON
        return jsonify({'error': 'Producto no encontrado'}), 404

@app.route('/producto/<int:product_id>')
def product_detail(product_id):
    all_products = load_products_cached()
    
    # Encontrar el producto principal que se está viendo
    current_product = next((p for p in all_products if p['id'] == product_id), None)
    
    if not current_product:
        return render_template('404.html'), 404

    # --- INICIO DE LA NUEVA LÓGICA DE PRODUCTOS RELACIONADOS ---
    full_inventory = load_inventory_cached()
    current_product = get_product_stock_levels(
        current_product, full_inventory
    )

    scored_products = []
    current_body_parts = set(current_product.get('body_parts', []))
    current_category = current_product.get('category')

    for product in all_products:
        # No comparar el producto consigo mismo
        if product['id'] == current_product['id']:
            continue

        score = 0
        
        # +2 puntos si la categoría coincide
        if product.get('category') == current_category:
            score += 2
        
        # +1 punto si comparten al menos una zona del cuerpo
        product_body_parts = set(product.get('body_parts', []))
        if current_body_parts.intersection(product_body_parts):
            score += 1

        # Si el producto tiene alguna relevancia (puntuación > 0), lo añadimos a la lista
        if score > 0:
            scored_products.append({'product': product, 'score': score})

    # 1. Ordenar la lista por la puntuación más alta (relevancia)
    scored_products.sort(key=lambda x: x['score'], reverse=True)

    # 2. MEJORA: Selección Aleatoria Ponderada
    # Tomamos un "pool" de candidatos más grande (ej. los 12 mejores productos relacionados)
    # para evitar mostrar siempre los mismos 4 si hay muchos similares.
    top_candidates = scored_products[:12]
    
    # Si tenemos suficientes candidatos, elegimos 4 al azar de entre los mejores
    if len(top_candidates) > 4:
        selected_items = random.sample(top_candidates, 4)
    else:
        # Si hay pocos, los mostramos todos
        selected_items = top_candidates

    # Extraer solo los diccionarios de productos
    related_products = [item['product'] for item in selected_items]
    
    return render_template(
        'product_detail.html', 
        product=current_product, 
        related_products=related_products
    )
# --- RUTAS DE TERMINOS Y CONDICIONES ---

@app.route('/terminos-y-condiciones')
def terminos_y_condiciones():
    return render_template('terminos-y-condiciones.html')

@app.route('/cart')
def view_cart():
    cart = initialize_cart()
    products = load_products_cached()
    for item in cart['cart_items']:
        product = next((p for p in products if str(p['id']) == item['product_id']), None)
        if product:
            item['full_product'] = product
    
    subtotal = sum(item['price'] * item['quantity'] for item in cart['cart_items'])
    total = get_cart_total(cart)
    coupon = next((c for c in load_coupons() if c['code'] == cart['coupon']), None) if cart['coupon'] else None
    
    # --- LISTA DE DEPARTAMENTOS DE PERÚ ---
    regions = [
        "Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", 
        "Callao", "Cusco", "Huancavelica", "Huánuco", "Ica", "Junín", 
        "La Libertad", "Lambayeque", "Lima", "Loreto", "Madre de Dios", 
        "Moquegua", "Pasco", "Piura", "Puno", "San Martín", "Tacna", 
        "Tumbes", "Ucayali"
    ]
    # --- FIN DE LA LISTA DE DEPARTAMENTOS ---
    shipping_info = calculate_shipping(subtotal, cart.get('shipping_region'))
    cart['shipping_cost'] = shipping_info['cost']
    promo_message = shipping_info.get('promo_message')

    return render_template('cart.html', cart=cart, subtotal=subtotal, total=total, coupon=coupon, regions=regions, promo_message=promo_message)

@app.route('/checkout')
def checkout():
    cart = initialize_cart()
    if not cart['cart_items']:
        flash('Tu carrito está vacío', 'danger')
        return redirect(url_for('joyas'))
    
    subtotal = sum(item['price'] * item['quantity'] for item in cart['cart_items'])
    total = get_cart_total(cart)
    
    return render_template('checkout.html', cart=cart, subtotal=subtotal, total=total)

# --- RUTAS DE API Y ACCIONES DEL CARRITO ---

@app.route('/toggle_wishlist', methods=['POST'])
def toggle_wishlist():
    # Asegúrate de que la lista de deseos exista en la sesión
    if 'wishlist' not in session:
        session['wishlist'] = []

    data = request.get_json()
    product_id = data.get('product_id')

    if not product_id:
        return jsonify({'status': 'error', 'message': 'Falta product_id'}), 400

    # Si el producto ya está, lo quitamos. Si no, lo añadimos.
    if product_id in session['wishlist']:
        session['wishlist'].remove(product_id)
        status = 'removed'
    else:
        session['wishlist'].append(product_id)
        status = 'added'
    
    session.modified = True
    
    return jsonify({'status': 'success', 'action': status, 'wishlist': session['wishlist']})


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    cart = initialize_cart()
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    size = request.form.get('size') # ej: "8mm"
    
    if not size:
        return jsonify({'status': 'error', 'message': 'Por favor selecciona un tamaño'}), 400

    product = next((p for p in load_products_cached() if str(p['id']) == product_id), None)
    if not product:
        return jsonify({'status': 'error', 'message': 'Producto no encontrado'}), 404
    
    available_stock = 0
    inventory_links = None
    
    # --- CASO 1: Producto de Pieza Única (Aro, Nostril, Navel) ---
    if 'gauge' not in product:
        available_stock = product.get('stock', {}).get(size, 0)
    
    # --- CASO 2: Producto de Componentes (Labret, Banana, Herradura, Barra) ---
    else:
        full_inventory = load_inventory_cached()
        gauge = product.get('gauge')
        base_type = product.get('base_type')

        if not all([gauge, base_type]):
             return jsonify({'status': 'error', 'message': 'Producto mal configurado (falta gauge o base_type)'}), 500

        # 1. Encontrar la BASE por su 'size_label'
        all_bases_of_type = full_inventory.get(gauge, {}).get('bases', {}).get(base_type, {})
        target_base_key_value = next(
            (item for item in all_bases_of_type.items() if item[1].get('size_label') == size), 
            (None, None)
        )
        target_base_id = target_base_key_value[0]
        target_base_obj = target_base_key_value[1]
        
        if not target_base_obj:
            return jsonify({'status': 'error', 'message': f'El tamaño {size} no está disponible.'}), 404
        
        base_stock = target_base_obj.get('stock', 0)
        
        # 2. Encontrar el stock limitante de los TOPS
        top_stock_limit = 999
        
        # Sistema 2 (1-Top): Labret
        if 'inventory_top_id' in product:
            top_id = product['inventory_top_id']
            top_stock_limit = full_inventory.get(gauge, {}).get('tops', {}).get(top_id, {}).get('stock', 0)
            inventory_links = { "gauge": gauge, "top_ids": [top_id], "base_id": target_base_id, "base_type": base_type }

        # Sistema 3 (2-Tops): Banana, Herradura, Barra
        elif 'inventory_top_ids' in product:
            top_ids_needed = product.get('inventory_top_ids', []) # ej: ["top_bola", "top_bola"]
            top_needs = {}
            for t_id in top_ids_needed:
                top_needs[t_id] = top_needs.get(t_id, 0) + 1
            
            for top_id, count_needed in top_needs.items():
                stock_of_this_top = full_inventory.get(gauge, {}).get('tops', {}).get(top_id, {}).get('stock', 0)
                possible_sets = stock_of_this_top // count_needed
                if possible_sets < top_stock_limit:
                    top_stock_limit = possible_sets
            inventory_links = { "gauge": gauge, "top_ids": top_ids_needed, "base_id": target_base_id, "base_type": base_type }
        
        # El stock real es el mínimo de las dos piezas (Tops vs Base)
        available_stock = min(top_stock_limit, base_stock)

    # --- Validación de Carrito (lógica sin cambios) ---
    item_in_cart = next((item for item in cart['cart_items'] if item['product_id'] == product_id and item['size'] == size), None)
    quantity_in_cart = item_in_cart['quantity'] if item_in_cart else 0

    if available_stock < (quantity_in_cart + quantity):
        return jsonify({
            'status': 'error',
            'message': f'Stock insuficiente. Solo quedan {available_stock} unidades de este tamaño.'
        }), 400
    
    # --- Lógica para añadir al carrito (con una pequeña adición) ---
    if product.get('on_sale'):
        price = product.get('sale_price', product['price'])
    else:
        price = product['price']
    
    existing_item = next((item for item in cart['cart_items'] if item['product_id'] == product_id and item['size'] == size), None)

    if existing_item:
        existing_item['quantity'] += quantity
    else:
        new_item = {
            'product_id': product_id,
            'name': product['name'],
            'image': product['images'][0] if product.get('images') else '',
            'price': price,
            'quantity': quantity,
            'size': size,
            'original_price': product['price'],
            'material': product.get('material', 'N/A'),
            'body_parts': product.get('body_parts', []),
            'is_new': product.get('is_new', False),
            'on_sale': product.get('on_sale', False),
            'added_at': datetime.now().isoformat()
        }
        
        if inventory_links:
            new_item['inventory_links'] = inventory_links

        cart['cart_items'].append(new_item)
    
    session.modified = True
    return jsonify({'status': 'success', 'message': f'"{product["name"]}" añadido al carrito', 'cart_count': len(cart['cart_items'])})

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    cart = initialize_cart()
    data = request.get_json()
    if not data: 
        return jsonify({'status': 'error', 'message': 'No se recibieron datos'}), 400
 
    product_id = data.get('product_id')
    size = data.get('size')
    
    initial_count = len(cart['cart_items'])
    cart['cart_items'] = [item for item in cart['cart_items'] if not (item['product_id'] == product_id and item['size'] == size)]
    
    if len(cart['cart_items']) < initial_count:
        session.modified = True
        flash('Producto eliminado del carrito', 'success')
        return jsonify({'status': 'success', 'cart': cart, 'cart_count': len(cart['cart_items'])})
    else:
        flash('Ítem no encontrado en el carrito', 'danger')
        return jsonify({'status': 'error', 'cart': cart, 'cart_count': len(cart['cart_items'])})


@app.route('/update_cart_item', methods=['POST'])
def update_cart_item():
    cart = initialize_cart()
    data = request.get_json()

    product_id = data.get('product_id')
    size = data.get('size')
    new_quantity = int(data.get('quantity', 1))

    if new_quantity < 1:
        return jsonify({'status': 'error', 'message': 'Cantidad inválida'}), 400

    item_to_update = None
    for item in cart['cart_items']:
        if item['product_id'] == product_id and item['size'] == size:
            item['quantity'] = new_quantity
            item_to_update = item
            break

    if item_to_update:
        session.modified = True

        # --- CÁLCULOS CLAVE CORREGIDOS ---
        item_total = item_to_update['price'] * item_to_update['quantity']
        subtotal = sum(i['price'] * i['quantity'] for i in cart['cart_items'])

        # ¡NUEVO! Obtenemos la información de envío completa
        shipping_info = calculate_shipping(subtotal, cart.get('shipping_region'))
        shipping_cost = shipping_info.get('cost', 0)

        total = get_cart_total(cart) # get_cart_total ya considera el envío

        return jsonify({
            'status': 'success',
            'item_total': item_total,
            'subtotal': subtotal,
            'shipping_cost': shipping_cost, # Devolvemos el costo de envío
            'total': total,
            'promo_message': shipping_info.get('promo_message') # Y el mensaje de promo
        })
    else:
        return jsonify({'status': 'error', 'message': 'Ítem no encontrado'}), 404

@app.route('/update_shipping', methods=['POST'])
def update_shipping():
    cart = initialize_cart()
    data = request.get_json()
    region = data.get('region')

    if not region:
        return jsonify({'status': 'error', 'message': 'No se seleccionó ninguna región.'}), 400

    cart['shipping_region'] = region
    session.modified = True

    # --- CÁLCULOS CLAVE ---
    subtotal = sum(item.get('price', 0) * item.get('quantity', 0) for item in cart.get('cart_items', []))
    shipping_info = calculate_shipping(subtotal, region)
    cart['shipping_cost'] = shipping_info['cost']
    total = get_cart_total(cart)

    # La respuesta ahora incluye todos los datos que necesitamos
    return jsonify({
        'status': 'success',
        'subtotal': subtotal,
        'shipping_cost': cart['shipping_cost'],
        'total': total,
        'promo_message': shipping_info.get('promo_message')
    })

@app.route('/save_cart', methods=['POST'])
def save_cart():
    if 'cart' in session and session['cart']['cart_items']:
        # Guardamos el carrito actual en una clave diferente
        session['saved_cart'] = session['cart']
        # Opcional: Limpiar el carrito actual después de guardarlo
        session.pop('cart', None) 
        session.modified = True
        return jsonify({'status': 'success', 'message': '¡Tu carrito ha sido guardado!'})
    return jsonify({'status': 'error', 'message': 'Tu carrito está vacío.'}), 400

@app.route('/restore_cart', methods=['POST'])
def restore_cart():
    if 'saved_cart' in session:
        # Reemplaza el carrito actual (si existe) con el guardado
        session['cart'] = session.pop('saved_cart')
        session.modified = True
        return jsonify({'status': 'success', 'message': '¡Tu carrito ha sido restaurado!'})
    return jsonify({'status': 'error', 'message': 'No hay carritos guardados.'}), 404

@app.route('/process_order', methods=['POST'])
def process_order():
    """
    Recibe los datos del formulario de checkout, 'verifica' el pago,
    sincroniza con Google Sheets (Clientes y Ventas) y prepara notificación.
    """
    data = request.get_json()
    customer_info = data.get('customer_info')
    yape_code = data.get('yape_code')
    cart = session.get('cart', {})
    order_timestamp = datetime.now().strftime("%d/%m/%Y a las %I:%M %p")

    # --- 1. Validación simple ---
    if not all([customer_info, yape_code, cart.get('cart_items')]):
        return jsonify({'message': 'Faltan datos para procesar el pedido.'}), 400

    if len(yape_code) < 3:
        return jsonify({'message': 'El código de Yape parece inválido.'}), 400

    # ==================================================================
    # BLOQUE DE SINCRONIZACIÓN CON GOOGLE SHEETS
    # ==================================================================
    sale_id_generated = f"V-{uuid.uuid4().hex[:6].upper()}" # Genera ID tipo V-1BDFC8
    final_client_id = "Pendiente"

    try:
        # A. Preparar datos para el registro de cliente
        # Adaptamos lo que viene del carrito para que funcione con find_or_create_client
        client_data_for_sheet = {
            'name': customer_info['name'],
            'phone': customer_info['phone'],
            'dni': customer_info.get('dni', ''), # Puede venir vacío o con ceros
            'dob': '', # El carrito no pide fecha de nacimiento
            'consent_offers': customer_info.get('consent_offers', False)
        }
        
        # B. Obtener/Crear Cliente (Devuelve el DNI o ID Web)
        final_client_id = find_or_create_client(client_data_for_sheet)
        
        # C. Registrar la Venta en la hoja "Registro_Ventas"
        register_sale_in_sheets(sale_id_generated, customer_info, cart, final_client_id)
        
    except Exception as e:
        # Si falla Google Sheets, NO detenemos la venta, solo lo registramos en consola
        print(f"ADVERTENCIA: Error sincronizando con Sheets: {e}")

    # ==================================================================
    # INICIO: LÓGICA DE DESCUENTO DE STOCK (Tu código original intacto)
    # ==================================================================
    inventory_data = load_json_data(INVENTORY_FILE, {})
    products_data = load_json_data(app.config['PRODUCTS_FILE'], [])
    products_json_changed = False
    
    for item in cart['cart_items']:
        quantity_to_deduct = item['quantity']
        
        # --- CASO 1: Producto de Componentes (Labret, Banana, etc.) ---
        if 'inventory_links' in item:
            links = item['inventory_links']
            gauge = links['gauge']
            base_type = links['base_type']
            base_id = links['base_id']
            top_ids_to_deduct = links.get('top_ids', []) 
            
            try:
                # A. Descontar stock de la BASE
                base_stock = inventory_data[gauge]['bases'][base_type][base_id]['stock']
                inventory_data[gauge]['bases'][base_type][base_id]['stock'] = max(0, base_stock - quantity_to_deduct)
                
                # B. Descontar stock de los TOPS
                for top_id in top_ids_to_deduct:
                    top_stock = inventory_data[gauge]['tops'][top_id]['stock']
                    inventory_data[gauge]['tops'][top_id]['stock'] = max(0, top_stock - quantity_to_deduct)
                    
            except KeyError as e:
                print(f"ERROR: No se pudo descontar stock. Enlace de inventario roto: {e}")
            
        # --- CASO 2: Producto de Pieza Única (Aro, Nostril, Navel) ---
        else:
            product_id = item['product_id']
            size = item['size']
            product_to_update = next((p for p in products_data if str(p['id']) == product_id), None)
            
            if product_to_update and size in product_to_update.get('stock', {}):
                current_stock = product_to_update['stock'][size]
                product_to_update['stock'][size] = max(0, current_stock - quantity_to_deduct)
                products_json_changed = True
            else:
                print(f"ERROR: No se pudo descontar stock para pieza única ID {product_id}, Talla {size}")

    # --- Guardar los archivos de inventario actualizados ---
    try:
        save_json_data(INVENTORY_FILE, inventory_data)
        if products_json_changed:
            save_json_data(app.config['PRODUCTS_FILE'], products_data)
    except Exception as e:
        print(f"ERROR CRÍTICO: No se pudo guardar el inventario actualizado: {e}")
        
    # --- FIN: LÓGICA DE DESCUENTO DE STOCK ---
    
    # --- 3. Preparar el mensaje de WhatsApp para ti ---
    total = get_cart_total(cart)
    items_text = ""
    for item in cart['cart_items']:
        items_text += f"- {item['name']} (Tamaño: {item['size']}, Cant: {item['quantity']}) - S/ {item['price'] * item['quantity']}\n"
        if item.get('message'):
            items_text += f"  📝 Mensaje: {item['message']}\n"

    # Mensaje Actualizado con los IDs de gestión
    message_to_owner = (f"""
        *NUEVO PEDIDO WEB 🛍️*
        Fecha: {order_timestamp}
        *ID Venta:* `{sale_id_generated}`
        *ID Cliente:* `{final_client_id}`
        *Yape:* `{yape_code}`

        *Cliente:*
        - Nombre: {customer_info.get('name')}
        - DNI: {customer_info.get('dni')}
        - Cel: {customer_info.get('phone')}
        - Dirección: {customer_info.get('address')}, {customer_info.get('city')}

        *Resumen:*
        {items_text}
        *Subtotal:* S/ {sum(i['price'] * i['quantity'] for i in cart['cart_items'])}
        *Envío:* S/ {cart.get('shipping_cost', 0)}
        *TOTAL PAGADO:* *S/ {total}*

        *Consentimientos:*
        - Compras: {'Sí' if customer_info.get('consent_purchase') else 'No'}
        - Ofertas: {'Sí' if customer_info.get('consent_offers') else 'No'}
            """.strip())

    # --- INICIO: Bloque para enviar evento a Meta CAPI ---
    try:
        full_name = customer_info.get("name", "").split()
        first_name = full_name[0] if full_name else ""
        last_name = " ".join(full_name[1:]) if len(full_name) > 1 else ""

        user_data_for_meta = {
            "first_name": first_name,
            "last_name": last_name,
            "phone": customer_info.get("phone", ""),
            "city": customer_info.get("city", ""),
            "state": customer_info.get("region", "")
        }

        custom_data_for_meta = {
            "currency": "PEN",
            "value": get_cart_total(cart),
            "content_ids": [item['product_id'] for item in cart['cart_items']],
            "contents": [
                {"id": item['product_id'], "quantity": item['quantity']} for item in cart['cart_items']
            ],
            "num_items": len(cart['cart_items']),
            "order_id": sale_id_generated # Agregamos el ID de venta a Meta también
        }

        send_meta_capi_event(
            event_name="Purchase",
            user_data_raw=user_data_for_meta,
            custom_data=custom_data_for_meta
        )
    except Exception as e:
        print(f"No se pudo enviar el evento a Meta CAPI. Error: {e}")
    # --- FIN: Bloque Meta CAPI ---

    # --- 4. Enviar notificación ---
    send_order_notification(message_to_owner)
    
    # --- 5. Limpiar sesión ---
    session.pop('cart', None)
    session.pop('saved_cart', None) 
    session.modified = True

    return jsonify({
        'message': '¡Pedido confirmado! Redirigiendo...',
        'redirect_url': url_for('index') 
    })

# --- RUTA PARA GUARDAR MENSAJES PERSONALIZADOS EN EL CARRITO ---
@app.route('/update_cart_message', methods=['POST'])
def update_cart_message():
    cart = initialize_cart()
    data = request.get_json()
    
    product_id = data.get('product_id')
    size = data.get('size')
    message = data.get('message', '')

    # Buscamos el ítem en el carrito y le añadimos/actualizamos el mensaje
    for item in cart.get('cart_items', []):
        if item['product_id'] == product_id and item['size'] == size:
            item['message'] = message
            session.modified = True
            return jsonify({'status': 'success', 'message': 'Mensaje guardado.'})
            
    return jsonify({'status': 'error', 'message': 'Ítem no encontrado.'}), 404


# --- RUTAS DE PRUEBA DE SESIÓN ---

@app.route('/test-session')
def test_session():
    session['test_value'] = 'hola mundo'
    print("--- /test-session: Se ha establecido session['test_value'] = 'hola mundo' ---")
    return "Valor de prueba establecido en la sesión. Ahora ve a /check-session"

@app.route('/check-session')
def check_session():
    test_value = session.get('test_value', 'NO ESTABLECIDO')
    print(f"--- /check-session: El valor de session['test_value'] es: {test_value} ---")
    return f"El valor de 'test_value' en la sesión es: {test_value}"


# --- 4. PUNTO DE ENTRADA DE LA APLICACIÓN ---
@app.route('/agendar')
def booking_page():
    # Renderiza la página de reservas
    return render_template('booking.html', services=SERVICES)

@app.route('/api/available_slots')
def get_available_slots():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify([])

    # 1. TUS HORARIOS BASE
    base_slots = [
        "10:00", "11:00", "12:00", "13:00", 
        "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"
    ]

    try:
        # 2. Leer TODA la hoja como una matriz simple (lista de listas)
        # Esto evita el error "index out of range" por encabezados malformados
        sheet = get_google_sheet()
        rows = sheet.get_all_values() # <--- Cambio clave
        
        occupied_slots = []
        
        # 3. Recorrer filas (saltando la primera que es el encabezado)
        for i, row in enumerate(rows):
            if i == 0: continue 
            
            # Protección: Si la fila está vacía o tiene menos de 7 columnas, la saltamos
            if not row or len(row) < 7: 
                continue

            # Mapeo manual de columnas (A=0, B=1, C=2...)
            # B: Fecha (Index 1)
            # C: Hora (Index 2)
            # G: Estado (Index 6)
            
            row_date = str(row[1]).strip()
            row_time = str(row[2]).strip()
            row_status = str(row[6]).strip()

            # Lógica de filtrado
            if row_date == date_str:
                if row_status not in ['CANCELLED', 'RECHAZADA', 'No Asistió']:
                    occupied_slots.append(row_time)

        # 4. Calcular disponibles
        available = [slot for slot in base_slots if slot not in occupied_slots]
        
        return jsonify(available)

    except Exception as e:
        print(f"Error Sheets CRÍTICO: {e}")
        # En caso de error, devolvemos los base_slots para no bloquear la venta,
        # o una lista vacía si prefieres seguridad total.
        return jsonify(base_slots)

# ==========================================
# LÓGICA DE CLIENTES Y RESERVAS
# ==========================================

def get_clients_sheet():
    """Conecta a la pestaña de Clientes."""
    gc = gspread.service_account(filename="service_account.json")
    return gc.open("Katharsis_Gestor").worksheet("Clientes")

def register_sale_in_sheets(sale_id, customer_info, cart, client_id):
    """
    Registra la venta forzando la escritura desde la columna A.
    """
    try:
        # 1. Conexión
        agenda_ws = get_google_sheet()
        spreadsheet = agenda_ws.spreadsheet
        ws = spreadsheet.worksheet("Registro_Ventas")
        
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notes = f"Venta Web: {customer_info.get('city', 'Peru')}"
        
        # 2. Preparar las filas de datos
        rows_to_add = []
        for item in cart['cart_items']:
            total_price = item['price'] * item['quantity']
            row = [
                sale_id,                            # A
                current_date,                       # B
                str(client_id),                     # C
                customer_info['name'],              # D
                "Producto",                         # E
                item['product_id'],                 # F
                item['name'],                       # G
                item['size'],                       # H
                item['quantity'],                   # I
                item['price'],                      # J
                total_price,                        # K
                "",                                 # L (Costo)
                "Yape Web",                         # M
                notes                               # N
            ]
            rows_to_add.append(row)

        # 3. ENCONTRAR LA PRIMERA FILA VACÍA REAL
        # Obtenemos toda la columna A para ver dónde termina
        col_a_values = ws.col_values(1) 
        first_empty_row = len(col_a_values) + 1
        
        # 4. DEFINIR EL RANGO EXACTO PARA ESCRIBIR
        # Desde A{fila} hasta N{fila + n_items}
        start_cell = f"A{first_empty_row}"
        end_cell = f"N{first_empty_row + len(rows_to_add) - 1}"
        range_to_update = f"{start_cell}:{end_cell}"
        
        # 5. ESCRIBIR LOS DATOS EN ESE RANGO
        ws.update(range_to_update, rows_to_add)
        
        print(f"✅ Venta {sale_id} registrada correctamente en filas {first_empty_row}-{first_empty_row + len(rows_to_add) - 1}.")
        
    except Exception as e:
        print(f"❌ Error registrando venta en Sheets: {e}")

def find_or_create_client(data):
    """
    Lógica MAESTRA de Clientes (Versión Final Blindada):
    1. Admite ceros a la izquierda (fuerza string).
    2. Funciona para Agenda (con DOB) y Carrito (sin DOB).
    3. Busca por DNI o Nombre.
    4. Si encuentra: Actualiza ID temporal (CLI-xxx) por DNI real y llena huecos vacíos.
    5. Si no encuentra: Crea uno nuevo con soporte de consentimiento.
    """
    try:
        sheet = get_clients_sheet()
        records = sheet.get_all_records()
        
        # 1. LIMPIEZA DE DATOS (Vital para los ceros a la izquierda)
        # Convertimos todo a string explícitamente para que '0123' no sea 123
        input_dni = str(data.get('dni', '')).strip()
        input_name = str(data['name']).strip().lower()
        input_phone = str(data['phone']).strip()
        
        # Manejo de Consentimiento (Viene del carrito, por defecto No)
        input_consent = "Sí" if data.get('consent_offers') else "No"
        
        # 2. MANEJO HÍBRIDO DE FECHA (Agenda vs Carrito)
        input_dob_sheet = ""
        if data.get('dob'): # Solo si la fecha existe (Agenda)
            try:
                # Convertir de YYYY-MM-DD (HTML) a DD/MM/YYYY (Excel)
                input_dob_sheet = datetime.strptime(data['dob'], "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                input_dob_sheet = data['dob'] # Fallback
        
        # Variables para búsqueda
        found_index = -1
        existing_row = None

        # 3. ALGORITMO DE BÚSQUEDA
        for i, row in enumerate(records):
            # Forzamos string en los datos del Excel para comparar texto con texto
            row_dni = str(row.get('ID_Cliente_DNI', '')).strip()
            row_name = str(row.get('Nombre_Completo', '')).strip().lower()
            
            # A) Coincidencia EXACTA por DNI
            if input_dni and row_dni == input_dni:
                found_index = i
                existing_row = row
                break
            
            # B) Coincidencia por NOMBRE (Solo si nombre es largo, para evitar falsos positivos)
            if len(input_name) > 3 and row_name == input_name:
                found_index = i
                existing_row = row
                break
                
        # 4. ESCENARIO: CLIENTE ENCONTRADO (Actualizar y Rellenar)
        if existing_row:
            print(f"Cliente existente encontrado: {existing_row['Nombre_Completo']}")
            
            # Calculamos fila en Excel (Índice + 2 por encabezado)
            row_num = found_index + 2 
            
            current_id = str(existing_row.get('ID_Cliente_DNI', ''))
            final_id = current_id

            # --- A. REEMPLAZO DE ID TEMPORAL ---
            # Si tiene ID temporal (CLI- o WEB-) Y ahora nos dio un DNI real
            if (current_id.upper().startswith('CLI-') or current_id.upper().startswith('WEB-')) and input_dni:
                print(f"ACTUALIZANDO: ID temporal {current_id} -> DNI {input_dni}")
                sheet.update_cell(row_num, 1, input_dni) # Col 1: ID
                final_id = input_dni

            # --- B. SMART FILL (Rellenar huecos) ---
            # Si falta teléfono en Excel y lo tenemos ahora
            if not existing_row.get('Telefono') and input_phone:
                sheet.update_cell(row_num, 3, input_phone) # Col 3: Telefono
                
            # Si falta Cumpleaños en Excel y lo tenemos ahora (viene de Agenda)
            excel_dob = existing_row.get('Fec. Nacimiento (DD/MM/YYYY)', '')
            if not excel_dob and input_dob_sheet:
                sheet.update_cell(row_num, 5, input_dob_sheet) # Col 5: Nacimiento

            return final_id

        # 5. ESCENARIO: CLIENTE NUEVO (Crear)
        else:
            print("Cliente nuevo. Registrando...")
            
            # Generar ID: DNI si existe, sino WEB-UUID
            final_id = input_dni if input_dni else f"WEB-{uuid.uuid4().hex[:6].upper()}"
            
            # Orden Columnas: [ID, Nombre, Telefono, Email, Nacimiento, Registro, Consentimiento]
            new_row = [
                str(final_id),          # Aseguramos texto
                data['name'].title(),   # Nombre bonito
                input_phone,
                "",                     # Email (vacío)
                input_dob_sheet,        # Fecha nac (o vacío si es carrito)
                datetime.now().strftime("%Y-%m-%d"), # Fecha Registro
                input_consent           # Consentimiento
            ]
            
            sheet.append_row(new_row)
            return final_id

    except Exception as e:
        print(f"Error en lógica de clientes: {e}")
        # Retorno de seguridad para no romper el flujo de venta/agenda
        return data.get('dni') or f"ERR-{data.get('name')[:3]}"

# --- CONFIGURACIÓN GOOGLE SHEETS ---
def get_google_sheet():
    """Conecta con Google Sheets usando la autenticación moderna de gspread."""
    try:
        # Método moderno: gspread busca y autentica solo con el archivo JSON
        gc = gspread.service_account(filename="service_account.json")
        
        # Abre la hoja. ¡RECUERDA PONER EL NOMBRE DE TU ARCHIVO DE DRIVE!
        sheet = gc.open("Katharsis_Gestor").worksheet("Agenda_Unificada")
        return sheet
    except Exception as e:
        print(f"Error CRÍTICO conectando a Google Sheets: {e}")
        # Lanzamos el error para verlo en consola si falla
        raise e

# --- RUTA DE RESERVA ACTUALIZADA ---
@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    data = request.get_json()
    
    # Validar campos (incluyendo el nuevo 'client_dob')
    required = ['service_id', 'date', 'time', 'client_name', 'client_phone', 'client_dob', 'yape_code']
    if not all(k in data for k in required):
        return jsonify({'status': 'error', 'message': 'Faltan datos obligatorios.'}), 400

    try:
        # 1. BUSCAR O REGISTRAR CLIENTE
        client_data = {
            'name': data['client_name'],
            'phone': data['client_phone'],
            'dni': data.get('client_dni', ''),
            'dob': data['client_dob']
        }
        
        # Esta función nos devuelve el ID (DNI real o generado)
        final_client_id = find_or_create_client(client_data)
        
        # 2. PREPARAR CITA
        appt_id = str(uuid.uuid4())[:8]
        service_info = SERVICES.get(data['service_id'], {})
        
        full_data = {
            "id": appt_id,
            "source": "WEB",
            "status": "CONFIRMED", 
            "date": data['date'],
            "time": data['time'],
            "service": service_info.get('name', 'Servicio'),
            "client_name": data['client_name'],
            "client_id": final_client_id, # Guardamos el ID enlazado
            "phone": data['client_phone'],
            "deposit": 20.00,
            "yape": data['yape_code']
        }

        # 3. GUARDAR EN AGENDA (Google Sheets)
        # Orden: ID, Fecha, Hora, Servicio, Cliente(Nombre), Tel, Estado, Seña, Yape, JSON
        # NOTA: En la columna E (Cliente) guardamos el NOMBRE para que sea legible en el Excel,
        # pero en el JSON de respaldo guardamos el ID para el sistema.
        row = [
            full_data['id'],
            full_data['date'],
            full_data['time'],
            full_data['service'],
            full_data['client_name'],
            full_data['phone'],
            full_data['status'],
            full_data['deposit'],
            full_data['yape'],
            json.dumps(full_data)
        ]
        
        sheet = get_google_sheet()
        sheet.append_row(row)

        # 4. NOTIFICACIÓN TELEGRAM
        msg = (f"📅 *NUEVA CITA WEB*\n\n"
               f"👤 *Cliente:* {full_data['client_name']} (ID: {final_client_id})\n"
               f"🎂 *Cumple:* {data['client_dob']}\n"
               f"💎 *Servicio:* {full_data['service']}\n"
               f"🗓 *Fecha:* {full_data['date']} a las {full_data['time']}\n"
               f"💰 *Seña:* S/ 20.00 (Yape: `{full_data['yape']}`)")
        
        send_order_notification(msg)

        return jsonify({'status': 'success', 'message': 'Cita registrada.', 'redirect_url': url_for('index')})

    except Exception as e:
        print(f"Error crítico al agendar: {e}")
        return jsonify({'status': 'error', 'message': 'Error de conexión. Intenta de nuevo.'}), 500
    
if __name__ == '__main__':
    session_dir = app.config['SESSION_FILE_DIR']
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        print(f"Directorio de sesiones '{session_dir}' creado.")
    
    app.run(debug=True, port=5000)


   