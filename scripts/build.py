from __future__ import annotations

import argparse
import json
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
COPY_WORKBOOK_PATH = ROOT / "content" / "site-copy.xlsx"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
PUBLIC_DIR = ROOT / "public"
DIST_DIR = ROOT / "dist"
COPY_SCRIPT_PATH = ROOT / "scripts" / "copy_workbook.mjs"
NODE_BIN = Path("/Users/slite/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
EXCLUDED_COPY_KEYS = {"slug", "image", "homeCardRole"}


def load_content() -> dict:
    return json.loads(CONTENT_PATH.read_text(encoding="utf-8"))


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


def run_copy_script(command: str, input_path: Path, output_path: Path) -> None:
    ensure_node_runtime()
    subprocess.run(
        [str(NODE_BIN), str(COPY_SCRIPT_PATH), command, str(input_path), str(output_path)],
        check=True,
        cwd=ROOT,
    )


def export_copy_workbook(content: dict) -> None:
    rows = collect_copy_rows(content)
    temp_json = ROOT / "content" / ".site-copy-export.json"
    temp_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        run_copy_script("export", temp_json, COPY_WORKBOOK_PATH)
    finally:
        temp_json.unlink(missing_ok=True)


def import_copy_workbook() -> dict:
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
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def copy_static_assets() -> None:
    copy_tree(ASSETS_DIR, DIST_DIR / "assets")
    copy_tree(PUBLIC_DIR, DIST_DIR)


def render_footer_subs(content: dict, assets_prefix: str) -> dict[str, str]:
    footer = content["footer"]
    return {
        "footer_note": footer["note"],
        "footer_meta_label": footer["metaLabel"],
        "footer_about_label": footer["aboutLabel"],
        "footer_legal_label": footer["legalLabel"],
        "footer_bilibili_label": footer["bilibiliLabel"],
        "about_href": f"{assets_prefix}/about/",
        "legal_href": f"{assets_prefix}/legal/",
        "bilibili_url": content["links"]["bilibiliUrl"],
        "year": str(datetime.now().year),
    }


def render_product_cards(content: dict) -> str:
    cards = []
    ui_cards = content["ui"]["cards"]
    for product in content["products"]:
        role_class = f" product-link--{product.get('homeCardRole', 'standard')}"
        cards.append(
            f"""
        <a class="product-link{role_class}" href="products/{escape(product['slug'])}/" aria-label="进入 {escape(product['title'])} 详情页">
          <img class="product-shot" src="{escape(product['image'])}" alt="{escape(product['title'])} 界面缩略图" />
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


def build_home(content: dict) -> None:
    template = load_template("index.html.tmpl")
    site = content["site"]
    html = template.substitute(
        page_title=site["home"]["pageTitle"],
        meta_description=site["home"]["metaDescription"],
        assets_prefix=".",
        brand_label=site["home"]["label"],
        hero_title=site["home"]["title"],
        hero_subtitle=site["home"]["subtitle"],
        product_cards=render_product_cards(content),
        **render_footer_subs(content, "."),
    )
    write_file(DIST_DIR / "index.html", html)


def build_product_pages(content: dict) -> None:
    template = load_template("product.html.tmpl")
    site = content["site"]
    ui = content["ui"]["productPage"]
    for product in content["products"]:
        html = template.substitute(
            page_title=f"{product['title']} / {site['pageTitleSuffix']}",
            meta_description=product["description"],
            assets_prefix="../..",
            brand_label=site["home"]["label"],
            home_href="../..",
            back_label=ui["backLabel"],
            product_title=product["title"],
            product_subtitle=product["subtitle"],
            product_description=product["description"],
            download_label=ui["downloadLabel"],
            download_url=product["downloadUrl"],
            download_filename=Path(product["downloadUrl"]).name,
            product_image=f"../../{product['image']}",
            content_kicker=ui["contentKicker"],
            content_title_block=render_heading_block(ui["contentTitle"], "h2"),
            detail_content=render_product_detail_content(product),
            **render_footer_subs(content, "../.."),
        )
        write_file(DIST_DIR / "products" / product["slug"] / "index.html", html)


def build_basic_pages(content: dict) -> None:
    template = load_template("basic.html.tmpl")
    back_label = content["ui"]["productPage"]["backLabel"]
    for page in content["pages"].values():
        html = template.substitute(
            page_title=page["pageTitle"],
            meta_description=page["metaDescription"],
            assets_prefix="..",
            home_href="..",
            back_label=back_label,
            page_kicker=page["kicker"],
            page_heading=page["title"],
            page_intro_block=render_page_intro_block(page["intro"]),
            page_sections_block=render_page_sections_block(page["sections"]),
            **render_footer_subs(content, ".."),
        )
        write_file(DIST_DIR / page["slug"] / "index.html", html)


def build_site(content: dict) -> None:
    reset_dist()
    copy_static_assets()
    build_home(content)
    build_product_pages(content)
    build_basic_pages(content)


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
