"""
DOCX 文件生成工具

用于将文章内容转换为 Word 文档格式
"""

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path
import tempfile
import os


class DocxGenerator:
    """DOCX 文档生成器"""

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "toutiao_articles"
        self.temp_dir.mkdir(exist_ok=True)

    def create_article_docx(
        self,
        title: str,
        content: str,
        article_id: str = None,
    ) -> str:
        """
        创建文章 DOCX 文件

        Args:
            title: 文章标题
            content: 文章正文
            article_id: 文章ID (用于文件名)

        Returns:
            str: DOCX 文件的完整路径
        """
        # 创建文档
        doc = Document()

        # 设置标题
        title_para = doc.add_heading(title, level=1)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 添加空行
        doc.add_paragraph()

        # 添加正文内容
        paragraphs = content.split('\n')
        for para_text in paragraphs:
            if para_text.strip():
                para = doc.add_paragraph(para_text)
                # 设置段落格式
                para_format = para.paragraph_format
                para_format.line_spacing = 1.5
                para_format.space_after = Pt(6)

                # 设置字体
                for run in para.runs:
                    run.font.size = Pt(12)
                    run.font.name = '宋体'

        # 生成文件名
        if article_id:
            filename = f"article_{article_id}.docx"
        else:
            import uuid
            filename = f"article_{uuid.uuid4().hex[:8]}.docx"

        # 保存文件
        file_path = self.temp_dir / filename
        doc.save(str(file_path))

        return str(file_path)

    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        清理旧的临时文件

        Args:
            max_age_hours: 文件保留时间(小时)
        """
        import time

        if not self.temp_dir.exists():
            return

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        for file_path in self.temp_dir.glob("article_*.docx"):
            try:
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    file_path.unlink()
            except Exception:
                pass


# 全局实例
docx_generator = DocxGenerator()
