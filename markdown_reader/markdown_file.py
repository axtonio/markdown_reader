from __future__ import annotations

__all__ = ["MarkdownSection", "MarkdownFile"]

import re
import pdfkit
import pypandoc
import frontmatter
from copy import copy
from pathlib import Path
from frontmatter import Post
from typing import Literal, overload
from functools import cached_property
from dataclasses import dataclass, field
from terminal_app.naming import generate_path

LINK_PATTERN = r"\!\[.*?\]\((.*?)\)"
DOC_PATTERN = r"(?<!\!)\[([^]]+)\]\(([^)]+)\)"


@dataclass
class MarkdownSection:
    name: str
    level: int
    file: MarkdownFile
    parent: MarkdownSection | None = field(init=False)
    content: str = ""
    children: dict[str, MarkdownSection] = field(default_factory=dict)

    @property
    def images(self) -> list[str]:

        links = []
        for line in self.content.splitlines():
            match = re.search(LINK_PATTERN, line)
            if match:
                url = match.group(1)
                url = url.strip("<>")
                links.append(url)

        return links

    @property
    def docs(self) -> list[tuple[str, str]]:
        """
        Возвращает список кортежей (name, path), где
        [name](path) не содержит в начале восклицательный знак, чтобы исключить изображения.
        """
        doc_links = []
        for line in self.content.splitlines():
            matches = re.findall(DOC_PATTERN, line)
            for link_name, link_path in matches:
                doc_links.append((link_name.strip(), link_path.strip()))
        return doc_links

    @property
    def text(self) -> str:

        lines = []
        for line in self.content.splitlines():
            match = re.search(LINK_PATTERN, line)
            if not match:
                lines.append(line)

        return "\n".join(lines).strip("\n").strip()

    @cached_property
    def path(self) -> str:
        if self.parent is None:
            return self.file.name + "/" + self.name
        return self.parent.path + "/" + self.name

    def add_section(
        self,
        name: str,
        content: str = "",
        if_exist: Literal["replace", "error", "change_content"] = "change_content",
        remove_subsections: bool = True,
    ) -> MarkdownSection:

        lines: list[str] = []

        if remove_subsections:
            code = False
            for line in content.splitlines():
                if line.startswith("```"):
                    code = not code
                if line.startswith("#") and not code:
                    _, sub_section_name = self.file.level_and_name(line)
                    lines.append(f"***{sub_section_name}***")
                else:
                    lines.append(line)
            content = "\n".join(lines)

        if name in self.children.keys() and if_exist == "change_content":
            section = self.children[name]
            section.content = content

        else:

            assert name not in self.file.all_sections.keys() or if_exist == "replace"

            if name not in self.file.all_sections.keys():
                assert name.lower() not in map(
                    lambda x: x.lower(), self.file.all_sections.keys()
                )

            section = MarkdownSection(
                name=name, level=self.level + 1, file=self.file, content=content
            )

            section.parent = self

        self.children.pop(name, None)
        # * important, because check all_section in process section
        self.file.all_sections[name] = self.children[name] = section

        self.file.update()
        return section


class MarkdownFile:
    name: str
    frontmatter: Post
    header: MarkdownSection
    all_sections: dict[str, MarkdownSection] = {}

    def __init__(
        self,
        markdown_path: Path | str,
        table_of_content_name: str = "Content",
        mode: Literal["r", "w", "generate_path"] = "r",
    ) -> None:

        if isinstance(markdown_path, str):
            markdown_path = Path(markdown_path)

        if mode == "generate_path":
            markdown_path = generate_path(markdown_path)
        else:
            open(markdown_path, mode)

        assert markdown_path.suffix == ".md", "There must be a .md extension file"
        self.markdown_path = markdown_path
        self.name = self.markdown_path.stem
        self.table_of_content = table_of_content_name
        self.refresh_from_file()

    def delete_section(self, name: str) -> None:
        if name not in self.all_sections.keys():
            return None

        assert self.all_sections[name].parent
        parent = self.all_sections[name].parent

        if parent is not None:
            parent.children.pop(name)

        self.update()

    @overload
    def get_template(self, template: Literal["llm"]) -> None:
        pass

    @overload
    def get_template(
        self,
        template: Literal["llm"],
        *,
        if_exist: Literal["replace", "error"] = "error",
    ) -> None:
        pass

    @overload
    def get_template(self, template: Literal["llm"], *, clear: Literal[True]) -> None:
        pass

    def get_template(
        self,
        template: Literal["llm"],
        *,
        if_exist: Literal["replace", "error"] = "error",
        clear: bool = False,
    ) -> None:

        match template:
            case "llm":
                if clear:
                    self.header.children = {}

                if not self.header.content:
                    self.header.content = "***Тут пишите ваш запрос***"

                try:
                    self.header.add_section(
                        "Context",
                        if_exist=if_exist,
                    )
                except:
                    pass

                try:
                    self.header.add_section(
                        "RAG",
                        if_exist=if_exist,
                    )
                except:
                    pass

                try:
                    self.header.add_section(
                        "CAG",
                        if_exist=if_exist,
                    )
                except:
                    pass

                try:
                    self.header.add_section(
                        "System Prompt",
                        content="Отвечай в формате Markdown",
                        if_exist=if_exist,
                    )
                except:
                    pass

                try:
                    self.header.add_section("History", if_exist=if_exist)
                except:
                    pass

                self.save()

    @staticmethod
    def level_and_name(row: str) -> tuple[int, str]:
        row.strip()
        level = 0
        name = ""
        for sb in row:
            if sb == "#":
                level += 1
                continue
            name = row.replace("#", "").strip()
            break

        return level, name

    def _refresh_tree(self) -> None:

        current_section: MarkdownSection = None  # type: ignore
        old_section = self.all_sections
        self.all_sections = {}

        content = ""
        code = False

        def process_section(section_row: str) -> None:
            nonlocal old_section
            nonlocal current_section

            level, name = self.level_and_name(section_row)

            if (section := old_section.get(name, None)) is None:
                new_section = MarkdownSection(name=name, level=level, file=self)
            else:
                section.level = level
                new_section = section

            if level == 1:
                assert current_section is None, "There should be only one header"

                new_section.parent = None

                current_section = new_section
                self.header = current_section
                self.all_sections[current_section.name] = current_section
                return

            if new_section.level > current_section.level:
                assert (
                    current_section.level + 1 == new_section.level
                ), "Incorrect nesting order"
                new_section.parent = current_section
                current_section.children[new_section.name] = new_section
            else:
                parent_section = current_section

                while parent_section.level + 1 != new_section.level:
                    parent_section = parent_section.parent
                    assert parent_section is not None, "Incorrect nesting order"

                new_section.parent = parent_section
                parent_section.children[new_section.name] = new_section

            current_section = new_section
            self.all_sections[current_section.name] = current_section

        for row in self.frontmatter.content.splitlines(keepends=True):
            if row.startswith("```"):
                code = not code

            if row.startswith("#") and not code:
                if current_section is not None:
                    current_section.content = content.strip()

                process_section(row)
                content = ""
                continue

            content += row

        try:
            current_section.content = content.strip()
        except:
            self.header = MarkdownSection(name=self.name.title(), level=1, file=self)
            self.save()

    def refresh_from_file(self) -> None:
        self.file = open(self.markdown_path, "r", encoding="utf-8")

        self.frontmatter = frontmatter.load(self.markdown_path.as_posix())

        self._refresh_tree()

        self.file.close()

    def _refresh_formatter(self):

        section_content = ""

        def make_content(section: MarkdownSection) -> None:
            nonlocal section_content

            section_content += "{} {}{}\n\n".format(
                "#" * section.level,
                section.name,
                "\n\n" + section.content if section.content else "",
            )

            for section in section.children.values():
                make_content(section)

        make_content(self.header)

        formatter = copy(self.frontmatter)
        formatter.content = section_content

        return formatter

    def update(self) -> None:

        self.frontmatter = self._refresh_formatter()
        self._refresh_tree()

    def save(self, add_table_of_content: bool = False) -> None:
        if add_table_of_content:
            self.delete_section(self.table_of_content)
            table_of_content = ""

            def _add_level(sub_section: MarkdownSection):
                nonlocal table_of_content

                indent = " " * ((sub_section.level - 1) * 2)
                anchor = sub_section.name.lower().replace(" ", "-")
                table_of_content += "\n{}- [{}](#{})".format(
                    indent, sub_section.name, anchor
                )

                for child in sub_section.children.values():
                    _add_level(child)

            _add_level(self.header)

            children = self.header.children
            self.header.children = {}

            self.header.add_section(self.table_of_content, table_of_content)
            self.header.children.update(children)

        self.update()
        with open(self.markdown_path, "w") as f:
            f.write(frontmatter.dumps(self.frontmatter) + "\n")

    def export(
        self,
        html_path: Path | str | None = None,
        pdf_path: Path | str | None = None,
        custom_css: str | Path = Path(__file__).parent / "export.css",
        pdfkit_options: dict[str, str] | None = None,
    ) -> tuple[Path, Path]:
        if html_path is None:
            html_path = (
                self.markdown_path.parent / f"{self.markdown_path.stem}.html"
            ).as_posix()
        if pdf_path is None:
            pdf_path = (
                self.markdown_path.parent / f"{self.markdown_path.stem}.pdf"
            ).as_posix()
        if isinstance(custom_css, Path):
            custom_css = open(custom_css).read()

        html = pypandoc.convert_file(
            source_file=self.markdown_path,
            to="html",
            format="md",
            extra_args=["-s"],  # -s => standalone
        )

        # 2) Включаем meta viewport для «резиновой» ширины
        #    Плюс встраиваем CSS для скроллинга широких таблиц.
        meta_viewport = (
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        )
        meta_viewport += "<style>\n" + custom_css + "\n</style>\n"

        insert_pos = html.find("</head>")
        if insert_pos == -1:
            # если по какой-то причине нет </head>, добавим в начало
            html = meta_viewport + html
        else:
            html = html[:insert_pos] + meta_viewport + html[insert_pos:]

        # 3) Сохраняем этот HTML при желании
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # 4) Генерируем PDF, если нужно
        if not pdfkit_options:
            pdfkit_options = {
                "page-size": "A4",
                "margin-top": "10mm",
                "margin-right": "10mm",
                "margin-bottom": "10mm",
                "margin-left": "10mm",
                "encoding": "UTF-8",
                # Можно включать/выключать smart-shrinking, zoom и т. д.
            }

        pdfkit.from_file(html_path, pdf_path, options=pdfkit_options)

        return Path(html_path), Path(pdf_path)
