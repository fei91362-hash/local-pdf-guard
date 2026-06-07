from __future__ import annotations

from pathlib import Path

import pikepdf

from .models import PermissionOptions


def encrypt_with_permissions(
    input_path: Path,
    output_path: Path,
    owner_password: str,
    user_password: str = "",
    permissions: PermissionOptions | None = None,
) -> list[str]:
    if not owner_password:
        raise ValueError("Owner password is required.")
    permissions = permissions or PermissionOptions()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    allow = _build_permissions(permissions)
    with pikepdf.open(input_path) as pdf:
        sanitized_items = sanitize_pdf_structure(pdf)
        pdf.save(
            output_path,
            encryption=pikepdf.Encryption(
                owner=owner_password,
                user=user_password or "",
                R=6,
                allow=allow,
            ),
        )
    return sanitized_items


def is_encrypted(path: Path, password: str | None = "") -> bool:
    with pikepdf.open(path, password=password or "") as pdf:
        return bool(pdf.is_encrypted)


def inspect_pdf_structure(path: Path, password: str | None = "") -> tuple[list[str], dict[str, bool]]:
    warnings: list[str] = []
    status: dict[str, bool] = {}
    with pikepdf.open(path, password=password or "") as pdf:
        root = pdf.Root
        has_metadata = "/Metadata" in root or bool(getattr(pdf, "docinfo", None))
        has_open_action = "/OpenAction" in root
        has_names = "/Names" in root
        has_acroform = "/AcroForm" in root
        has_outlines = "/Outlines" in root

        status.update(
            {
                "metadata_present": bool(has_metadata),
                "open_action_present": bool(has_open_action),
                "names_present": bool(has_names),
                "acroform_present": bool(has_acroform),
                "outlines_present": bool(has_outlines),
            }
        )

        if has_metadata:
            warnings.append("metadata_present")
        if has_open_action:
            warnings.append("open_action_present")
        if has_names:
            warnings.append("names_dictionary_present")
        if has_acroform:
            warnings.append("acroform_present")
        if has_outlines:
            warnings.append("outlines_present")

        annotation_count = 0
        link_or_action_count = 0
        for page in pdf.pages:
            annots = page.get("/Annots", [])
            annotation_count += len(annots)
            for annot in annots:
                try:
                    if "/A" in annot or "/URI" in annot:
                        link_or_action_count += 1
                except Exception:
                    continue
        status["annotations_present"] = annotation_count > 0
        status["link_or_action_annotations_present"] = link_or_action_count > 0
        if annotation_count:
            warnings.append(f"annotations_present:{annotation_count}")
        if link_or_action_count:
            warnings.append(f"link_or_action_annotations_present:{link_or_action_count}")
    return warnings, status


def sanitize_pdf_structure(pdf: pikepdf.Pdf) -> list[str]:
    sanitized: list[str] = []
    sanitized.extend(_strip_metadata(pdf))
    root = pdf.Root

    for key, label in (
        ("/OpenAction", "open_action"),
        ("/AA", "additional_actions"),
        ("/Outlines", "outlines"),
        ("/Names", "names"),
        ("/AcroForm", "acroform"),
        ("/Metadata", "root_metadata"),
    ):
        try:
            if key in root:
                del root[key]
                sanitized.append(label)
        except Exception:
            pass

    for page in pdf.pages:
        try:
            if "/Annots" in page:
                del page["/Annots"]
                sanitized.append("page_annotations")
        except Exception:
            pass
        try:
            if "/AA" in page:
                del page["/AA"]
                sanitized.append("page_additional_actions")
        except Exception:
            pass
    return sorted(set(sanitized))


def _build_permissions(options: PermissionOptions) -> pikepdf.Permissions:
    return pikepdf.Permissions(
        accessibility=True,
        extract=options.allow_copy,
        modify_annotation=options.allow_annotate,
        modify_assembly=options.allow_assemble,
        modify_form=options.allow_form,
        modify_other=options.allow_modify,
        print_lowres=options.allow_print,
        print_highres=options.allow_print,
    )


def _strip_metadata(pdf: pikepdf.Pdf) -> list[str]:
    sanitized: list[str] = []
    try:
        with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=True) as meta:
            for key in list(meta.keys()):
                del meta[key]
                sanitized.append("xmp_metadata")
    except Exception:
        pass
    try:
        if pdf.docinfo:
            pdf.docinfo.clear()
            sanitized.append("docinfo")
    except Exception:
        pass
    return sorted(set(sanitized))
