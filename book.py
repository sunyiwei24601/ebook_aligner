# -*- coding: utf-8 -*-

import ebooklib
from ebooklib import epub
import re
from bs4 import BeautifulSoup
from translator import Translator, TranslatorType
import pickle
import os
from settings import *

BOOK_SAVE_DIR = "books"
PARAGRAPH_HEADER = ['<p>', '<h1>']
translator = Translator()


class Book:
    """
    电子书的主体，读取epub文件并解析为不同的pages(章节)
    """

    def __init__(self, filename, save=True, debug=False):
        self.book_file = epub.read_epub(os.path.join(EPUB_DIR, filename))
        self.filename = filename
        self.if_save = save
        page_items = list(self.book_file.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        self.pages = []
        bar = tqdm(page_items)
        for item in bar:
            name = item.get_name()
            bar.set_description(f'开始解析章节 {name}')
            if 'nav' not in name:
                page = Page(item, self)
                if len(page.head) != 0 and len(page.tail) != 0:
                    self.pages.append(page)
        # 测试单独章节使用
        if debug:
            self.pages = self.pages[8:10]

        logger.info("%s 章节解析完成。", self.get_name())
        self.length = self.get_length()

        self.save()

    def save(self):
        """
        保存为.book文件
        :return:
        """
        if self.if_save:
            save_filename = self.filename.split('.epub')[0] + '.book'
            with open(os.path.join(BOOK_SAVE_DIR, save_filename), 'wb') as f:
                pickle.dump(self, f)

    def get_length(self, translated=False):
        """
        获取全书长度
        :param translated: True则获取中文翻译版本长度
        :return:
        """
        if translated:
            self.length = sum([_.get_length(translated=True) for _ in self.pages])
        else:
            self.length = sum([page.get_length() for page in self.pages])
        return self.length

    def get_translate(self):
        """
        对每个page进行翻译，途中会保存
        :return:
        """
        for page in self.pages:
            page.translate()
            self.save()
        logger.info("%s 翻译完成", self.get_name())

    def save_combined(self):
        """
        将两本书合并之后，保存为新的epub文件
        :return:
        """
        for page in self.pages:
            page.set_page_combined()
        epub.write_epub(self.get_name() + '_combined.epub', self.book_file)

    def get_name(self):
        book_file = self.book_file
        try:
            title = book_file.get_metadata('DC', 'title')[0][0]
        except Exception as e:
            logger.warning("未找到本书的metadata, %s", e)
            title = self.filename
        return title.replace(":", "")[:20]

    @staticmethod
    def open_book(filename, load=True, debug=False):
        """
        打开一本书，如果已经存在则读取文件，不存在则重新载入
        :param filename: 电子书文件名，默认放在BOOK_SAVE_DIR文件夹下
        :param debug: 测试用选项，打开后只会选取某几个特定page
        :param load: 是否加载本地存档文件
        :return:
        """
        save_filename = filename.split('.epub')[0] + '.book'
        if save_filename in os.listdir(BOOK_SAVE_DIR) and load:
            with open(os.path.join(BOOK_SAVE_DIR, save_filename), 'rb') as f:
                book = pickle.load(f)
                logger.info("%s 加载成功。", book.get_name())
                return book
        else:
            return Book(filename, debug=debug)

    def reset(self):
        """
        重置已经对齐的内容，重新进行对齐
        :return:
        """
        self.if_save = True
        for page in self.pages:
            page.reset()
            page.book = self

    def get_main_page_num(self):
        """
        获取占本书前95%长度的章节数量，视为主要章节数量，用于比较不同电子书之间的章节数量差异
        :return: 
        """
        page_length_list = sorted([_.get_length() for _ in self.pages], reverse=True)

        sum_length = sum(page_length_list)
        target = 0
        for i, page_length in enumerate(page_length_list):
            target += page_length
            if target > 0.95 * sum_length:
                break
        return i + 1


class Page:
    """
    用来处理章节内容的类， 由不同的段落paragraph构成
    """
    def __init__(self, item, book):
        self.book = book
        self.origin = item
        self.name = item.get_name()
        self.html = item.get_content().decode('utf-8')

        # 分离html文件的开头，结尾与主体内容
        self.body_start = self.body_end = 0
        self.head = self.extract_head()
        self.tail = self.extract_tail()
        self.body = self.html[self.body_start:self.body_end]

        # 解析章节中的各个段落
        self.paragraphs = []
        self.extract_paragraphs()
        self.length = self.get_length()

        # 用于保存当前的状态
        self.is_translated = False
        self.is_aligned = False
        self.bad_aligned = False

        self.abstract = ""

    def extract_head(self):
        """找到第一个H1或者p的位置，将之前的都默认为header

        Returns:
            _type_: _description_
        """
        h1_index = self.html.find("<h1")
        p1_index = self.html.find("<p")

        if h1_index < 0 and p1_index < 0:
            logger.debug("Header Not Found.")
            self.body_start = 0
            return ""
        elif p1_index > h1_index > 0 or p1_index < 0:
            self.body_start = h1_index
            return self.html[:h1_index]
        else:
            self.body_start = p1_index
            return self.html[:p1_index]

    def extract_tail(self):
        """找到最后一段的结尾位置，后面的都是tailer
        """
        last_p_index = self.html.rfind("</p>") + 4
        last_h1_index = self.html.rfind("</h1>") + 4
        if last_p_index <= 3 and last_h1_index <= 3:
            self.body_end = len(self.html)
            logger.debug("Tail not found!")
            return ""
        self.body_end = max(last_p_index, last_h1_index)
        return self.html[last_p_index:]

    def extract_paragraphs(self):
        """
        根据标签头，拆分出每一段内容
        :return: 
        """
        parts = re.split('(<p|<h)', self.body)
        parts = [_ for _ in parts if len(_) > 0]
        if len(parts) < 2:
            return

        for i in range(0, int((len(parts) - 1)), 2):
            content = parts[i] + parts[i + 1]
            para = Paragraph(content, self)
            self.paragraphs.append(para)

    def print_page_combined(self):
        """
        预览章节对齐的效果
        :return:
        """
        logger.info("%s 章节对齐完成，预览效果如下 :", self.name)
        for p in self.paragraphs:
            print(p.text[:100])
            subjects = p.subjects
            for _ in subjects:
                print_color(_.text[:50], Color.GREEN)

    def set_page_combined(self):
        """
        合并已经对齐的内容，替换中文版中注释的超链接地址为当前文件的url
        :return:
        """
        content = self.head
        page_href = self.get_filename()
        for p in self.paragraphs:
            content += p.content
            for sub_p in p.subjects:
                sub_page_href = sub_p.page.get_filename()
                if page_href and sub_page_href:
                    content += sub_p.content.replace(sub_page_href, page_href)
                else:
                    content += sub_p.content
        content += self.tail
        self.origin.set_content(content.encode())

    def get_abstract(self, n=10, translated=False):
        """
        获取本章前n段的内容作为摘要，用于比较相似度
        :param translated: 是否获取中文版本
        :param n: 获取前n段内容作为摘要
        :return:
        """
        abstract = ""
        i = 0
        for p in self.paragraphs:
            content = p.translation if translated else p.text
            if len(p.text) > 0:
                abstract += content + " "
                i += 1
            if i >= n:
                break
        if translated:
            self.abstract = abstract
        return abstract

    def get_length(self, translated=False):
        """
        获取全文长度
        :param translated: True则表示获取翻译的中文长度
        :return:
        """
        if translated:
            self.length = sum([len(p.translation) for p in self.paragraphs])
        else:
            self.length = sum([len(p.text) for p in self.paragraphs])
        return self.length

    @time_log('Page_Translate')
    def translate(self, para_nums=15):
        """
        翻译章节的内容，只需翻译前para_nums段即可
        :param para_nums:
        :return:
        """
        # logger.info("正在翻译章节：%s", self.name)
        if self.is_translated:
            return
        bar = tqdm(self.paragraphs[:para_nums])

        for i, p in enumerate(bar):
            bar.set_description(f"正在翻译章节: {self.name}")
            p.get_translate()
            if i % 5 == 0:
                self.book.save()
        self.is_translated = True
        self.book.save()

    def save(self):
        self.book.save()

    def reset(self):
        """重置后方便重新对齐"""
        self.is_aligned = False
        for p in self.paragraphs:
            p.reset()

    def get_filename(self):
        """
        提取page的超链接地址
        :return:
        """
        parts = self.origin.file_name.split('/')
        if len(parts) > 0 and "html" in parts[-1]:
            return parts[-1]
        else:
            return ""


class Paragraph:
    def __init__(self, content, page):
        self.page = page
        self.content = content
        self.text = self.extract_text()
        self.subjects = []
        self.align_score = 0
        self.translation = ''
        self.is_translated = False

    def add_subject(self, paragraph, score=0):
        """增加一段对应的译文， 记录译文的匹配分数

        Args:
            paragraph (_type_): _description_
            :param score:
        """
        self.subjects.append(paragraph)
        self.align_score = score

    def extract_sentences(self):
        """提取出每一句句子

        Returns:
            _type_: _description_
        """
        sentences = re.split(r'\.|!', self.text)
        sentences = [_ for _ in sentences if len(_) > 0]
        sentences = [Sentence(_) for _ in sentences]
        return sentences

    def extract_text(self):
        soup = BeautifulSoup(self.content, 'html.parser')
        return soup.text.strip()

    @time_log("Paragraph_Translate")
    def get_translate(self):
        if len(self.text) < 2 or self.is_translated:
            return
        self.translation = translator.translate(self.text)
        self.is_translated = True

    def reset(self):
        self.subjects = []


class Sentence:
    """
    Deprecated, 本来可以用作逐句的翻译对齐
    """

    def __init__(self, text):
        self.text = text
        self.translation = ''
        self.translate()

    def translate(self):
        self.translation = translator.detect_before_translate(self.text)


if __name__ == '__main__':
    book = Book.open_book('book4.epub', load=True)
    book.get_translate()
    book.save_combined()
    print(book)
