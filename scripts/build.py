from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from string import Template


ROOT = Path(__file__).resolve().parent.parent
CONTENT_PATH = ROOT / "content" / "products.json"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
PUBLIC_DIR = ROOT / "public"
DIST_DIR = ROOT / "dist"


def load_content() -> dict:
    return json.loads(CONTENT_PATH.read_text(encoding="utf-8"))


def load_template(name: str) -> Template:
    return Template((TEMPLATES_DIR / name).read_text(encoding="utf-8"))


def render_product_cards(products: list[dict]) -> str:
    cards = []
    for product in products:
        role_class = f" product-link--{product.get('homeCardRole', 'standard')}"
        cards.append(
            f"""
        <a class="product-link{role_class}" href="products/{product['slug']}/" aria-label="进入 {product['title']} 详情页">
          <img class="product-shot" src="{product['image']}" alt="{product['title']} 界面缩略图" />
          <div class="product-overlay">
            <div class="product-meta">
              <div>
                <p class="section-kicker">Product</p>
                <h2>{product['title']}</h2>
              </div>
              <span class="cta-chip">enter</span>
            </div>
            <p>{product['subtitle']}</p>
          </div>
        </a>
        """.strip()
        )
    return "\n".join(cards)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def reset_dist() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def copy_static_assets() -> None:
    copy_tree(ASSETS_DIR, DIST_DIR / "assets")
    copy_tree(PUBLIC_DIR, DIST_DIR)


def build_home(site: dict, products: list[dict]) -> None:
    template = load_template("index.html.tmpl")
    html = template.substitute(
        page_title="slite / Max for Live Tools",
        meta_description=site["heroSubtitle"],
        assets_prefix=".",
        brand_label=site["label"],
        hero_title=site["heroTitle"],
        hero_subtitle=site["heroSubtitle"],
        product_cards=render_product_cards(products),
        footer_note=site["footerNote"],
        year=str(datetime.now().year),
    )
    write_file(DIST_DIR / "index.html", html)


def build_product_pages(site: dict, products: list[dict]) -> None:
    template = load_template("product.html.tmpl")
    for product in products:
        html = template.substitute(
            page_title=f"{product['title']} / slite",
            meta_description=product["description"],
            assets_prefix="../..",
            brand_label=site["label"],
            home_href="../..",
            product_title=product["title"],
            product_subtitle=product["subtitle"],
            product_description=product["description"],
            download_url=product["downloadUrl"],
            product_image=f"../../{product['image']}",
            detail_placeholder=product["detailPlaceholder"],
            footer_note=site["footerNote"],
            year=str(datetime.now().year),
        )
        write_file(DIST_DIR / "products" / product["slug"] / "index.html", html)


def main() -> None:
    content = load_content()
    site = content["site"]
    products = content["products"]
    reset_dist()
    copy_static_assets()
    build_home(site, products)
    build_product_pages(site, products)


if __name__ == "__main__":
    main()
