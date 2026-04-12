from __future__ import annotations

import argparse
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = Path.home() / "Zotero" / "zotero.sqlite"
DEFAULT_BIB_PATH = ROOT / "references.bib"
DEFAULT_GROUPS_PATH = ROOT / "references_groups.md"
GENERATED_BEGIN = "% BEGIN ZOTERO CURATED PACK"
GENERATED_END = "% END ZOTERO CURATED PACK"

GROUP_ORDER = (
    "Datasets and Benchmarks",
    "Surveys and Reviews",
    "Core Surface Defect Detection",
    "YOLO and Lightweight Variants",
    "Cross-domain Transfer Cases",
    "Foundational Detection Baselines",
)

SCOPED_COLLECTION_MARKERS = (
    "金属表面缺陷检测 / GC10-Net&NEU-DET",
    "金属表面缺陷检测 / GC10-Net&NEU-DET / new_innovation",
    "金属表面缺陷检测 / YOLO系列创新",
    "金属表面缺陷检测 / 计算机视觉CV / NET-DET&GC-NET",
    "金属表面缺陷检测 / 计算机视觉CV / 数据库-论文",
)

MANUAL_GROUP_OVERRIDES = {
    "song2013neudet": "Datasets and Benchmarks",
    "lv2020gc10det": "Datasets and Benchmarks",
    "fang2020review": "Surveys and Reviews",
    "zou2021review": "Surveys and Reviews",
    "liu2024slr": "Surveys and Reviews",
    "redmon2016yolo": "Foundational Detection Baselines",
    "lin2017focal": "Foundational Detection Baselines",
    "jocher2024ultralytics": "Foundational Detection Baselines",
}

EXACT_TITLE_EXCLUDES = {
    "damo-yolo: a report on real-time object detection design",
    "when object detection meets knowledge distillation: a survey",
}

POSITIVE_RE = re.compile(
    r"(defect|surface|steel|metal|inspection|weld|corrosion|dataset|benchmark|\bgc10\b|\bneu\b|\bmvtec\b)",
    re.IGNORECASE,
)
OFF_DOMAIN_RE = re.compile(
    r"(tomato|pavement|uav|remote sensing|underwater|auroral|thermal spot|bridge inspection|iot|lidar|weed|soap bar|pv panels|medical)",
    re.IGNORECASE,
)
ALLOW_OFF_DOMAIN_RE = re.compile(r"(defect|surface|steel|metal|weld|rail|inspection|dataset|benchmark)", re.IGNORECASE)
REVIEW_RE = re.compile(r"(review|survey|progress|comprehensive)", re.IGNORECASE)
DATASET_RE = re.compile(r"(dataset|database|benchmark|\bgc10\b|\bneu\b|\bmvtec\b)", re.IGNORECASE)
YOLO_RE = re.compile(r"(yolo|detr|rtdetr|fpn)", re.IGNORECASE)
CROSS_DOMAIN_RE = re.compile(r"(rail|weld|skin|civil infrastructure)", re.IGNORECASE)
STOPWORDS = {
    "a",
    "an",
    "and",
    "applied",
    "based",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "real",
    "the",
    "to",
    "using",
    "with",
}


@dataclass
class ReferenceItem:
    title: str
    year: str
    item_type: str
    authors: list[str] = field(default_factory=list)
    fields: dict[str, str] = field(default_factory=dict)
    collections: list[str] = field(default_factory=list)
    source: str = "zotero"
    item_id: int | None = None
    doi: str = ""
    cite_key: str = ""
    collection_note: str = ""

    def dedupe_key(self) -> str:
        if self.doi:
            return f"doi:{self.doi.lower()}"
        return f"title:{normalize_title(self.title)}"

    def score(self) -> int:
        important = ("publicationTitle", "proceedingsTitle", "volume", "issue", "pages", "url")
        return (
            len(self.authors) * 3
            + len(self.collections) * 2
            + sum(1 for field_name in important if self.fields.get(field_name))
            + (5 if self.doi else 0)
        )


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", slugify_ascii(clean_title(value)).lower())


def slugify_ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip()


def clean_title(title: str) -> str:
    cleaned = title.strip()
    cleaned = re.sub(r"^[\[\(【][^]\)】]{0,40}[\]\)】]\s*", "", cleaned)
    cleaned = cleaned.replace("—", "-").replace("–", "-").replace("−", "-")
    cleaned = re.sub(r"\s+:\s+", ": ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def parse_year(value: str) -> str:
    match = re.search(r"(19|20)\d{2}", value or "")
    return match.group(0) if match else "nodate"


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
    }
    escaped = []
    for char in value:
        escaped.append(replacements.get(char, char))
    return "".join(escaped)


def split_bib_entries(text: str) -> list[str]:
    entries: list[str] = []
    index = 0
    while True:
        start = text.find("@", index)
        if start == -1:
            break
        brace_start = text.find("{", start)
        if brace_start == -1:
            break
        depth = 0
        for pos in range(brace_start, len(text)):
            char = text[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    entries.append(text[start : pos + 1].strip())
                    index = pos + 1
                    break
        else:
            break
    return entries


def parse_manual_entry(entry_text: str) -> ReferenceItem | None:
    key_match = re.match(r"@\w+\{([^,]+),", entry_text)
    if not key_match:
        return None
    entry_key = key_match.group(1).strip()
    fields = {}
    for match in re.finditer(r"(?ms)^\s*([A-Za-z]+)\s*=\s*\{(.*?)\}\s*,?\s*$", entry_text):
        fields[match.group(1)] = match.group(2).strip()
    title = fields.get("title", "").strip()
    if not title:
        return None
    authors = [author.strip() for author in fields.get("author", "").split(" and ") if author.strip()]
    item_type_match = re.match(r"@(\w+)\{", entry_text)
    item_type = item_type_match.group(1) if item_type_match else "misc"
    item = ReferenceItem(
        title=clean_title(title),
        year=fields.get("year", "nodate").strip() or "nodate",
        item_type=item_type,
        authors=authors,
        fields=fields,
        collections=[],
        source="manual",
        doi=fields.get("doi", "").strip(),
        cite_key=entry_key,
    )
    return item


def strip_generated_block(text: str) -> str:
    if GENERATED_BEGIN not in text:
        return text.rstrip()
    before = text.split(GENERATED_BEGIN, 1)[0]
    return before.rstrip()


def load_manual_entries(bib_path: Path) -> tuple[str, dict[str, ReferenceItem], set[str], set[str]]:
    if bib_path.exists():
        raw_text = bib_path.read_text(encoding="utf-8")
    else:
        raw_text = ""
    manual_text = strip_generated_block(raw_text)
    entries = {}
    doi_keys: set[str] = set()
    title_keys: set[str] = set()
    for entry_text in split_bib_entries(manual_text):
        entry = parse_manual_entry(entry_text)
        if not entry:
            continue
        entries[entry.cite_key] = entry
        if entry.doi:
            doi_keys.add(entry.doi.lower())
        title_keys.add(normalize_title(entry.title))
    return manual_text, entries, doi_keys, title_keys


def load_zotero_items(db_path: Path) -> list[ReferenceItem]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row

    items_by_id: dict[int, ReferenceItem] = {}
    for row in conn.execute(
        """
        SELECT i.itemID, it.typeName
        FROM items i
        JOIN itemTypes it ON it.itemTypeID = i.itemTypeID
        WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems)
          AND it.typeName NOT IN ('attachment', 'note', 'annotation')
        """
    ):
        items_by_id[row["itemID"]] = ReferenceItem(
            title="",
            year="nodate",
            item_type=row["typeName"],
            item_id=row["itemID"],
        )

    for row in conn.execute(
        """
        SELECT id.itemID, f.fieldName, v.value
        FROM itemData id
        JOIN fields f ON f.fieldID = id.fieldID
        JOIN itemDataValues v ON v.valueID = id.valueID
        WHERE id.itemID IN (
            SELECT itemID FROM items WHERE itemID NOT IN (SELECT itemID FROM deletedItems)
        )
        """
    ):
        item = items_by_id.get(row["itemID"])
        if not item:
            continue
        item.fields[row["fieldName"]] = row["value"]

    for item in items_by_id.values():
        item.title = clean_title(item.fields.get("title", ""))
        item.year = parse_year(item.fields.get("date", ""))
        item.doi = item.fields.get("DOI", "").strip()

    creator_query = """
        SELECT ic.itemID, ct.creatorType, c.firstName, c.lastName, c.fieldMode, ic.orderIndex
        FROM itemCreators ic
        JOIN creators c ON c.creatorID = ic.creatorID
        JOIN creatorTypes ct ON ct.creatorTypeID = ic.creatorTypeID
        ORDER BY ic.itemID, ic.orderIndex
    """
    for row in conn.execute(creator_query):
        item = items_by_id.get(row["itemID"])
        if not item:
            continue
        if row["creatorType"] not in {"author", "inventor", "programmer"}:
            continue
        first = (row["firstName"] or "").strip()
        last = (row["lastName"] or "").strip()
        if last and first:
            item.authors.append(f"{last}, {first}")
        elif last:
            item.authors.append(last)
        elif first:
            item.authors.append(first)

    collection_query = """
        WITH RECURSIVE tree(collectionID, path) AS (
            SELECT collectionID, collectionName
            FROM collections
            WHERE parentCollectionID IS NULL
            UNION ALL
            SELECT c.collectionID, tree.path || ' / ' || c.collectionName
            FROM collections c
            JOIN tree ON c.parentCollectionID = tree.collectionID
        )
        SELECT ci.itemID, tree.path
        FROM collectionItems ci
        JOIN tree ON tree.collectionID = ci.collectionID
        ORDER BY ci.itemID, tree.path
    """
    for row in conn.execute(collection_query):
        item = items_by_id.get(row["itemID"])
        if item:
            item.collections.append(row["path"])

    conn.close()
    return [item for item in items_by_id.values() if item.title]


def is_relevant(item: ReferenceItem) -> bool:
    in_scoped_collection = any(
        path == "金属表面缺陷检测" or any(marker in path for marker in SCOPED_COLLECTION_MARKERS)
        for path in item.collections
    )
    if not in_scoped_collection:
        return False

    title_lower = item.title.lower()
    if title_lower in EXACT_TITLE_EXCLUDES:
        return False

    combined_text = "\n".join(
        [
            item.title,
            item.fields.get("abstractNote", ""),
            " ".join(item.collections),
        ]
    )
    if not POSITIVE_RE.search(combined_text):
        return False

    if OFF_DOMAIN_RE.search(item.title) and not ALLOW_OFF_DOMAIN_RE.search(item.title):
        return False

    return True


def merge_duplicate(existing: ReferenceItem, incoming: ReferenceItem) -> ReferenceItem:
    if incoming.score() > existing.score():
        primary, secondary = incoming, existing
    else:
        primary, secondary = existing, incoming

    merged = ReferenceItem(
        title=primary.title,
        year=primary.year,
        item_type=primary.item_type,
        authors=primary.authors or secondary.authors,
        fields={**secondary.fields, **primary.fields},
        collections=sorted(set(primary.collections) | set(secondary.collections)),
        source=primary.source,
        item_id=primary.item_id or secondary.item_id,
        doi=primary.doi or secondary.doi,
    )
    return merged


def dedupe_items(items: list[ReferenceItem]) -> list[ReferenceItem]:
    deduped: dict[str, ReferenceItem] = {}
    for item in items:
        key = item.dedupe_key()
        if key in deduped:
            deduped[key] = merge_duplicate(deduped[key], item)
        else:
            deduped[key] = item
    return list(deduped.values())


def build_cite_key(item: ReferenceItem, used_keys: set[str]) -> str:
    if item.cite_key:
        used_keys.add(item.cite_key)
        return item.cite_key

    surname_source = item.authors[0] if item.authors else "ref"
    surname = slugify_ascii(surname_source.split(",", 1)[0]).lower() or "ref"
    year = item.year if item.year != "nodate" else "nodate"
    words = re.findall(r"[A-Za-z0-9]+", slugify_ascii(item.title).lower())
    meaningful = [word for word in words if word not in STOPWORDS]
    title_slug = "".join(meaningful[:3]) or (f"item{item.item_id}" if item.item_id else "paper")
    base = f"{surname}{year}{title_slug}"
    base = re.sub(r"[^a-z0-9]+", "", base) or "refnodatepaper"

    candidate = base
    suffix_index = 0
    while candidate in used_keys:
        suffix_index += 1
        candidate = f"{base}{chr(ord('a') + suffix_index - 1)}"
    used_keys.add(candidate)
    return candidate


def classify_group(item: ReferenceItem) -> str:
    if item.source == "manual" and item.cite_key in MANUAL_GROUP_OVERRIDES:
        return MANUAL_GROUP_OVERRIDES[item.cite_key]

    title = item.title
    if DATASET_RE.search(title):
        return "Datasets and Benchmarks"
    if REVIEW_RE.search(title):
        return "Surveys and Reviews"
    if CROSS_DOMAIN_RE.search(title):
        return "Cross-domain Transfer Cases"
    if YOLO_RE.search(title):
        return "YOLO and Lightweight Variants"
    if re.search(r"(defect|inspection|steel|metal|surface)", title, re.IGNORECASE):
        return "Core Surface Defect Detection"
    return "Foundational Detection Baselines"


def format_bib_entry(item: ReferenceItem) -> str:
    type_map = {
        "journalArticle": "article",
        "conferencePaper": "inproceedings",
        "preprint": "article",
        "book": "book",
        "computerProgram": "misc",
        "article": "article",
    }
    bib_type = type_map.get(item.item_type, "misc")

    lines = [f"@{bib_type}{{{item.cite_key},"]
    ordered_fields: list[tuple[str, str]] = []

    if item.authors:
        ordered_fields.append(("author", " and ".join(item.authors)))

    ordered_fields.append(("title", item.title))

    journal = item.fields.get("publicationTitle")
    proceedings = item.fields.get("proceedingsTitle") or item.fields.get("conferenceName")
    if journal:
        ordered_fields.append(("journal", journal))
    elif proceedings:
        ordered_fields.append(("booktitle", proceedings))

    for field_name, bib_name in (
        ("volume", "volume"),
        ("issue", "number"),
        ("pages", "pages"),
        ("publisher", "publisher"),
    ):
        if item.fields.get(field_name):
            ordered_fields.append((bib_name, item.fields[field_name]))

    if item.year != "nodate":
        ordered_fields.append(("year", item.year))

    if item.doi:
        ordered_fields.append(("doi", item.doi))
    if item.fields.get("url"):
        ordered_fields.append(("url", item.fields["url"]))
    if item.item_type == "preprint":
        ordered_fields.append(("note", "Preprint"))

    for field_name, value in ordered_fields:
        if field_name == "url":
            rendered = value
        else:
            rendered = latex_escape(value)
        lines.append(f"  {field_name} = {{{rendered}}},")

    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("}")
    return "\n".join(lines)


def format_group_markdown(items: list[ReferenceItem]) -> str:
    grouped: dict[str, list[ReferenceItem]] = {group: [] for group in GROUP_ORDER}
    for item in items:
        grouped[classify_group(item)].append(item)

    lines = [
        "# Reference Groups",
        "",
        "This list keeps the existing manual anchors in `references.bib` and appends a deduplicated Zotero subset for metal surface defect writing.",
        "",
    ]

    for group in GROUP_ORDER:
        records = sorted(grouped[group], key=lambda ref: (ref.year, ref.title.lower()), reverse=True)
        if not records:
            continue
        lines.append(f"## {group} ({len(records)})")
        for item in records:
            year = item.year if item.year != "nodate" else "n.d."
            source_note = "existing references.bib" if item.source == "manual" else "; ".join(item.collections[:2])
            lines.append(f"- `{item.cite_key}` | {year} | {item.title} | source: {source_note}")
        lines.append("")

    lines.append("## Notes")
    lines.append("- `song2013neudet` and `lv2020gc10det` are preserved from the existing `references.bib`; they were not found as Zotero items in the current library.")
    lines.append("- Zotero duplicates were merged by DOI first, then by normalized title.")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(
    manual_text: str,
    manual_entries: dict[str, ReferenceItem],
    zotero_entries: list[ReferenceItem],
    bib_path: Path,
    groups_path: Path,
) -> None:
    used_keys = set(manual_entries)
    for item in zotero_entries:
        item.cite_key = build_cite_key(item, used_keys)

    generated_entries = "\n\n".join(format_bib_entry(item) for item in zotero_entries)
    manual_block = manual_text.strip()
    parts = []
    if manual_block:
        parts.append(manual_block)
    parts.append(GENERATED_BEGIN)
    if generated_entries:
        parts.append(generated_entries)
    parts.append(GENERATED_END)
    bib_path.write_text("\n\n".join(parts).strip() + "\n", encoding="utf-8")

    all_items = list(manual_entries.values()) + zotero_entries
    groups_path.write_text(format_group_markdown(all_items), encoding="utf-8")


def curate_references(db_path: Path, manual_dois: set[str], manual_titles: set[str]) -> list[ReferenceItem]:
    zotero_items = [item for item in load_zotero_items(db_path) if is_relevant(item)]
    zotero_items = dedupe_items(zotero_items)
    curated = []
    for item in zotero_items:
        if item.doi and item.doi.lower() in manual_dois:
            continue
        if normalize_title(item.title) in manual_titles:
            continue
        curated.append(item)
    curated.sort(key=lambda ref: (ref.year, ref.title.lower()), reverse=True)
    return curated


def main() -> int:
    if hasattr(__import__("sys").stdout, "reconfigure"):
        __import__("sys").stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Export a curated Zotero reference pack for paper writing.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to Zotero sqlite database.")
    parser.add_argument("--bib-path", type=Path, default=DEFAULT_BIB_PATH, help="Target BibTeX file.")
    parser.add_argument("--groups-path", type=Path, default=DEFAULT_GROUPS_PATH, help="Target markdown group list.")
    args = parser.parse_args()

    if not args.db_path.exists():
        raise FileNotFoundError(f"Zotero database not found: {args.db_path}")

    manual_text, manual_entries, manual_dois, manual_titles = load_manual_entries(args.bib_path)
    curated = curate_references(args.db_path, manual_dois, manual_titles)
    write_outputs(manual_text, manual_entries, curated, args.bib_path, args.groups_path)

    print(f"manual_entries={len(manual_entries)}")
    print(f"zotero_curated_entries={len(curated)}")
    print(f"bib_path={args.bib_path}")
    print(f"groups_path={args.groups_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
