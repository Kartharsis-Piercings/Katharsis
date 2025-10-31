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
from copy import deepcopy # deepcopy puede ser útil en algunas actualizaciones complejas

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

def load_json_data(filepath, default_value=None):
    """Carga datos desde un archivo JSON de forma segura."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # CORRECCIÓN: Si no se especifica un valor por defecto, devolvemos una LISTA vacía,
        # que es lo que la mayoría de las funciones esperan.
        return default_value if default_value is not None else []
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
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=1)
# Inicializar Flask-Session
Session(app)

# Configuración de la aplicación
app.config['PRODUCTS_PER_PAGE'] = 12
app.config['PRODUCTS_FILE'] = 'products.json'
app.config['COUPONS_FILE'] = 'coupons.json'
app.jinja_env.filters['format_text'] = format_content_text

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
    
    # 2. Lógica de paginación
    total_products = len(sorted_products)
    total_pages = (total_products + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    products_for_page = sorted_products[start_idx:end_idx]
    
    # 3. Devolver un objeto JSON con los productos Y la información de paginación
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

    # Ordenar la lista por la puntuación más alta
    scored_products.sort(key=lambda x: x['score'], reverse=True)

    # Extraer solo los productos y limitar a los 4 mejores
    related_products = [item['product'] for item in scored_products[:4]]
    
    # --- FIN DE LA NUEVA LÓGICA ---

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
    size = request.form.get('size')
    
    if not size:
        return jsonify({'status': 'error', 'message': 'Por favor selecciona un tamaño'}), 400

    product = next((p for p in load_products_cached() if str(p['id']) == product_id), None)
    if not product:
        return jsonify({'status': 'error', 'message': 'Producto no encontrado'}), 404
    
    # --- INICIO DE LA VALIDACIÓN DE STOCK ---
    available_stock = product.get('stock', {}).get(size, 0)

    # Considerar también el stock que ya está en el carrito
    item_in_cart = next((item for item in cart['cart_items'] if item['product_id'] == product_id and item['size'] == size), None)
    quantity_in_cart = item_in_cart['quantity'] if item_in_cart else 0

    if available_stock < (quantity_in_cart + quantity):
        return jsonify({
            'status': 'error',
            'message': f'Stock insuficiente. Solo quedan {available_stock} unidades de este tamaño.'
        }), 400
    # --- FIN DE LA VALIDACIÓN DE STOCK ---

    # --- Lógica de precios corregida ---
    if product.get('on_sale'):
        price = product.get('sale_price', product['price'])
    else:
        price = product['price']
    existing_item = next((item for item in cart['cart_items'] if item['product_id'] == product_id and item['size'] == size), None)

    if existing_item:
        existing_item['quantity'] += quantity
    else:
        cart['cart_items'].append({
            'product_id': product_id,
            'name': product['name'],
            'image': product['images'][0] if product.get('images') else '',
            'price': price, # Este ya es el precio de oferta si aplica
            'original_price': product['price'], # Guardamos el precio original para el badge
            'quantity': quantity,
            'size': size,
            'material': product.get('material', 'N/A'), # Añadimos material
            'body_parts': product.get('body_parts', []), # Añadimos zonas del cuerpo
            'is_new': product.get('is_new', False), # Añadimos si es nuevo
            'on_sale': product.get('on_sale', False), # Añadimos si está en oferta
            'added_at': datetime.now().isoformat()
        })
    
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
    Recibe los datos del formulario de checkout, 'verifica' el pago
    y prepara una notificación por WhatsApp.
    """
    data = request.get_json()
    customer_info = data.get('customer_info')
    yape_code = data.get('yape_code')
    cart = session.get('cart', {})
    order_timestamp = datetime.now().strftime("%d/%m/%Y a las %I:%M %p")

    # --- 1. Validación simple ---
    if not all([customer_info, yape_code, cart.get('cart_items')]):
        return jsonify({'message': 'Faltan datos para procesar el pedido.'}), 400

    # --- 2. Simulación de Verificación de Yape ---
    # En un caso real, aquí conectarías con la API de Yape o un sistema de verificación.
    # Por ahora, simularemos que cualquier código de más de 5 caracteres es válido.
    if len(yape_code) < 3 > 5:
        return jsonify({'message': 'El código de Yape parece inválido.'}), 400

    # --- 3. Preparar el mensaje de WhatsApp para ti ---
    total = get_cart_total(cart)
    items_text = ""
    for item in cart['cart_items']:
        items_text += f"- {item['name']} (Tamaño: {item['size']}, Cant: {item['quantity']}) - S/ {item['price'] * item['quantity']}\n"
        # Si el ítem tiene un mensaje, lo añadimos
        if item.get('message'):
            items_text += f"  📝 Mensaje: {item['message']}\n"
    # URL-encode para el mensaje de Telegram
    message_to_owner = (f"""

Fecha del Pedido: {order_timestamp}
*Código de Pedido:* `{cart.get('id', 'N/A')[:8]}`
*Código Yape (VERIFICADO):* `{yape_code}`

*Cliente:*
- *Nombre:* {customer_info.get('name')}
- *DNI:* {customer_info.get('dni')}
- *Celular:* {customer_info.get('phone')}
- *Dirección:* {customer_info.get('address')}, {customer_info.get('city')}, {customer_info.get('region')}

*Resumen del Carrito:*
{items_text}
*Subtotal:* S/ {sum(i['price'] * i['quantity'] for i in cart['cart_items'])}
*Envío:* S/ {cart.get('shipping_cost', 0)}
*TOTAL PAGADO:* *S/ {total}*

*Consentimientos:*
- *Notificaciones de compra:* {'Sí' if customer_info.get('consent_purchase') else 'No'}
- *Ofertas y promociones:* {'Sí' if customer_info.get('consent_offers') else 'No'}

*Acción requerida: Prepara el paquete y coordina el envío.*
    """.strip())

    # --- INICIO: Bloque para enviar evento a Meta CAPI ---
    try:
        # 1. Preparamos los datos del usuario (dividiendo el nombre)
        full_name = customer_info.get("name", "").split()
        first_name = full_name[0] if full_name else ""
        last_name = " ".join(full_name[1:]) if len(full_name) > 1 else ""

        user_data_for_meta = {
            "first_name": first_name,
            "last_name": last_name,
            "phone": customer_info.get("phone", ""),
            "city": customer_info.get("city", ""),
            "state": customer_info.get("region", "")
            # Nota: Sería ideal añadir un campo de email en tu formulario para mejorar el matching.
        }

        # 2. Preparamos los datos de la compra
        custom_data_for_meta = {
            "currency": "PEN",
            "value": get_cart_total(cart),
            "content_ids": [item['product_id'] for item in cart['cart_items']],
            "contents": [
                {"id": item['product_id'], "quantity": item['quantity']} for item in cart['cart_items']
            ],
            "num_items": len(cart['cart_items'])
        }

        # 3. Enviamos el evento 'Purchase'
        send_meta_capi_event(
            event_name="Purchase",
            user_data_raw=user_data_for_meta,
            custom_data=custom_data_for_meta
        )
    except Exception as e:
        print(f"No se pudo enviar el evento a Meta CAPI. Error: {e}")
    # --- FIN: Bloque para enviar evento a Meta CAPI ---

    # --- 4. Abrir WhatsApp Web con el mensaje (en el servidor) ---
    # CAMBIA '51999888777' por tu número de WhatsApp en formato internacional
    send_order_notification(message_to_owner)
    
    # --- 5. Limpiar el carrito y responder al cliente ---
    session.pop('cart', None)
    session.pop('saved_cart', None) # También limpiar el guardado por si acaso
    session.modified = True

    # Aquí también podrías enviar un mensaje de confirmación al cliente si tienes una API
    # ...

    # Devuelve una respuesta exitosa al frontend
    return jsonify({
        'message': '¡Pago verificado con éxito! Tu pedido ha sido confirmado. Serás redirigido en breve.',
        'redirect_url': url_for('index') # O una página de "gracias por tu compra"
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

if __name__ == '__main__':
    session_dir = app.config['SESSION_FILE_DIR']
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        print(f"Directorio de sesiones '{session_dir}' creado.")
    
    app.run(debug=True, port=5000)


   