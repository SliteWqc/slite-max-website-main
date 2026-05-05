from __future__ import annotations

from pathlib import Path
import re
import html
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
PACKAGE_ROOT = PROJECT_ROOT / "Product Package"
DOWNLOAD_ROOT = ROOT / "public" / "downloads"
MANUAL_ROOT = PROJECT_ROOT / "manual"
EXTRACTED_IMAGE_ROOT = ROOT / "manual-assets-generated"


MANUALS = {
    "exporter": {
        "folder": "Slite - Clip Exporter 1.0",
        "device": "Slite - Clip Exporter 1.0.amxd",
        "source_pdf": "exporter-manual.pdf",
        "english_md": "exporter-manual.en.md",
        "pdf": "exporter-manual-en.pdf",
        "package_zip": "Slite - Clip Exporter 1.0 en.zip",
        "zip": "slite-clip-exporter-1.0-en.zip",
        "title": "Slite - Clip Exporter Manual",
        "subtitle": "English Version",
        "sections": [
            (
                "Preface",
                [
                    "Slite Exporter is a batch clip-export device for Ableton Live Arrangement View.",
                    "It is designed for the stage after arrangement work, where you need to quickly confirm a group of arrangement clips and export them as audio files using shared settings.",
                    "It is not a matrix-style, arbitrary multi-track ripper. Its workflow is intentionally stable and predictable: capture the export set, preview the result, then export the captured set in batch.",
                ],
            ),
            (
                "1. Capture Section",
                [
                    "Capture is the most important part of Slite Exporter. It decides which clips will be exported this time.",
                    "Exporter supports only two track scopes: the currently selected single track, or all tracks. Each scope can optionally use the current loop range, creating four fixed capture entries.",
                    "TRACK captures all clips on the selected track and ignores the loop. TRACK IN LOOP captures clips on the selected track that overlap the current loop. TRACKS captures all clips on all tracks and ignores the loop. TRACKS IN LOOP captures clips on all tracks that overlap the current loop.",
                    "Think of capture as freezing the current export targets into a list. Preview shows this captured list, and Export acts on this captured list. It will not automatically follow every later change you make in Live.",
                    "Capture again if you change the loop range, switch selected track, choose another capture mode, add or delete target clips, replace a clip source, or just consolidated clips and are preparing to export.",
                ],
            ),
            (
                "2. Main Controls",
                [
                    "Preview shows the latest capture result. It is not every clip in the Arrangement; it is the current export set.",
                    "Sample Rate controls the export sample rate. The current options are 44.1, 48, and 96 kHz. Bit Depth controls exported bit depth. Channel controls stereo or mono output.",
                    "Fade In and Fade Out set short fades at the start and end of exported files. Normalize applies shared level processing when you want batch results to feel more consistent. Peak Ceiling sets the output peak limit and is often used together with Normalize.",
                    "Clip Gain is enabled by default. When enabled, the clip gain set in Live is included in the exported result; when disabled, export ignores the clip's current gain adjustment.",
                    "Choose Folder sets the export directory. The folder path is stored in the current Live Set for that Exporter instance. If the path becomes invalid later, the UI may still show it, but export will be blocked until you choose a valid folder again.",
                    "Status shows feedback: red means error, green means success, and yellow means notice. Export runs the batch export using the current capture set and current settings.",
                ],
            ),
            (
                "3. Known Behaviors and Boundaries",
                [
                    "Exporter is for Arrangement View. It is not a Session View batch exporter.",
                    "For warped clips, the current strategy is to turn warp off first and then export. Mixed warped clips can currently export, but this does not mean Exporter exports while preserving warp state.",
                    "Fresh consolidate can behave differently across platforms. On macOS, freshly consolidated clips usually export directly, though capturing again is still recommended. On Windows, freshly consolidated clips may require saving, reopening the Set, capturing again, and then exporting.",
                    "Based on current Ableton Live 12.3 testing, Windows resample clips may need the Save Set / Collect All and Save, reopen, recapture, export workflow. Bounce clips usually export directly.",
                    "If a clip source changes after capture, Exporter blocks export for safety instead of exporting with a potentially wrong source.",
                    "If the saved export folder is deleted, renamed, or moved, the old path may stay visible, but export is blocked until a valid folder is selected.",
                    "Duplicate clip names show a yellow notice. It is only a warning and does not stop export; the filename conflict fallback still applies.",
                    "If Ableton Live's audio device is offline or unstable, Exporter's main window may fail to open. In that case, check Live's audio device first before treating it as a device bug.",
                ],
            ),
            (
                "4. Recommended Workflow",
                [
                    "Decide whether you want to export the selected track or all tracks.",
                    "Choose normal capture or loop-based capture depending on your target range.",
                    "Check Preview to confirm that the captured clips are correct.",
                    "Set sample rate, bit depth, channel, normalize, peak ceiling, clip gain, and export folder.",
                    "If the Arrangement changed after capture, capture again before exporting.",
                    "Press Export and check the status feedback.",
                ],
            ),
        ],
    },
    "renamer": {
        "folder": "Slite - Clip Renamer 1.0",
        "device": "Slite - Clip Renamer 1.0.amxd",
        "source_pdf": "renamer-manual.pdf",
        "english_md": "renamer-manual.en.md",
        "pdf": "renamer-manual-en.pdf",
        "package_zip": "Slite - Clip Renamer 1.0 en.zip",
        "zip": "slite-clip-renamer-1.0-en.zip",
        "title": "Slite - Arrangement Clip Renamer Manual",
        "subtitle": "English Version",
        "sections": [
            (
                "Preface",
                [
                    "Slite Arrangement Clip Renamer is a batch renaming device for Ableton Live Arrangement View.",
                    "It helps organize arrangement clip names during editing. You first capture a group of clips, then preview the naming result, and finally write the new names back to the Live Set in one pass.",
                    "Renamer is not an audio renderer and not a free matrix-style multi-track naming tool. It uses fixed capture modes to build a clear target set, then generates final names through an ordered rule system.",
                ],
            ),
            (
                "1. Capture Section",
                [
                    "Capture decides which arrangement clips will be renamed this time.",
                    "Renamer supports two track scopes only: the currently selected track, or all tracks. Each scope can optionally use the current loop range, creating four fixed capture entries.",
                    "TRACK captures all arrangement clips on the selected track and ignores the loop. IN LOOP under selected captures clips on the selected track that overlap the current loop. TRACKS captures all arrangement clips on all tracks and ignores the loop. IN LOOP under all captures clips on all tracks that overlap the current loop.",
                    "TRACK and TRACKS will automatically set Live's loop to the overall boundary of the captured clips, making it easier to inspect the group. IN LOOP uses the current loop and does not reset it.",
                    "Loop capture checks time overlap. A clip does not need to be fully inside the loop. After capture, the preview target set is fixed. Editing rules changes the preview result but does not automatically select a new clip set.",
                ],
            ),
            (
                "2. Main Interface",
                [
                    "The interface consists of capture, rules, preview, and execution areas. A good workflow is to capture first, enable naming rules one by one, check the preview, then press RENAME.",
                    "before shows the original names recorded at capture time. This is the base input for the naming calculation.",
                    "after shows the result produced by all active rules. This preview updates live, but it does not write anything back to Live until RENAME is pressed.",
                    "The root and replace rules create or rewrite the base text. remove and insert delete or insert text. index, locator, and track append order information or insert locator and track names.",
                    "RENAME writes the current after results back to the captured clips. If there is no capture result or no active rule, it will not take effect.",
                ],
            ),
            (
                "3. Naming Rules",
                [
                    "root replaces the naming base with the text in the input box. It resets the base text instead of appending to it.",
                    "replace replaces all matching target text in the current result. If target is empty, enabling replace has no practical effect.",
                    "remove can delete matching text, or delete a character range using pos, count, and beg / end. beg counts from the start of the string, and end counts from the end.",
                    "insert places text at a specific character position. If pos is beyond the current string length, the text is inserted at the end.",
                    "locator inserts the locator name belonging to the clip's loop segment. It only works when a valid locator exists in the loop range and the clip can be matched to a locator segment.",
                    "track inserts the name of the clip's track. auto behaves like locator auto: it only adds underscores when needed to prevent fields from sticking together.",
                    "index appends an order number. track mode counts clips per track, all mode counts across the whole captured set. start controls the first number, and digits controls zero padding.",
                ],
            ),
            (
                "4. Rule Order and Priority",
                [
                    "Renamer rules run in a fixed order. The final name is recalculated from a stable source name, not from the previous preview result.",
                    "The source name is usually the original clip name recorded at capture time. If it is empty, the track name is used as a fallback. Preview changes do not modify the source name. Only after RENAME is executed successfully does the written name become the next preview base.",
                    "The fixed order is root, replace, remove, locator, track, insert, index.",
                    "root has the highest priority and replaces the original base. replace and remove only affect text that already exists at their stage. locator and track insert fields before insert runs. index is always appended last.",
                ],
            ),
            (
                "5. Preview Behavior",
                [
                    "before and after are not two independent data sources. They are a before-and-after view of the same captured clips.",
                    "before shows the names recorded during capture. after shows target names calculated from the current rules.",
                    "Changing rule switches, rule text, locator names, locator positions, loop range, or track names can refresh preview. Preview refresh does not rename anything; only RENAME writes changes back.",
                    "The capture set itself does not change because preview refreshed. If you add, delete, or move clips, or want another group of tracks, capture again.",
                ],
            ),
            (
                "6. Known Behaviors and Feedback",
                [
                    "Capture again when you switch between selected and all, change selected track, add, delete, or move target clips, want a different loop set, or need before to match the current clip names.",
                    "You do not need to capture again when only changing rule switches, text, positions, digits, mode, loop range, locator names, locator positions, or captured track names, because preview can refresh for these changes.",
                    "Typical cases that do not work as expected include pressing RENAME before capture, having all rules disabled, using IN LOOP without a valid loop, capturing no arrangement clips, enabling replace with an empty target, or enabling locator without a usable locator segment.",
                    "Renamer currently reports feedback as text messages rather than a separate colored status strip. Common messages include no target tracks, loop range unavailable, no matching arrangement clips, captured N clips across M tracks, no captured clips, no active rules, and rename executed on N clips.",
                ],
            ),
            (
                "7. Recommended Workflow",
                [
                    "In Arrangement View, decide whether to process the selected track or all tracks.",
                    "Choose normal capture or IN LOOP capture.",
                    "Check the before list to make sure the captured set is correct.",
                    "Enable naming rules one by one and watch the after list.",
                    "If you use locator, confirm that the loop and locator segments are correct.",
                    "When the final preview is correct, press RENAME to write all names back.",
                    "When the target set changes, capture again instead of only changing rules. This keeps preview, numbering, and locator matching aligned with the current Live Set.",
                ],
            ),
        ],
    },
}


def build_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ManualTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#202125"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#8a8d95"),
            uppercase=True,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#202125"),
            spaceBefore=14,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualSubheading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=colors.HexColor("#202125"),
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=14,
            textColor=colors.HexColor("#33363d"),
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualBullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.3,
            leading=13,
            leftIndent=8 * mm,
            firstLineIndent=-4 * mm,
            textColor=colors.HexColor("#33363d"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualQuote",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            leftIndent=6 * mm,
            rightIndent=6 * mm,
            borderColor=colors.HexColor("#D6D6D6"),
            borderWidth=0.5,
            borderPadding=6,
            backColor=colors.HexColor("#F5F5F2"),
            textColor=colors.HexColor("#33363d"),
            spaceAfter=8,
        )
    )
    return styles


def convert_inline(text: str) -> str:
    escaped = html.escape(text.strip())
    escaped = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def extract_pdf_images(manual: dict) -> list[Path]:
    source_pdf = PACKAGE_ROOT / manual["folder"] / manual["source_pdf"]
    image_dir = EXTRACTED_IMAGE_ROOT / manual["folder"]
    image_dir.mkdir(parents=True, exist_ok=True)
    for old_image in image_dir.glob("*.png"):
        old_image.unlink()

    image_paths: list[Path] = []
    reader = PdfReader(source_pdf)
    counter = 1
    for page_number, page in enumerate(reader.pages, start=1):
        for image in page.images:
            image_path = image_dir / f"{counter:02d}-page-{page_number}.png"
            image_path.write_bytes(image.data)
            image_paths.append(image_path)
            counter += 1
    return image_paths


def paragraph_style_for_heading(level: int, styles: dict[str, ParagraphStyle]) -> ParagraphStyle:
    if level == 1:
        return styles["ManualTitle"]
    if level == 2:
        return styles["ManualHeading"]
    return styles["ManualSubheading"]


def parse_markdown(manual: dict, styles: dict[str, ParagraphStyle], images: list[Path]) -> list:
    md_path = MANUAL_ROOT / manual["english_md"]
    lines = md_path.read_text(encoding="utf-8").splitlines()
    story: list = []
    image_index = 0
    pending_blockquote: list[str] = []
    pending_list: list[str] = []

    def flush_blockquote() -> None:
        nonlocal pending_blockquote
        if not pending_blockquote:
            return
        text = "<br/>".join(convert_inline(line) for line in pending_blockquote)
        story.append(Paragraph(text, styles["ManualQuote"]))
        story.append(Spacer(1, 2 * mm))
        pending_blockquote = []

    def flush_list() -> None:
        nonlocal pending_list
        if not pending_list:
            return
        list_items = []
        for item in pending_list:
            list_items.append(Paragraph(convert_inline(item), styles["ManualBullet"]))
        story.extend(list_items)
        story.append(Spacer(1, 1.5 * mm))
        pending_list = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith(">"):
            flush_list()
            pending_blockquote.append(stripped.lstrip(">").strip())
            continue

        flush_blockquote()

        if not stripped:
            flush_list()
            continue

        if stripped == "---":
            flush_list()
            story.append(Spacer(1, 4 * mm))
            continue

        if stripped.startswith("!["):
            flush_list()
            if image_index < len(images):
                image_path = images[image_index]
                image_index += 1
                story.append(Spacer(1, 2 * mm))
                story.append(Image(str(image_path), width=160 * mm, height=92 * mm, kind="proportional"))
                story.append(Spacer(1, 5 * mm))
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_list()
            level = len(heading.group(1))
            text = convert_inline(heading.group(2))
            style = paragraph_style_for_heading(level, styles)
            story.append(Paragraph(text, style))
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if bullet:
            pending_list.append(f"• {bullet.group(1)}")
            continue
        if numbered:
            pending_list.append(f"{numbered.group(1)}. {numbered.group(2)}")
            continue

        flush_list()
        story.append(Paragraph(convert_inline(stripped), styles["ManualBody"]))
        story.append(Spacer(1, 1.2 * mm))

    flush_blockquote()
    flush_list()
    return story


def draw_page_frame(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8D8D8"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 18 * mm, A4[0] - 18 * mm, 18 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, str(canvas.getPageNumber()))
    canvas.restoreState()


def make_pdf(manual: dict) -> Path:
    package_dir = PACKAGE_ROOT / manual["folder"]
    output_path = package_dir / manual["pdf"]
    styles = build_styles()
    images = extract_pdf_images(manual)
    story = parse_markdown(manual, styles, images)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=manual["title"],
        author="slite.audio",
    )
    doc.build(story, onFirstPage=draw_page_frame, onLaterPages=draw_page_frame)
    return output_path


def write_package_archive(output_zip: Path, manual: dict, pdf_path: Path) -> None:
    package_dir = PACKAGE_ROOT / manual["folder"]
    device_path = package_dir / manual["device"]
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output_zip, "w", ZIP_DEFLATED) as archive:
        archive.write(device_path, f"{manual['folder']}/{manual['device']}")
        archive.write(pdf_path, f"{manual['folder']}/{manual['pdf']}")


def make_zip(manual: dict, pdf_path: Path) -> tuple[Path, Path]:
    package_zip = PACKAGE_ROOT / manual["package_zip"]
    download_zip = DOWNLOAD_ROOT / manual["zip"]

    write_package_archive(package_zip, manual, pdf_path)
    write_package_archive(download_zip, manual, pdf_path)

    return package_zip, download_zip


def main() -> None:
    for manual in MANUALS.values():
        pdf_path = make_pdf(manual)
        package_zip, download_zip = make_zip(manual, pdf_path)
        print(f"Created {pdf_path}")
        print(f"Created {package_zip}")
        print(f"Created {download_zip}")


if __name__ == "__main__":
    main()
