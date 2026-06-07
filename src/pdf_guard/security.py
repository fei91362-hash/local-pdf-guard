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
) -> None:
    if not owner_password:
        raise ValueError("Owner password is required.")
    permissions = permissions or PermissionOptions()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    allow = _build_permissions(permissions)
    with pikepdf.open(input_path) as pdf:
        _strip_metadata(pdf)
        pdf.save(
            output_path,
            encryption=pikepdf.Encryption(
                owner=owner_password,
                user=user_password or "",
                R=6,
                allow=allow,
            ),
        )


def is_encrypted(path: Path, password: str | None = "") -> bool:
    with pikepdf.open(path, password=password or "") as pdf:
        return bool(pdf.is_encrypted)


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


def _strip_metadata(pdf: pikepdf.Pdf) -> None:
    try:
        with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=True) as meta:
            for key in list(meta.keys()):
                del meta[key]
    except Exception:
        pass
    try:
        pdf.docinfo.clear()
    except Exception:
        pass

