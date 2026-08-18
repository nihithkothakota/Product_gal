"""
Ingestion service — handles the "Universal Save" path.
Extracts metadata from URLs using OpenGraph tags and JSON-LD structured data.
In Phase 1 this runs synchronously; Phase 2 will make it async via the queue.
"""

import hashlib
import re
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


class ExtractionResult:
    """Structured result from URL metadata extraction."""

    def __init__(
        self,
        title: str | None = None,
        description: str | None = None,
        brand: str | None = None,
        price: float | None = None,
        currency: str = "INR",
        store: str | None = None,
        image_urls: list[str] | None = None,
        source: str | None = None,
    ):
        self.title = title
        self.description = description
        self.brand = brand
        self.price = price
        self.currency = currency
        self.store = store
        self.image_urls = image_urls or []
        self.source = source


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent hashing (strip tracking params, fragments)."""
    parsed = urlparse(url)
    # Remove common tracking parameters
    clean_query = re.sub(
        r"(utm_\w+|ref|tag|camp|creative|linkCode|th|psc)=[^&]*&?",
        "",
        parsed.query or "",
    )
    clean_query = clean_query.rstrip("&")
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if clean_query:
        normalized += f"?{clean_query}"
    return normalized.lower().rstrip("/")


def hash_url(url: str) -> str:
    """Generate a SHA256 hash of a normalized URL for duplicate detection."""
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def detect_store(url: str) -> str | None:
    """Detect the store name from the URL domain."""
    domain_to_store = {
        "amazon": "Amazon",
        "flipkart": "Flipkart",
        "myntra": "Myntra",
        "ajio": "AJIO",
        "nykaa": "Nykaa",
        "meesho": "Meesho",
        "snapdeal": "Snapdeal",
        "tatacliq": "Tata CLiQ",
        "ebay": "eBay",
        "etsy": "Etsy",
    }
    domain = urlparse(url).netloc.lower()
    for key, store_name in domain_to_store.items():
        if key in domain:
            return store_name
    return None


def detect_source(url: str) -> str:
    """Detect the source platform from the URL."""
    domain = urlparse(url).netloc.lower()
    source_map = {
        "instagram": "instagram",
        "facebook": "facebook",
        "pinterest": "pinterest",
        "reddit": "reddit",
        "youtube": "youtube",
        "twitter": "twitter",
        "x.com": "twitter",
        "t.me": "telegram",
        "telegram": "telegram",
        "wa.me": "whatsapp",
        "whatsapp": "whatsapp",
    }
    for key, source_name in source_map.items():
        if key in domain:
            return source_name
    return "web"


async def extract_from_url(url: str) -> ExtractionResult:
    """
    Fetch a URL and extract product metadata from:
    1. JSON-LD structured data (preferred — most reliable)
    2. OpenGraph meta tags
    3. Standard HTML meta tags and title

    This is the Phase 1 synchronous extraction pipeline.
    Phase 2 will route through async workers with LLM fallback.
    """
    # Auto-prepend https:// if protocol is missing
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url

    result = ExtractionResult(
        store=detect_store(url),
        source=detect_source(url),
    )

    direct_success = True
    response_text = ""
    try:
        try:
            from curl_cffi.requests import AsyncSession
            use_curl_cffi = True
        except ImportError:
            use_curl_cffi = False

        if use_curl_cffi:
            async with AsyncSession(impersonate="chrome120", timeout=15.0) as session:
                response = await session.get(url, allow_redirects=True)
                response_text = response.text
                response_status = response.status_code
        else:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            ) as client:
                response = await client.get(url)
                response_text = response.text
                response_status = response.status_code

        if response_status >= 400:
            raise Exception(f"HTTP Error {response_status}")
    except Exception as e:
        logger.warning("url_fetch_failed_trying_fallback", url=url, error=str(e))
        direct_success = False

    if direct_success:
        soup = BeautifulSoup(response_text, "lxml")
        # ── 1. Try JSON-LD ───────────────────────────────────────────────────
        _extract_json_ld(soup, result)
        # ── 2. Try OpenGraph ─────────────────────────────────────────────────
        _extract_og_tags(soup, result)
        # ── 3. Fallback to standard HTML ─────────────────────────────────────
        _extract_html_fallback(soup, result)
        
        # Clean direct extraction titles first so generic titles are cleared to None
        _clean_generic_title(result)

    # If direct extraction failed or returned insufficient details, try Microlink fallback
    if not result.title or not result.image_urls:
        await _extract_via_microlink(url, result)
        _clean_generic_title(result)

    # Resolve and clean image URLs to be absolute
    from urllib.parse import urljoin
    resolved = []
    for img in result.image_urls:
        if img:
            img = img.strip()
            abs_img = urljoin(url, img)
            if abs_img.startswith(("http://", "https://")) and abs_img not in resolved:
                resolved.append(abs_img)
    result.image_urls = resolved

    # Clean generic/promotional/marketing images
    _clean_generic_images(result)

    logger.info(
        "url_extracted",
        url=url,
        title=result.title,
        price=result.price,
        images=len(result.image_urls),
    )

    return result


def _clean_generic_title(result: ExtractionResult) -> None:
    """Clean up generic site, cart, and captcha titles to avoid wrong autofills."""
    if not result.title:
        return
        
    title_lower = result.title.lower().strip()
    generic_titles = {
        "amazon.in", "amazon", "amazon.com", "amazon.co.uk",
        "flipkart", "flipkart.com",
        "myntra", "myntra.com",
        "ajio", "ajio.com",
        "nykaa", "nykaa.com",
        "meesho", "meesho.com",
        "etsy", "etsy.com",
        "ebay", "ebay.com",
        "instagram", "pinterest", "facebook",
        "log in • instagram", "pinterest india",
        "security check", "robot check", "captcha", "just a moment...",
        "add to your order", "add to order", "shopping cart", "shopping bag",
        "your cart", "cart", "checkout", "sign in", "sign up", "login", "register",
        "amazon.in: buy online", "buy online", "electronics online", "shop online"
    }
    
    # If the title is exactly one of these or contains generic robot check indicators
    if title_lower in generic_titles or any(kw in title_lower for kw in ["security check", "robot check", "captcha", "just a moment"]):
        result.title = None


def _extract_json_ld(soup: BeautifulSoup, result: ExtractionResult) -> None:
    """Parse JSON-LD structured data for product info."""
    import json

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Handle @graph arrays
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") in (
                        "Product", "IndividualProduct", "ProductModel"
                    ):
                        data = item
                        break
                else:
                    continue

            if isinstance(data, dict) and data.get("@type") in (
                "Product", "IndividualProduct", "ProductModel"
            ):
                result.title = result.title or data.get("name")
                result.description = result.description or data.get("description")
                result.brand = result.brand or (
                    data.get("brand", {}).get("name")
                    if isinstance(data.get("brand"), dict)
                    else data.get("brand")
                )

                # Price from offers
                offers = data.get("offers", {})
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict):
                    price_str = offers.get("price") or offers.get("lowPrice")
                    if price_str:
                        try:
                            result.price = float(str(price_str).replace(",", ""))
                        except ValueError:
                            pass
                    result.currency = result.currency or offers.get("priceCurrency", "INR")

                # Images
                image = data.get("image")
                if isinstance(image, str):
                    result.image_urls.append(image)
                elif isinstance(image, list):
                    result.image_urls.extend(
                        [img if isinstance(img, str) else img.get("url", "")
                         for img in image[:5]]
                    )

        except (json.JSONDecodeError, AttributeError, TypeError):
            continue


def _extract_og_tags(soup: BeautifulSoup, result: ExtractionResult) -> None:
    """Extract OpenGraph meta tags."""
    og_map = {
        "og:title": "title",
        "og:description": "description",
        "og:image": "image",
        "product:price:amount": "price",
        "product:price:currency": "currency",
        "product:brand": "brand",
    }

    for meta in soup.find_all("meta", property=True):
        prop = meta.get("property", "")
        content = meta.get("content", "")
        if not content:
            continue

        if prop == "og:title" and not result.title:
            result.title = content
        elif prop == "og:description" and not result.description:
            result.description = content[:500]
        elif prop == "og:image" and content not in result.image_urls:
            result.image_urls.append(content)
        elif prop == "product:price:amount" and not result.price:
            try:
                result.price = float(content.replace(",", ""))
            except ValueError:
                pass
        elif prop == "product:price:currency":
            result.currency = content
        elif prop == "product:brand" and not result.brand:
            result.brand = content


def _extract_html_fallback(soup: BeautifulSoup, result: ExtractionResult) -> None:
    """Fallback: extract from standard HTML elements."""
    # ── Title ──────────────────────────────────────────────────────────
    if not result.title:
        # Check itemprop="name" or h1
        h1_tag = soup.find("h1")
        if h1_tag:
            result.title = h1_tag.text.strip()
        else:
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                result.title = title_tag.string.strip()

    if not result.description:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            result.description = (meta_desc.get("content") or "")[:500]

    # ── Brand Fallback ─────────────────────────────────────────────────
    if not result.brand:
        # 1. Check itemprop="brand"
        brand_el = soup.find(attrs={"itemprop": "brand"})
        if brand_el:
            result.brand = brand_el.text.strip()
            
        # 2. Check meta name="brand"
        if not result.brand:
            meta_brand = soup.find("meta", attrs={"name": "brand"}) or soup.find("meta", attrs={"property": "og:brand"})
            if meta_brand:
                result.brand = (meta_brand.get("content") or "").strip()
                
        # 3. Check common class names
        if not result.brand:
            brand_classes = [
                "pdp-brand", "brand", "product-brand", "product-meta-brand",
                "css-hv5jpp", "css-pxj4mu", "css-xaga9n", "designer-name", "manufacturer"
            ]
            for class_name in brand_classes:
                brand_el = soup.find(class_=class_name)
                if brand_el and brand_el.text.strip():
                    txt = brand_el.text.strip()
                    if len(txt) < 50:
                        result.brand = txt
                        break

    # ── Specific Retailers & Schema Price/Image Extraction ───────────────
    
    # 1. Check itemprop="price"
    if not result.price:
        price_el = soup.find(attrs={"itemprop": "price"})
        if price_el:
            content = price_el.get("content") or price_el.text
            try:
                result.price = float(re.sub(r"[^\d.]", "", content))
            except ValueError:
                pass

    # 2. Check itemprop="image"
    image_el = soup.find(attrs={"itemprop": "image"})
    if image_el:
        content = image_el.get("content") or image_el.get("src")
        if content and content not in result.image_urls:
            result.image_urls.append(content)

    # 3. Class-based price extraction (search in elements containing 'price')
    if not result.price:
        for class_pattern in ["price", "price-current", "offer-price", "sales-price", "amount"]:
            price_els = soup.find_all(class_=re.compile(class_pattern, re.I))
            for el in price_els:
                text = el.text.strip()
                if text:
                    # Look for currency match
                    match = re.search(r"[₹$]\s*([0-9,]+\.?\d*)", text)
                    if match:
                        try:
                            result.price = float(match.group(1).replace(",", ""))
                            break
                        except ValueError:
                            continue
            if result.price:
                break

    # 4. Standard HTML fallback regex search (last resort)
    if not result.price:
        price_patterns = [
            r"₹\s*([0-9,]+\.?\d*)",
            r"\$\s*([0-9,]+\.?\d*)",
            r"(?:price|Price|MRP)\s*[:=]\s*₹?\$?\s*([0-9,]+\.?\d*)",
        ]
        text = soup.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    result.price = float(match.group(1).replace(",", ""))
                    break
                except ValueError:
                    continue

    # ── Image Fallbacks ──────────────────────────────────────────────
    if not result.image_urls:
        # Look for typical product/main image classes
        for class_pattern in ["product-image", "main-image", "featured-image", "primary-image"]:
            img_el = soup.find("img", class_=re.compile(class_pattern, re.I))
            if img_el and img_el.get("src"):
                result.image_urls.append(img_el.get("src"))
                break

    # Look for any large image on the page if still none
    if not result.image_urls:
        imgs = soup.find_all("img")
        for img in imgs:
            src = img.get("src")
            if src and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                # Skip tiny icons or spacer gifs
                width = img.get("width")
                height = img.get("height")
                if width and height:
                    try:
                        if int(width) < 100 or int(height) < 100:
                            continue
                    except ValueError:
                        pass
                result.image_urls.append(src)
                if len(result.image_urls) >= 3:
                    break


async def _extract_via_microlink(url: str, result: ExtractionResult) -> None:
    """Fallback extraction using Microlink API with custom e-commerce selectors."""
    try:
        # Construct query with multiple fallback selectors for Amazon, Flipkart, Myntra, etc.
        # %23 = #, %2C = comma, %5B = [, %5D = ], %22 = "
        api_url = (
            f"https://api.microlink.io/?url={url}"
            "&data.img_src.selector=%23landingImage%2C+%23imgBlkFront%2C+.VU-ZEB%2C+._396cs4%2C+.pdp-image%2C+img.product-image"
            "&data.img_src.attr=src"
            "&data.price.selector=span.a-price-whole%2C+._30jeq3%2C+._16Jk6d%2C+span%5Bitemprop%3D%22price%22%5D%2C+.pdp-price"
            "&data.price.attr=text"
        )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(api_url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    item = data.get("data", {})
                    result.title = result.title or item.get("title")
                    result.description = result.description or item.get("description")
                    result.store = result.store or item.get("publisher")
                    
                    # Parse custom price if extracted
                    price_val = item.get("price")
                    if price_val and not result.price:
                        try:
                            clean_price = re.sub(r"[^\d.]", "", str(price_val))
                            if clean_price:
                                result.price = float(clean_price)
                        except ValueError:
                            pass
                    
                    # Add custom extracted main image
                    img_src = item.get("img_src")
                    if img_src and img_src not in result.image_urls:
                        result.image_urls.insert(0, img_src)
                    
                    # Fallback default image
                    img_data = item.get("image", {})
                    img_url = img_data.get("url") if isinstance(img_data, dict) else img_data
                    if img_url and img_url not in result.image_urls:
                        result.image_urls.append(img_url)
                        
                    logger.info("microlink_extraction_success", url=url)
    except Exception as e:
        logger.warning("microlink_extraction_failed", url=url, error=str(e))


def _clean_generic_images(result: ExtractionResult) -> None:
    """Filter out promotional banners, logos, and tracking pixels from extracted images."""
    cleaned = []
    generic_keywords = [
        "logo", "sprite", "header", "nav", "footer", "banner", "marketing/prime",
        "prime-logo", "transparent", "pixel", "clear.gif", "spinner", "loading",
        "checkmark", "btn", "button", "arrow", "icon", "ad-system", "amazon-adsystem",
        "prime_logo", "logo-rgb"
    ]
    for url in result.image_urls:
        if not url:
            continue
        url_lower = url.lower()
        if any(kw in url_lower for kw in generic_keywords):
            continue
        # For Amazon, reject G/ images (marketing/logos/etc.) and keep I/ images (products)
        if "amazon.com" in url_lower or "amazon.in" in url_lower or "media-amazon.com" in url_lower:
            if "/images/g/" in url_lower:
                continue
        if url not in cleaned:
            cleaned.append(url)
    result.image_urls = cleaned
