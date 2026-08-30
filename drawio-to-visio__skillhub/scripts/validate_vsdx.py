#!/usr/bin/env python3
"""Validate a VSDX OPC relationship chain and optional page text."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree


CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
PACKAGE_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOCUMENT_RELS_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
VISIO_NS = "http://schemas.microsoft.com/office/visio/2012/main"

ROOT_REL_TYPE = "http://schemas.microsoft.com/visio/2010/relationships/document"
PAGES_REL_TYPE = "http://schemas.microsoft.com/visio/2010/relationships/pages"
PAGE_REL_TYPE = "http://schemas.microsoft.com/visio/2010/relationships/page"

CONTENT_TYPES_PART = "[Content_Types].xml"
ROOT_RELS_PART = "_rels/.rels"
DOCUMENT_PART = "visio/document.xml"
DOCUMENT_RELS_PART = "visio/_rels/document.xml.rels"
PAGES_PART = "visio/pages/pages.xml"
PAGES_RELS_PART = "visio/pages/_rels/pages.xml.rels"

REQUIRED_CONTENT_TYPES = {
    DOCUMENT_PART: "application/vnd.ms-visio.drawing.main+xml",
    PAGES_PART: "application/vnd.ms-visio.pages+xml",
}
MAX_MEMBERS = 20_000
MAX_TOTAL_UNCOMPRESSED = 512 * 1024 * 1024
MAX_XML_PART = 64 * 1024 * 1024


def qname(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_xml_part(
    archive: zipfile.ZipFile,
    name: str,
    expected_root: str,
) -> ElementTree.Element:
    try:
        info = archive.getinfo(name)
    except KeyError:
        fail(f"missing required entry: {name}")
    if info.file_size > MAX_XML_PART:
        fail(f"XML part is too large to validate safely: {name}")

    try:
        with archive.open(info) as stream:
            root = ElementTree.parse(stream).getroot()
    except (ElementTree.ParseError, OSError) as exc:
        fail(f"invalid XML in {name}: {exc}")
    if root.tag != expected_root:
        fail(f"unexpected root element in {name}: {root.tag}")
    return root


def relationship_map(root: ElementTree.Element, part_name: str) -> dict[str, dict[str, str]]:
    relationships: dict[str, dict[str, str]] = {}
    for relationship in root:
        if relationship.tag != qname(PACKAGE_RELS_NS, "Relationship"):
            fail(f"unexpected element in {part_name}: {relationship.tag}")
        rel_id = relationship.get("Id", "")
        rel_type = relationship.get("Type", "")
        target = relationship.get("Target", "")
        if not rel_id or not rel_type or not target:
            fail(f"incomplete relationship in {part_name}")
        if rel_id in relationships:
            fail(f"duplicate relationship ID in {part_name}: {rel_id}")
        target_mode = relationship.get("TargetMode", "Internal")
        if target_mode not in {"Internal", "External"}:
            fail(f"invalid TargetMode in {part_name}: {target_mode}")
        relationships[rel_id] = {
            "type": rel_type,
            "target": target,
            "target_mode": target_mode,
        }
    return relationships


def resolve_target(source_part: str, target: str, part_name: str) -> str:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        fail(f"external target is not allowed in {part_name}: {target}")
    decoded = unquote(parsed.path).replace("\\", "/")
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source_part), decoded))
    if resolved == ".." or resolved.startswith("../") or resolved.startswith("/"):
        fail(f"relationship target escapes the package in {part_name}: {target}")
    return resolved


def require_relationship(
    relationships: dict[str, dict[str, str]],
    relationship_type: str,
    source_part: str,
    rels_part: str,
) -> str:
    matches = [rel for rel in relationships.values() if rel["type"] == relationship_type]
    if len(matches) != 1:
        fail(f"expected exactly one {relationship_type} relationship in {rels_part}")
    relationship = matches[0]
    if relationship["target_mode"].lower() == "external":
        fail(f"required relationship is external in {rels_part}")
    return resolve_target(source_part, relationship["target"], rels_part)


def content_type_overrides(root: ElementTree.Element) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for element in root:
        if element.tag not in {
            qname(CONTENT_TYPES_NS, "Default"),
            qname(CONTENT_TYPES_NS, "Override"),
        }:
            fail(f"unexpected element in {CONTENT_TYPES_PART}: {element.tag}")
        if element.tag == qname(CONTENT_TYPES_NS, "Override"):
            raw_part_name = element.get("PartName", "")
            content_type = element.get("ContentType", "")
            if not raw_part_name.startswith("/") or raw_part_name.startswith("//"):
                fail(f"Override PartName must start with one slash in {CONTENT_TYPES_PART}")
            part_name = raw_part_name[1:]
            if not part_name or not content_type:
                fail(f"incomplete Override in {CONTENT_TYPES_PART}")
            if part_name in overrides:
                fail(f"duplicate Override in {CONTENT_TYPES_PART}: {raw_part_name}")
            overrides[part_name] = content_type
    return overrides


def validate_page(
    archive: zipfile.ZipFile,
    page_part: str,
    expected_text: list[str],
) -> tuple[int, int, set[str]]:
    try:
        info = archive.getinfo(page_part)
    except KeyError:
        fail(f"referenced Visio page is missing: {page_part}")
    if info.file_size > MAX_XML_PART:
        fail(f"Visio page is too large to validate safely: {page_part}")

    shape_count = 0
    connect_count = 0
    found: set[str] = set()
    root_seen = False
    text_depth = 0
    shape_depth = 0

    try:
        with archive.open(info) as stream:
            for event, element in ElementTree.iterparse(stream, events=("start", "end")):
                if event == "start":
                    if not root_seen:
                        root_seen = True
                        if element.tag != qname(VISIO_NS, "PageContents"):
                            fail(f"unexpected root element in {page_part}: {element.tag}")
                    if element.tag == qname(VISIO_NS, "Shape"):
                        shape_depth += 1
                    if element.tag == qname(VISIO_NS, "Text"):
                        text_depth += 1
                    continue

                if element.tag == qname(VISIO_NS, "Shape"):
                    shape_count += 1
                    shape_depth -= 1
                elif element.tag == qname(VISIO_NS, "Connect"):
                    connect_count += 1
                elif element.tag == qname(VISIO_NS, "Text"):
                    if shape_depth > 0:
                        page_text = "".join(element.itertext())
                        for phrase in expected_text:
                            if phrase in page_text:
                                found.add(phrase)
                    text_depth -= 1

                if text_depth == 0:
                    element.clear()
    except (ElementTree.ParseError, OSError) as exc:
        fail(f"invalid XML in {page_part}: {exc}")

    if not root_seen:
        fail(f"empty Visio page: {page_part}")
    return shape_count, connect_count, found


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--expect", action="append", default=[])
    args = parser.parse_args()

    if any(not phrase for phrase in args.expect):
        fail("--expect text must not be empty")

    path = args.file.expanduser().resolve()
    if not path.is_file():
        fail(f"VSDX not found: {path}")
    if path.stat().st_size < 1024:
        fail("VSDX is unexpectedly small")

    with path.open("rb") as stream:
        prefix = stream.read(8)
    if prefix.startswith(b"%PDF"):
        fail("output is a PDF renamed as VSDX")
    if not prefix.startswith(b"PK"):
        fail("output is not a ZIP/OPC package")

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        fail(f"invalid ZIP package: {exc}")

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            fail("VSDX contains too many package members")
        if sum(info.file_size for info in infos) > MAX_TOTAL_UNCOMPRESSED:
            fail("VSDX uncompressed size exceeds the validation limit")

        for info in infos:
            member_name = info.filename[:-1] if info.is_dir() else info.filename
            if (
                not member_name
                or member_name.startswith("/")
                or "\\" in member_name
                or any(part in {"", ".", ".."} for part in member_name.split("/"))
                or posixpath.normpath(member_name) != member_name
            ):
                fail(f"invalid package member path: {info.filename}")

        bad_member = archive.testzip()
        if bad_member:
            fail(f"corrupt ZIP member: {bad_member}")

        names = set(archive.namelist())
        if len(names) != len(infos):
            fail("VSDX contains duplicate package member names")

        content_types_root = parse_xml_part(
            archive,
            CONTENT_TYPES_PART,
            qname(CONTENT_TYPES_NS, "Types"),
        )
        overrides = content_type_overrides(content_types_root)
        for part_name, expected_type in REQUIRED_CONTENT_TYPES.items():
            if overrides.get(part_name) != expected_type:
                fail(f"missing or invalid content type for {part_name}")

        root_rels = relationship_map(
            parse_xml_part(archive, ROOT_RELS_PART, qname(PACKAGE_RELS_NS, "Relationships")),
            ROOT_RELS_PART,
        )
        if require_relationship(root_rels, ROOT_REL_TYPE, "", ROOT_RELS_PART) != DOCUMENT_PART:
            fail(f"root relationships do not reference {DOCUMENT_PART}")

        parse_xml_part(archive, DOCUMENT_PART, qname(VISIO_NS, "VisioDocument"))
        document_rels = relationship_map(
            parse_xml_part(
                archive,
                DOCUMENT_RELS_PART,
                qname(PACKAGE_RELS_NS, "Relationships"),
            ),
            DOCUMENT_RELS_PART,
        )
        if require_relationship(
            document_rels,
            PAGES_REL_TYPE,
            DOCUMENT_PART,
            DOCUMENT_RELS_PART,
        ) != PAGES_PART:
            fail(f"document relationships do not reference {PAGES_PART}")

        pages_root = parse_xml_part(archive, PAGES_PART, qname(VISIO_NS, "Pages"))
        pages_rels = relationship_map(
            parse_xml_part(
                archive,
                PAGES_RELS_PART,
                qname(PACKAGE_RELS_NS, "Relationships"),
            ),
            PAGES_RELS_PART,
        )

        referenced_pages: list[str] = []
        for page in pages_root.findall(qname(VISIO_NS, "Page")):
            rel_element = page.find(qname(VISIO_NS, "Rel"))
            rel_id = rel_element.get(qname(DOCUMENT_RELS_NS, "id"), "") if rel_element is not None else ""
            if not rel_id or rel_id not in pages_rels:
                fail("Visio page has a missing or unknown relationship ID")
            relationship = pages_rels[rel_id]
            if relationship["type"] != PAGE_REL_TYPE:
                fail(f"unexpected relationship type for Visio page: {relationship['type']}")
            if relationship["target_mode"].lower() == "external":
                fail("Visio page relationship cannot be external")
            page_part = resolve_target(PAGES_PART, relationship["target"], PAGES_RELS_PART)
            if page_part in referenced_pages:
                fail(f"duplicate Visio page relationship target: {page_part}")
            if overrides.get(page_part) != "application/vnd.ms-visio.page+xml":
                fail(f"missing or invalid content type for {page_part}")
            if page_part not in names:
                fail(f"referenced Visio page is missing: {page_part}")
            referenced_pages.append(page_part)

        if not referenced_pages:
            fail("no referenced Visio pages found")

        shape_count = 0
        connect_count = 0
        found_text: set[str] = set()
        for page_part in referenced_pages:
            page_shapes, page_connects, page_found = validate_page(
                archive,
                page_part,
                args.expect,
            )
            shape_count += page_shapes
            connect_count += page_connects
            found_text.update(page_found)

        if shape_count < 1:
            fail("no Visio shapes found in referenced pages")
        missing_text = [phrase for phrase in args.expect if phrase not in found_text]
        if missing_text:
            fail(f"missing expected page text: {', '.join(missing_text)}")

    result = {
        "status": "PASS",
        "file": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "pages": len(referenced_pages),
        "shapes": shape_count,
        "connect_records": connect_count,
        "expected_text_checked": len(args.expect),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
