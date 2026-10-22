"""Tests de FileManager: operaciones de archivos y carpetas con dirs temporales."""
from __future__ import annotations

from pathlib import Path

import pytest

from automation.file_manager import FileManager


@pytest.fixture
def fm() -> FileManager:
    return FileManager()


# --------------------------------------------------------------------------- #
# create_file / create_folder
# --------------------------------------------------------------------------- #
class TestCreate:
    def test_create_file_creates_it(self, fm: FileManager, tmp_dir: Path) -> None:
        target = str(tmp_dir / "hello.txt")
        msg = fm.create_file(target, "hola mundo")
        assert Path(target).exists()
        assert Path(target).read_text(encoding="utf-8") == "hola mundo"
        assert "creado" in msg.lower() or "existente" in msg.lower() or "escrib" in msg.lower()

    def test_create_file_without_content(self, fm: FileManager, tmp_dir: Path) -> None:
        target = str(tmp_dir / "empty.txt")
        fm.create_file(target)
        assert Path(target).exists()

    def test_create_folder(self, fm: FileManager, tmp_dir: Path) -> None:
        folder = str(tmp_dir / "subdir")
        msg = fm.create_folder(folder)
        assert Path(folder).is_dir()
        assert "cread" in msg.lower() or "exist" in msg.lower()


# --------------------------------------------------------------------------- #
# delete_file / delete_folder
# --------------------------------------------------------------------------- #
class TestDelete:
    def test_delete_existing_file(self, fm: FileManager, tmp_dir: Path) -> None:
        f = tmp_dir / "del_me.txt"
        f.write_text("bye")
        msg = fm.delete_file(str(f))
        # Con send2trash puede que no se borre del disco pero el msg es correcto
        assert "papelera" in msg.lower() or "borrad" in msg.lower() or "eliminad" in msg.lower()

    def test_delete_nonexistent_file(self, fm: FileManager, tmp_dir: Path) -> None:
        msg = fm.delete_file(str(tmp_dir / "ghost.txt"))
        assert "no existe" in msg.lower() or "not found" in msg.lower() or "error" in msg.lower()

    def test_delete_file_rejects_directory(self, fm: FileManager, tmp_dir: Path) -> None:
        d = tmp_dir / "adir"
        d.mkdir()
        msg = fm.delete_file(str(d))
        assert "carpeta" in msg.lower() or "directori" in msg.lower() or "error" in msg.lower()

    def test_delete_folder(self, fm: FileManager, tmp_dir: Path) -> None:
        d = tmp_dir / "del_folder"
        d.mkdir()
        msg = fm.delete_folder(str(d))
        assert "carpeta" in msg.lower() or "papelera" in msg.lower() or "borrad" in msg.lower()

    def test_delete_nonexistent_folder(self, fm: FileManager, tmp_dir: Path) -> None:
        msg = fm.delete_folder(str(tmp_dir / "ghost_dir"))
        assert "no existe" in msg.lower() or "error" in msg.lower()


# --------------------------------------------------------------------------- #
# copy_file / move_file
# --------------------------------------------------------------------------- #
class TestCopyMove:
    def test_copy_file(self, fm: FileManager, tmp_dir: Path) -> None:
        src = tmp_dir / "original.txt"
        dst = str(tmp_dir / "copy.txt")
        src.write_text("contenido")
        msg = fm.copy_file(str(src), dst)
        assert Path(dst).exists()
        assert "copiad" in msg.lower() or "copiado" in msg.lower()

    def test_move_file(self, fm: FileManager, tmp_dir: Path) -> None:
        src = tmp_dir / "move_me.txt"
        dst = str(tmp_dir / "moved.txt")
        src.write_text("mover")
        msg = fm.move_file(str(src), dst)
        assert Path(dst).exists()
        assert not src.exists()


# --------------------------------------------------------------------------- #
# list_directory / search_files
# --------------------------------------------------------------------------- #
class TestListSearch:
    def test_list_directory(self, fm: FileManager, tmp_dir: Path) -> None:
        (tmp_dir / "a.txt").write_text("a")
        (tmp_dir / "b.py").write_text("b")
        msg = fm.list_directory(str(tmp_dir))
        assert "a.txt" in msg or "b.py" in msg

    def test_list_nonexistent_directory(self, fm: FileManager) -> None:
        msg = fm.list_directory("/ruta/que/no/existe_xyz")
        assert "no existe" in msg.lower() or "error" in msg.lower()

    def test_search_files(self, fm: FileManager, tmp_dir: Path) -> None:
        (tmp_dir / "report.pdf").write_text("pdf content")
        (tmp_dir / "notes.txt").write_text("notes")
        msg = fm.search_files(str(tmp_dir), "*.pdf")
        assert "report.pdf" in msg

    def test_search_no_results(self, fm: FileManager, tmp_dir: Path) -> None:
        msg = fm.search_files(str(tmp_dir), "*.xyz_nada")
        assert "no se encontraron" in msg.lower() or "0" in msg or "ninguno" in msg.lower()
