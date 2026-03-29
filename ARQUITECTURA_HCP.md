# Hotel Concierge Pro — Arquitectura Escalable

## Resumen Ejecutivo

Arquitectura de dos capas que separa la **presencia publica** (landing SEO, catalogo)
del **sistema operativo** (reservas, admin, CRM), permitiendo escalar a multi-hotel
sin reescribir infraestructura.

---

## Arquitectura de Dominios

```
hotel-conciergepro.com           --> GitHub Pages (landing publica, SEO, catalogo)
app.hotel-conciergepro.com       --> Base44 (auth, reservas, admin, CRM, mailing)
api.hotel-conciergepro.com       --> [Futuro] Flask API custom
{hotel}.hotel-conciergepro.com   --> [Futuro] White-label por hotel
```

### Por que esta separacion?

1. **SEO**: Google indexa la landing publica sin barreras de login
2. **Conversion**: Visitante ve catalogo completo → decide → entonces crea cuenta
3. **Velocidad**: HTML estatico en CDN global (GitHub Pages) = <1s carga
4. **Independencia**: Si Base44 falla, la landing sigue visible
5. **Escalabilidad**: Migrar Base44 a Flask/React sin tocar la landing

---

## Configuracion DNS Requerida

En el registrador del dominio hotel-conciergepro.com:

| Tipo | Host | Valor | Proposito |
|------|------|-------|-----------|
| A | @ | 185.199.108.153 | GitHub Pages |
| A | @ | 185.199.109.153 | GitHub Pages |
| A | @ | 185.199.110.153 | GitHub Pages |
| A | @ | 185.199.111.153 | GitHub Pages |
| CNAME | www | DavidCabreraRivas.github.io | www redirect |
| CNAME | app | cname.base44.app | Base44 app |

**Orden de migracion:**
1. Crear CNAME `app` → Base44 y verificar que funciona
2. Configurar en Base44 que acepte `app.hotel-conciergepro.com`
3. Cambiar registros A del root a GitHub Pages
4. Esperar propagacion DNS (1-4 horas)
5. Activar HTTPS en GitHub Pages

---

## Estructura del Repositorio

```
Hotel-Concierge-Pro_global/
├── index.html              # Landing EN (publica, SEO)
├── CNAME                   # hotel-conciergepro.com
├── robots.txt              # Instrucciones crawlers
├── sitemap.xml             # Mapa del sitio
├── 404.html                # Pagina de error personalizada
├── ARQUITECTURA_HCP.md     # Este documento
├── es/
│   └── index.html          # Landing ES (SEO, hreflang)
└── assets/                 # [Futuro] CSS/JS/imagenes separados
```

---

## Modelo de Negocio y Escalado

### Fase Actual: Piloto Gueldera
- 1 hotel, 16 actividades, 7 categorias
- Comision: 15-25% por reserva
- Revenue estimado: 380-645 EUR/mes

### Fase 2: Multi-Hotel Lanzarote
- 5-10 hoteles independientes
- El modelo Base44 ya soporta multi-hotel (entity Hotel + hotel_id en Activity)
- Cada hotel ve solo sus reservas y comisiones
- Landing muestra todos los hoteles con filtro

### Fase 3: Canarias
- White-label subdomains por hotel
- Migracion de Base44 a stack custom (trigger: pagos, APIs externas, o > 50 hoteles)
- Stack destino: Next.js + FastAPI + PostgreSQL + Stripe

### Fase 4: SaaS
- hotel-conciergepro.com como producto SaaS para hoteles independientes
- Pricing: freemium (5 actividades gratis) + pro (ilimitado + analytics)

---

## Stack Actual vs Futuro

| Componente | Ahora | Futuro |
|-----------|-------|--------|
| Landing | GitHub Pages (HTML estatico) | Mismo (o Next.js SSG) |
| App | Base44 (no-code) | Flask/FastAPI + React |
| BD | Base44 interno | PostgreSQL |
| Auth | Base44 built-in | Auth0 / Firebase |
| Email | Gmail (linaschmidt123top) | SendGrid / AWS SES |
| Pagos | Manual | Stripe + Redsys |
| Analytics | - | GA4 + Mixpanel |
| CDN | GitHub Pages (Fastly) | CloudFlare |

---

## Trigger de Migracion Base44 → Custom

Migrar cuando se cumpla CUALQUIERA de estas condiciones:
- [ ] Necesidad de pagos online (Stripe/Redsys)
- [ ] Sync en tiempo real con calendarios de proveedores
- [ ] > 50 hoteles activos
- [ ] Rate limits de Base44 API
- [ ] Workflows complejos (cancelaciones, reembolsos, listas espera)

---

## Acciones Inmediatas

1. **Verificar que Base44 acepta subdominios custom** (app.hotel-conciergepro.com)
2. **Push del repo a GitHub** y activar GitHub Pages
3. **Configurar DNS** segun tabla anterior
4. **Enviar email a marketplace@canariasdestino.com** con esta arquitectura como soporte

---

*Hotel Concierge Pro — InnovaGestion Hotelera*
*Puerto del Carmen, Lanzarote — 2026*
