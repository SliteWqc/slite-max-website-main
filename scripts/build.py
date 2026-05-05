from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from html import escape
from pathlib import Path
from string import Template
from zipfile import ZipFile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
CONTENT_PATH = ROOT / "content" / "site.json"
EN_CONTENT_PATH = ROOT / "content" / "site.en.json"
COPY_WORKBOOK_PATH = ROOT / "content" / "site-copy.xlsx"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
PUBLIC_DIR = ROOT / "public"
DIST_DIR = ROOT / "dist"
COPY_SCRIPT_PATH = ROOT / "scripts" / "copy_workbook.mjs"
NODE_BIN = Path("/Users/slite/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
EXCLUDED_COPY_KEYS = {"slug", "image", "homeCardRole"}
LOCALES = {
    "zh": {
        "html_lang": "zh-CN",
        "content_path": CONTENT_PATH,
        "output_prefix": "",
        "language_label": "EN",
        "target_language": "en",
        "image_alt_suffix": "界面预览",
    },
    "en": {
        "html_lang": "en",
        "content_path": EN_CONTENT_PATH,
        "output_prefix": "en",
        "language_label": "中文",
        "target_language": "zh",
        "image_alt_suffix": "interface preview",
    },
}


def load_content() -> dict:
    return json.loads(CONTENT_PATH.read_text(encoding="utf-8"))


def load_locale_content(locale_key: str) -> dict:
    return json.loads(LOCALES[locale_key]["content_path"].read_text(encoding="utf-8"))


def save_content(content: dict) -> None:
    CONTENT_PATH.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_template(name: str) -> Template:
    return Template((TEMPLATES_DIR / name).read_text(encoding="utf-8"))


def copy_leaf_paths(content: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    def walk(node: object, path: list[str]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in EXCLUDED_COPY_KEYS:
                    continue
                walk(value, [*path, key])
            return

        if isinstance(node, list):
            for index, value in enumerate(node):
                if isinstance(value, dict) and "slug" in value:
                    walk(value, [*path, value["slug"]])
                else:
                    walk(value, [*path, str(index)])
            return

        if isinstance(node, str):
            rows.append((".".join(path), node))

    walk(content, [])
    return rows


def area_for_path(path: str) -> str:
    if path.startswith("site.home."):
        return "home.hero"
    if path.startswith("site."):
        return "site.global"
    if path.startswith("footer."):
        return "shared.footer"
    if path.startswith("links."):
        return "shared.links"
    if path.startswith("ui.cards."):
        return "home.cards"
    if path.startswith("ui.productPage."):
        return "product.shared"
    if path.startswith("pages.about."):
        return "about.page"
    if path.startswith("pages.legal."):
        return "legal.page"
    if path.startswith("products.renamer."):
        return "product.renamer"
    if path.startswith("products.exporter."):
        return "product.exporter"
    return "misc"


def note_for_path(path: str) -> str:
    if path.endswith("pageTitle"):
        return "浏览器标签页标题"
    if path.endswith("metaDescription"):
        return "页面 meta description"
    if path.endswith("label"):
        return "小标题或链接标签文字"
    if path.endswith("subtitle"):
        return "副标题文案"
    if path.endswith("description"):
        return "产品简介文案"
    if path.endswith("detailPlaceholder"):
        return "详情页大段说明占位"
    if path.endswith("downloadUrl"):
        return "下载按钮跳转链接"
    if path.endswith("bilibiliUrl"):
        return "哔哩哔哩主页链接"
    if ".sections." in path and path.endswith(".heading"):
        return "分段标题"
    if ".sections." in path and path.endswith(".body"):
        return "分段正文"
    if path.endswith("title"):
        return "主标题"
    if path.endswith("intro"):
        return "页面导语"
    if path.endswith("note"):
        return "页脚说明"
    if path.endswith("ctaLabel"):
        return "首页产品按钮文字"
    if path.endswith("kicker"):
        return "小型栏目标签"
    if path.endswith("backLabel"):
        return "返回按钮文字"
    if path.endswith("downloadLabel"):
        return "下载按钮文字"
    if path.endswith("contentTitle"):
        return "详情页内容块标题"
    if path.endswith("contentKicker"):
        return "详情页内容块标签"
    return "可编辑文案"


def set_value_at_path(content: dict, path: str, value: str) -> None:
    segments = path.split(".")
    node: object = content
    for segment in segments[:-1]:
        if isinstance(node, list):
            if segment.isdigit():
                node = node[int(segment)]
                continue
            matched = None
            for item in node:
                if isinstance(item, dict) and item.get("slug") == segment:
                    matched = item
                    break
            if matched is None:
                raise KeyError(path)
            node = matched
            continue
        if not isinstance(node, dict):
            raise KeyError(path)
        node = node[segment]

    final_key = segments[-1]
    if isinstance(node, list):
        node[int(final_key)] = value
        return
    if not isinstance(node, dict):
        raise KeyError(path)
    node[final_key] = value


def collect_copy_rows(content: dict) -> list[dict[str, str]]:
    rows = []
    for path, current_text in copy_leaf_paths(content):
        rows.append(
            {
                "page_or_area": area_for_path(path),
                "field_key": path,
                "current_text": current_text,
                "notes": note_for_path(path),
            }
        )
    return rows


def ensure_node_runtime() -> None:
    if not NODE_BIN.exists():
        raise FileNotFoundError(f"Node runtime not found: {NODE_BIN}")


def can_export_copy_workbook() -> bool:
    if os.environ.get("SKIP_COPY_WORKBOOK_EXPORT") == "1":
        return False
    return NODE_BIN.exists()


def run_copy_script(command: str, input_path: Path, output_path: Path) -> None:
    ensure_node_runtime()
    subprocess.run(
        [str(NODE_BIN), str(COPY_SCRIPT_PATH), command, str(input_path), str(output_path)],
        check=True,
        cwd=ROOT,
    )


def export_copy_workbook(content: dict) -> None:
    if not can_export_copy_workbook():
        print("Skipping copy workbook export: local Node runtime is unavailable.")
        return
    rows = collect_copy_rows(content)
    temp_json = ROOT / "content" / ".site-copy-export.json"
    temp_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        run_copy_script("export", temp_json, COPY_WORKBOOK_PATH)
    finally:
        temp_json.unlink(missing_ok=True)


def import_copy_workbook() -> dict:
    ensure_node_runtime()
    content = load_content()
    valid_paths = {path for path, _ in copy_leaf_paths(content)}
    imported_rows = read_copy_workbook_rows(COPY_WORKBOOK_PATH)

    for row in imported_rows:
        field_key = row["field_key"]
        if field_key not in valid_paths:
            continue
        set_value_at_path(content, field_key, row["current_text"])

    save_content(content)
    return content


def read_copy_workbook_rows(path: Path) -> list[dict[str, str]]:
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    with ZipFile(path) as archive:
        shared_strings: list[str] = []

        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for shared_item in shared_root.findall("a:si", namespace):
                shared_strings.append(
                    "".join(text_node.text or "" for text_node in shared_item.iterfind(".//a:t", namespace))
                )

        sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        parsed_rows: list[list[str]] = []

        for row in sheet_root.findall(".//a:row", namespace):
            values: list[str] = []
            for cell in row.findall("a:c", namespace):
                cell_type = cell.get("t")
                value = ""

                inline_string = cell.find("a:is", namespace)
                if inline_string is not None:
                    value = "".join(text_node.text or "" for text_node in inline_string.iterfind(".//a:t", namespace))
                else:
                    raw_value = cell.find("a:v", namespace)
                    if raw_value is not None and raw_value.text is not None:
                        value = shared_strings[int(raw_value.text)] if cell_type == "s" else raw_value.text

                values.append(value)
            parsed_rows.append(values)

    data_rows = [row for row in parsed_rows[1:] if len(row) > 1 and row[1]]
    return [
        {
            "page_or_area": row[0] if len(row) > 0 else "",
            "field_key": row[1] if len(row) > 1 else "",
            "current_text": row[2] if len(row) > 2 else "",
            "notes": row[3] if len(row) > 3 else "",
        }
        for row in data_rows
    ]


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def reset_dist() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def copy_static_assets() -> None:
    copy_tree(ASSETS_DIR, DIST_DIR / "assets")
    copy_tree(PUBLIC_DIR, DIST_DIR)


def output_base(locale_key: str) -> Path:
    prefix = LOCALES[locale_key]["output_prefix"]
    return DIST_DIR / prefix if prefix else DIST_DIR


def locale_root_href(locale_key: str, page_depth: str) -> str:
    if page_depth == "home":
        return "." if locale_key == "zh" else "."
    if page_depth == "product":
        return "../.."
    return ".."


def language_href(locale_key: str, page_depth: str, slug: str | None = None) -> str:
    if locale_key == "zh":
        if page_depth == "home":
            return "en/"
        if page_depth == "product" and slug:
            return f"../../en/products/{slug}/"
        if page_depth == "basic" and slug:
            return f"../en/{slug}/"
        return "en/"

    if page_depth == "home":
        return "../"
    if page_depth == "product" and slug:
        return f"../../../products/{slug}/"
    if page_depth == "basic" and slug:
        return f"../../{slug}/"
    return "../"


def render_footer_subs(content: dict, root_href: str) -> dict[str, str]:
    footer = content["footer"]
    return {
        "footer_note": footer["note"],
        "footer_meta_label": footer["metaLabel"],
        "footer_about_label": footer["aboutLabel"],
        "footer_legal_label": footer["legalLabel"],
        "footer_bilibili_label": footer["bilibiliLabel"],
        "about_href": f"{root_href}/about/",
        "legal_href": f"{root_href}/{content['pages']['legal']['slug']}/",
        "bilibili_url": content["links"]["bilibiliUrl"],
        "year": str(datetime.now().year),
    }


def render_product_cards(content: dict, locale_key: str, assets_prefix: str) -> str:
    cards = []
    ui_cards = content["ui"]["cards"]
    aria_template = "进入 {title} 详情页" if locale_key == "zh" else "Open {title} details"
    alt_template = "{title} 界面缩略图" if locale_key == "zh" else "{title} interface thumbnail"
    for product in content["products"]:
        role_class = f" product-link--{product.get('homeCardRole', 'standard')}"
        image_src = f"{assets_prefix}/{product['image']}"
        cards.append(
            f"""
        <a class="product-link{role_class}" href="products/{escape(product['slug'])}/" aria-label="{escape(aria_template.format(title=product['title']))}">
          <img class="product-shot" src="{escape(image_src)}" alt="{escape(alt_template.format(title=product['title']))}" />
          <div class="product-overlay">
            <div class="product-meta">
              <div>
                <p class="section-kicker">{escape(ui_cards['kicker'])}</p>
                <h2>{escape(product['title'])}</h2>
              </div>
              <span class="cta-chip">{escape(ui_cards['ctaLabel'])}</span>
            </div>
            <p>{escape(product['subtitle'])}</p>
          </div>
        </a>
        """.strip()
        )
    return "\n".join(cards)


def render_page_sections(sections: list[dict]) -> str:
    blocks = []
    for section in sections:
        blocks.append(
            f"""
        <article class="content-block">
          <h2>{escape(section['heading'])}</h2>
          <p>{escape(section['body'])}</p>
        </article>
        """.strip()
        )
    return "\n".join(blocks)


def render_heading_block(text: str, level: str = "h2") -> str:
    if not text.strip():
        return ""
    return f"<{level}>{escape(text)}</{level}>"


def render_home_title(text: str) -> str:
    if text == "Slite's M4L Tools":
        return 'Slite&#x27;s <span class="brand-phrase">M4L Tools</span>'
    return escape(text)


def render_home_subtitle(text: str) -> str:
    return escape(text).replace("Max for Live", '<span class="text-accent">Max for Live</span>')


def render_product_detail_content(product: dict) -> str:
    sections = product.get("detailSections", [])
    if sections:
        blocks = []
        for section in sections:
            blocks.append(
                f"""
          <article class="detail-block">
            <h3>{escape(section['heading'])}</h3>
            <p>{escape(section['body'])}</p>
          </article>
                """.rstrip()
            )
        return "\n".join(blocks)

    return f"<p>{escape(product['detailPlaceholder'])}</p>"


def render_page_intro_block(intro: str) -> str:
    if not intro.strip():
        return ""
    return f'<p class="page-intro">{escape(intro)}</p>'


def render_page_sections_block(sections: list[dict]) -> str:
    rendered_sections = render_page_sections(sections)
    if not rendered_sections.strip():
        return ""
    return (
        '<section class="content-placeholder content-placeholder--stack reveal">\n'
        f"{rendered_sections}\n"
        "</section>"
    )


def build_home(content: dict, locale_key: str) -> None:
    template = load_template("index.html.tmpl")
    site = content["site"]
    locale = LOCALES[locale_key]
    assets_prefix = "." if locale_key == "zh" else ".."
    html = template.substitute(
        html_lang=locale["html_lang"],
        page_title=site["home"]["pageTitle"],
        meta_description=site["home"]["metaDescription"],
        assets_prefix=assets_prefix,
        language_href=language_href(locale_key, "home"),
        language_label=locale["language_label"],
        target_language=locale["target_language"],
        brand_label=site["home"]["label"],
        hero_title=render_home_title(site["home"]["title"]),
        hero_subtitle=render_home_subtitle(site["home"]["subtitle"]),
        product_cards=render_product_cards(content, locale_key, assets_prefix),
        **render_footer_subs(content, locale_root_href(locale_key, "home")),
    )
    write_file(output_base(locale_key) / "index.html", html)


def build_product_pages(content: dict, locale_key: str) -> None:
    template = load_template("product.html.tmpl")
    site = content["site"]
    ui = content["ui"]["productPage"]
    locale = LOCALES[locale_key]
    for product in content["products"]:
        assets_prefix = "../.." if locale_key == "zh" else "../../.."
        home_href = "../.." if locale_key == "zh" else "../.."
        html = template.substitute(
            html_lang=locale["html_lang"],
            page_title=f"{product['title']} / {site['pageTitleSuffix']}",
            meta_description=product["description"],
            assets_prefix=assets_prefix,
            language_href=language_href(locale_key, "product", product["slug"]),
            language_label=locale["language_label"],
            target_language=locale["target_language"],
            brand_label=site["home"]["label"],
            home_href=home_href,
            back_label=ui["backLabel"],
            product_title=product["title"],
            product_subtitle=product["subtitle"],
            product_description=product["description"],
            download_label=ui["downloadLabel"],
            download_url=product["downloadUrl"],
            download_filename=Path(product["downloadUrl"]).name,
            product_image=f"{assets_prefix}/{product['image']}",
            product_image_alt=f"{product['title']} {locale['image_alt_suffix']}",
            content_kicker=ui["contentKicker"],
            content_title_block=render_heading_block(ui["contentTitle"], "h2"),
            detail_content=render_product_detail_content(product),
            **render_footer_subs(content, locale_root_href(locale_key, "product")),
        )
        write_file(output_base(locale_key) / "products" / product["slug"] / "index.html", html)


def build_basic_pages(content: dict, locale_key: str) -> None:
    template = load_template("basic.html.tmpl")
    back_label = content["ui"]["productPage"]["backLabel"]
    locale = LOCALES[locale_key]
    for page in content["pages"].values():
        assets_prefix = ".." if locale_key == "zh" else "../.."
        html = template.substitute(
            html_lang=locale["html_lang"],
            page_title=page["pageTitle"],
            meta_description=page["metaDescription"],
            assets_prefix=assets_prefix,
            language_href=language_href(locale_key, "basic", page["slug"]),
            language_label=locale["language_label"],
            target_language=locale["target_language"],
            home_href="..",
            back_label=back_label,
            page_kicker=page["kicker"],
            page_heading=page["title"],
            page_intro_block=render_page_intro_block(page["intro"]),
            page_sections_block=render_page_sections_block(page["sections"]),
            **render_footer_subs(content, locale_root_href(locale_key, "basic")),
        )
        write_file(output_base(locale_key) / page["slug"] / "index.html", html)


def build_site(content: dict | None = None) -> None:
    reset_dist()
    copy_static_assets()
    build_content = content or load_locale_content("zh")
    build_home(build_content, "zh")
    build_product_pages(build_content, "zh")
    build_basic_pages(build_content, "zh")

    en_content = load_locale_content("en")
    build_home(en_content, "en")
    build_product_pages(en_content, "en")
    build_basic_pages(en_content, "en")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and sync the slite.audio static site.")
    parser.add_argument(
        "command",
        nargs="?",
        default="build",
        choices=["build", "import-copy", "export-copy"],
        help="build: build site and refresh workbook; import-copy: import workbook changes then rebuild; export-copy: refresh workbook only",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "import-copy":
        content = import_copy_workbook()
        build_site(content)
        export_copy_workbook(content)
        return

    content = load_content()

    if args.command == "export-copy":
        export_copy_workbook(content)
        return

    build_site(content)
    export_copy_workbook(content)


if __name__ == "__main__":
    main()
