from markdown_reader import MarkdownFile

file = MarkdownFile("test.md")

research_section = file.header.add_section("Исследование", content="1")

new_section = research_section.add_section("Новое", content="Работает")
research_section.add_section("Старое", "Класс")
new_section.add_section("Круто", "очень")
file.save(add_table_of_content=True)