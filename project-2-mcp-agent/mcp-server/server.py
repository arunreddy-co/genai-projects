import re
import json
import requests
from bs4 import BeautifulSoup
from fastmcp import FastMCP

mcp = FastMCP("TechStackSniper", instructions="Detects website technology stacks and extracts business info for sales prospecting.")


@mcp.tool()
def detect_tech_stack(url: str) -> dict:
    """Detects the technology stack of a website by analyzing its HTML and HTTP headers.

    Visits the given URL and identifies CMS, frameworks, JavaScript libraries,
    analytics tools, CDN providers, and server technologies.

    Args:
        url: The full URL of the website to analyze (e.g., https://example.com)

    Returns:
        dict: A dictionary containing detected technologies organized by category.
    """
    if not url.startswith("http"):
        url = "https://" + url

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        html = resp.text.lower()
        resp_headers = {k.lower(): v.lower() for k, v in resp.headers.items()}

        result = {
            "url": url,
            "status": "success",
            "cms": "Unknown",
            "frameworks": [],
            "js_libraries": [],
            "analytics": [],
            "cdn": "Unknown",
            "server": resp_headers.get("server", "Unknown"),
            "powered_by": resp_headers.get("x-powered-by", "Not disclosed"),
        }

        # CMS Detection
        if "wp-content" in html or "wp-includes" in html:
            result["cms"] = "WordPress"
        elif "cdn.shopify.com" in html or "shopify" in html:
            result["cms"] = "Shopify"
        elif 'content="wix.com' in html or "wix-code" in html:
            result["cms"] = "Wix"
        elif "squarespace" in html:
            result["cms"] = "Squarespace"
        elif "drupal" in html or "sites/default/files" in html:
            result["cms"] = "Drupal"
        elif "joomla" in html:
            result["cms"] = "Joomla"
        elif "ghost" in resp_headers.get("x-powered-by", ""):
            result["cms"] = "Ghost"
        elif 'content="webflow' in html:
            result["cms"] = "Webflow"

        # Framework Detection
        if "__next" in html or "_next/static" in html:
            result["frameworks"].append("Next.js")
        if "__nuxt" in html or "_nuxt" in html:
            result["frameworks"].append("Nuxt.js")
        if "ng-version" in html or "ng-app" in html:
            result["frameworks"].append("Angular")
        if "data-reactroot" in html or "react" in html:
            result["frameworks"].append("React")
        if re.search(r'vue[\.\-]', html) or "v-app" in html:
            result["frameworks"].append("Vue.js")
        if "laravel" in html or "laravel" in resp_headers.get("set-cookie", ""):
            result["frameworks"].append("Laravel")
        if "rails" in resp_headers.get("x-powered-by", ""):
            result["frameworks"].append("Ruby on Rails")
        if "express" in resp_headers.get("x-powered-by", ""):
            result["frameworks"].append("Express.js")

        # JS Libraries
        if "jquery" in html:
            result["js_libraries"].append("jQuery")
        if "bootstrap" in html:
            result["js_libraries"].append("Bootstrap")
        if "tailwind" in html:
            result["js_libraries"].append("Tailwind CSS")
        if "gsap" in html:
            result["js_libraries"].append("GSAP")
        if "three.js" in html or "threejs" in html:
            result["js_libraries"].append("Three.js")

        # Analytics
        if "google-analytics" in html or "gtag" in html or "googletagmanager" in html:
            result["analytics"].append("Google Analytics")
        if "hotjar" in html:
            result["analytics"].append("Hotjar")
        if "mixpanel" in html:
            result["analytics"].append("Mixpanel")
        if "segment" in html:
            result["analytics"].append("Segment")
        if "facebook.com/tr" in html or "fbq" in html:
            result["analytics"].append("Facebook Pixel")

        # CDN
        if "cloudflare" in resp_headers.get("server", ""):
            result["cdn"] = "Cloudflare"
        elif "cloudfront" in str(resp_headers):
            result["cdn"] = "AWS CloudFront"
        elif "fastly" in str(resp_headers):
            result["cdn"] = "Fastly"
        elif "akamai" in str(resp_headers):
            result["cdn"] = "Akamai"

        if not result["frameworks"]:
            result["frameworks"] = ["No major framework detected"]
        if not result["js_libraries"]:
            result["js_libraries"] = ["No major libraries detected"]
        if not result["analytics"]:
            result["analytics"] = ["No analytics detected"]

        return result

    except requests.exceptions.Timeout:
        return {"url": url, "status": "error", "error": "Connection timed out after 10 seconds"}
    except requests.exceptions.ConnectionError:
        return {"url": url, "status": "error", "error": "Could not connect to the website"}
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


@mcp.tool()
def get_site_info(url: str) -> dict:
    """Extracts basic business information from a website's meta tags and HTML.

    Reads the title, description, and main heading to understand what the
    business does without needing to render the full page.

    Args:
        url: The full URL of the website to analyze (e.g., https://example.com)

    Returns:
        dict: A dictionary with the site's title, description, and main heading.
    """
    if not url.startswith("http"):
        url = "https://" + url

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else "No title found"

        meta_desc = soup.find("meta", attrs={"name": "description"})
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        description = ""
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()
        elif og_desc and og_desc.get("content"):
            description = og_desc["content"].strip()
        else:
            description = "No description found"

        h1 = soup.find("h1")
        main_heading = h1.get_text(strip=True) if h1 else "No main heading found"

        og_type = soup.find("meta", attrs={"property": "og:type"})
        site_type = og_type["content"].strip() if og_type and og_type.get("content") else "Unknown"

        return {
            "url": url,
            "status": "success",
            "title": title,
            "description": description[:300],
            "main_heading": main_heading[:200],
            "site_type": site_type,
        }

    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
