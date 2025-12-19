"""
DOCX 文件生成工具

用于将文章内容（含图片）转换为 Word 文档格式
"""

from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from pathlib import Path
import tempfile
import os
import structlog

logger = structlog.get_logger()


class DocxGenerator:
    """DOCX 文档生成器（支持图片嵌入）"""

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "toutiao_articles"
        self.temp_dir.mkdir(exist_ok=True)

    def _set_chinese_font(self, run, font_name: str = "宋体"):
        """设置中文字体"""
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)

    def _add_image_to_doc(
        self,
        doc: Document,
        image_path: str,
        width_inches: float = 5.5,
        caption: str = None,
    ) -> bool:
        """
        添加图片到文档

        Args:
            doc: 文档对象
            image_path: 图片本地路径
            width_inches: 图片宽度（英寸）
            caption: 图片说明（可选）

        Returns:
            bool: 是否成功添加
        """
        try:
            if not os.path.exists(image_path):
                logger.warning("image_not_found", path=image_path)
                return False

            # 添加图片
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run()
            run.add_picture(image_path, width=Inches(width_inches))

            # 添加图片说明
            if caption:
                caption_para = doc.add_paragraph()
                caption_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                caption_run = caption_para.add_run(caption)
                caption_run.font.size = Pt(9)
                caption_run.font.italic = True
                self._set_chinese_font(caption_run, "宋体")

            return True
        except Exception as e:
            logger.error("add_image_failed", path=image_path, error=str(e))
            return False

    def _organize_images_by_position(self, images: list) -> dict:
        """
        按位置组织图片

        Returns:
            dict: {
                "cover": [img1, ...],
                "after_paragraph": {1: [img], 3: [img], ...},
                "end": [img1, ...]
            }
        """
        organized = {
            "cover": [],
            "after_paragraph": {},
            "end": [],
        }

        for img in images:
            position = img.get("position", "end")
            path = img.get("path", "")

            if not path or not os.path.exists(path):
                continue

            if position == "cover":
                organized["cover"].append(img)
            elif position.startswith("after_paragraph:"):
                try:
                    para_num = int(position.split(":")[1])
                    if para_num not in organized["after_paragraph"]:
                        organized["after_paragraph"][para_num] = []
                    organized["after_paragraph"][para_num].append(img)
                except:
                    organized["end"].append(img)
            else:
                organized["end"].append(img)

        return organized

    def create_article_docx(
        self,
        title: str,
        content: str,
        images: list = None,
        article_id: str = None,
    ) -> str:
        """
        创建文章 DOCX 文件（含图片）

        Args:
            title: 文章标题
            content: 文章正文
            images: 图片列表 [{"path": str, "position": str, "prompt": str}, ...]
            article_id: 文章ID (用于文件名)

        Returns:
            str: DOCX 文件的完整路径
        """
        doc = Document()
        images = images or []

        # 组织图片
        organized_images = self._organize_images_by_position(images)

        # 1. 添加标题
        title_para = doc.add_heading(title, level=1)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in title_para.runs:
            self._set_chinese_font(run, "黑体")

        # 添加空行
        doc.add_paragraph()

        # 2. 添加封面图（如果有）
        for img in organized_images["cover"]:
            self._add_image_to_doc(doc, img["path"], width_inches=5.5)
            doc.add_paragraph()  # 图片后空行

        # 3. 添加正文内容（按段落，插入图片）
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]

        for para_index, para_text in enumerate(paragraphs):
            para_num = para_index + 1  # 段落号从1开始

            # 添加段落文本
            para = doc.add_paragraph(para_text)
            para_format = para.paragraph_format
            para_format.line_spacing = 1.5
            para_format.space_after = Pt(6)
            para_format.first_line_indent = Cm(0.74)  # 首行缩进2字符

            for run in para.runs:
                run.font.size = Pt(12)
                self._set_chinese_font(run, "宋体")

            # 检查此段落后是否需要插入图片
            if para_num in organized_images["after_paragraph"]:
                doc.add_paragraph()  # 段落后空行
                for img in organized_images["after_paragraph"][para_num]:
                    self._add_image_to_doc(doc, img["path"], width_inches=5.0)
                doc.add_paragraph()  # 图片后空行

        # 4. 添加结尾图片
        if organized_images["end"]:
            doc.add_paragraph()  # 正文后空行
            for img in organized_images["end"]:
                self._add_image_to_doc(doc, img["path"], width_inches=5.0)

        # 生成文件名
        if article_id:
            filename = f"article_{article_id}.docx"
        else:
            import uuid
            filename = f"article_{uuid.uuid4().hex[:8]}.docx"

        # 保存文件
        file_path = self.temp_dir / filename
        doc.save(str(file_path))

        logger.info(
            "docx_created",
            path=str(file_path),
            title=title[:30],
            image_count=len(images),
        )

        return str(file_path)

    def create_preview_docx(
        self,
        title: str,
        content: str,
        images: list = None,
        article_id: str = None,
    ) -> str:
        """
        创建预览用的 DOCX 文件（与发布版相同）

        这是 create_article_docx 的别名，用于语义清晰
        """
        return self.create_article_docx(title, content, images, article_id)

    def get_docx_path(self, article_id: str) -> str | None:
        """获取已生成的 DOCX 文件路径"""
        file_path = self.temp_dir / f"article_{article_id}.docx"
        if file_path.exists():
            return str(file_path)
        return None

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
        cleaned = 0

        for file_path in self.temp_dir.glob("article_*.docx"):
            try:
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    file_path.unlink()
                    cleaned += 1
            except Exception:
                pass

        if cleaned > 0:
            logger.info("docx_cleanup", cleaned_count=cleaned)


# 全局实例
docx_generator = DocxGenerator()
